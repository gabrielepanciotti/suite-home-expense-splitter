# tests/test_split_finance_source.py
"""Issue #4: the divider reads shared expenses from the finance node. Zero network:
the finance API is an httpx.MockTransport."""
from __future__ import annotations

from datetime import date

import httpx
import pytest

from home_expense_splitter.split.engine import LedgerSource, compute_split, split_expenses
from home_expense_splitter.split.sources import FinanceSource, FinanceUnavailable, source_for
from tests.archive_rows import add_row
from home_expense_splitter.store.tables import Reimbursement


def _row(raw_hash: str, kind: str, cents: int, category: str | None = None, bp: int | None = None) -> dict:
    return {
        "raw_hash": raw_hash, "kind": kind, "amount_cents": cents, "category": category,
        "member_b_share_bp": bp, "status": "confermato",
    }


LEDGER = [
    _row("h1", "spesa_condivisa", 100000, "CASA"),
    _row("h2", "spesa_condivisa", 3000, "SALUTE", bp=3333),
    _row("h3", "spesa_condivisa", 5000, "AMAZON (vari)"),  # excluded by house rule
    _row("h4", "spesa_condivisa", 7000, "CASA"),           # reimbursed locally
    _row("t1", "member_transfer", 20000),
    _row("t2", "member_transfer", -5000),
]


def _client(rows: list[dict], calls: list[httpx.Request] | None = None) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if calls is not None:
            calls.append(request)
        p = request.url.params
        assert p["status"] == "confermato"
        matching = [r for r in rows if r["kind"] == p["kind"]]
        offset, limit = int(p["offset"]), int(p["limit"])
        return httpx.Response(200, json={"items": matching[offset:offset + limit], "total": len(matching)})

    return httpx.Client(base_url="http://finance.test", transport=httpx.MockTransport(handler))


def test_finance_source_split():
    source = FinanceSource(_client(LEDGER), reimbursed_hashes={"h4"})
    assert [row["raw_hash"] for row in source.shared_rows()] == ["h1", "h2", "h3", "h4"]
    res = split_expenses(source, member_a_pct=70, member_b_pct=30, escluse=["AMAZON"])
    assert res["divisible_cents"] == 103000
    assert res["member_b_quota_cents"] == 30000 + 1000
    assert res["net_bonifici_cents"] == 15000
    assert res["saldo_cents"] == 16000


def test_finance_source_pages_through_everything(monkeypatch):
    monkeypatch.setattr("home_expense_splitter.split.sources.PAGE_SIZE", 2)
    rows = [_row(f"h{i}", "spesa_condivisa", 100, "CASA") for i in range(5)]
    calls: list[httpx.Request] = []
    expenses = FinanceSource(_client(rows, calls)).shared_expenses()
    assert len(expenses) == 5
    assert len(calls) == 3  # 2 + 2 + 1


def test_finance_source_deduplicates_rows_repeated_across_pages(monkeypatch):
    monkeypatch.setattr("home_expense_splitter.split.sources.PAGE_SIZE", 2)
    first = [
        _row("h1", "spesa_condivisa", 100, "CASA"),
        _row("h2", "spesa_condivisa", 200, "CASA"),
    ]
    second = [
        _row("h2", "spesa_condivisa", 200, "CASA"),
        _row("h3", "spesa_condivisa", 300, "CASA"),
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        items = first if request.url.params["offset"] == "0" else second
        return httpx.Response(200, json={"items": items, "total": 3})

    client = httpx.Client(base_url="http://finance.test", transport=httpx.MockTransport(handler))
    rows = FinanceSource(client).shared_rows()
    assert [row["raw_hash"] for row in rows] == ["h1", "h2", "h3"]


@pytest.mark.parametrize("response", [httpx.Response(500), httpx.Response(200, text="not json")])
def test_finance_errors_raise_unavailable(response):
    client = httpx.Client(base_url="http://finance.test", transport=httpx.MockTransport(lambda r: response))
    with pytest.raises(FinanceUnavailable):
        FinanceSource(client).shared_expenses()


def test_connection_error_raises_unavailable():
    def refuse(request):
        raise httpx.ConnectError("refused", request=request)

    client = httpx.Client(base_url="http://finance.test", transport=httpx.MockTransport(refuse))
    with pytest.raises(FinanceUnavailable):
        FinanceSource(client).net_member_transfers_cents()


@pytest.mark.parametrize("missing_field", ["raw_hash", "amount_cents", "category"])
def test_finance_row_missing_required_field_raises_unavailable(missing_field: str) -> None:
    row = _row("h1", "spesa_condivisa", 100, "CASA")
    del row[missing_field]

    with pytest.raises(FinanceUnavailable, match=missing_field):
        FinanceSource(_client([row])).shared_rows()


@pytest.mark.parametrize(
    ("field", "value"),
    [("amount_cents", "100"), ("raw_hash", 1)],
)
def test_finance_row_wrong_required_field_type_raises_unavailable(field: str, value: object) -> None:
    row = _row("h1", "spesa_condivisa", 100, "CASA")
    row[field] = value

    with pytest.raises(FinanceUnavailable, match=field):
        FinanceSource(_client([row])).shared_rows()


def test_finance_source_close_closes_mock_transport() -> None:
    closed: list[bool] = []

    class TrackingMockTransport(httpx.MockTransport):
        def close(self) -> None:
            closed.append(True)
            super().close()

    transport = TrackingMockTransport(
        lambda request: httpx.Response(200, json={"items": [], "total": 0})
    )
    client = httpx.Client(base_url="http://finance.test", transport=transport)

    with FinanceSource(client) as source:
        assert source.shared_rows() == []

    assert closed == [True]


def test_source_for_default_is_finance(session, monkeypatch):
    monkeypatch.delenv("HOMEEXPENSESPLITTER_SPLIT_SOURCE")
    assert isinstance(source_for(session), FinanceSource)


def test_source_for_ledger_reads_archive(session):
    assert isinstance(source_for(session), LedgerSource)


def test_source_for_finance_carries_local_reimbursements(session, monkeypatch):
    session.add(Reimbursement(raw_hash="h4"))
    session.flush()
    monkeypatch.setenv("HOMEEXPENSESPLITTER_SPLIT_SOURCE", "finance")
    monkeypatch.setenv("FINANCE_URL", "http://finance.test")
    source = source_for(session)
    assert isinstance(source, FinanceSource)
    assert source._reimbursed == {"h4"}


def test_source_for_rejects_unknown(session, monkeypatch):
    monkeypatch.setenv("HOMEEXPENSESPLITTER_SPLIT_SOURCE", "excel")
    with pytest.raises(ValueError):
        source_for(session)


def test_ledger_and_finance_agree_on_same_data(session):
    """Parity: the same ledger read locally or through finance gives the same balance,
    with `rimborsato` carried by the reimbursements table on the finance side."""
    rows = []
    for i, (kind, cents, cat, status) in enumerate([
        ("spesa_condivisa", 100001, "CASA", "confermato"),
        ("spesa_condivisa", 5277, "CASA", "rimborsato"),
        ("spesa_condivisa", 999, "AMAZON x", "confermato"),
        ("member_transfer", 20000, None, "confermato"),
        ("member_transfer", -3000, None, "confermato"),
    ]):
        t = add_row(
            session, d=date(2025, 1, i + 1), description=f"r{i}", amount_cents=cents,
            kind=kind, category=cat, shared=kind == "spesa_condivisa", status=status,
        )
        session.flush()
        # finance copies rimborsato as confermato (Finance hes_migration).
        rows.append(_row(t.raw_hash, kind, cents, cat))
        if status == "rimborsato":
            session.add(Reimbursement(raw_hash=t.raw_hash))
    session.flush()

    kw = dict(member_a_pct=70, member_b_pct=30, escluse=["AMAZON"])
    local = compute_split(session, **kw)
    reimbursed = {r.raw_hash for r in session.query(Reimbursement)}
    remote = split_expenses(FinanceSource(_client(rows), reimbursed), **kw)
    assert local == remote
