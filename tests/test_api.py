# tests/test_api.py
from __future__ import annotations

from collections.abc import Iterator
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from home_expense_splitter.split.engine import compute_split
from tests.archive_rows import add_row
from home_expense_splitter.store.tables import Base, Transaction
from home_expense_splitter_backend import app as app_module
from home_expense_splitter_backend.app import XLSX_MEDIA, app
from home_expense_splitter_backend.claims import claims_dependency
from home_expense_splitter_backend.db import get_session
from suite_backend_core.gate import GateClaims

ESCLUSE = ["AMAZON", "TECNOLOGIA / ELETTRONICA (condivisa)", "ACQUISTI VARI (condivisi)"]


def _seed_golden(session: Session) -> None:
    """Stesso dataset di test_split: divisibile 877713, bonifici netti 152627."""
    for desc, cents, cat in (
        ("Affitto", 500000, "CASA"),
        ("Spesa", 300000, "ALIMENTARI"),
        ("Bollette", 77713, "UTENZE"),
        ("Cuffie", 99999, "AMAZON (vari - per casa?)"),  # esclusa
    ):
        add_row(
            session, d=date(2025, 1, 1), description=desc, amount_cents=cents,
            kind="spesa_condivisa", category=cat, shared=True,
        )
    add_row(
        session, d=date(2025, 1, 1), description="Bonifico da member B",
        amount_cents=220627, kind="member_transfer", category=None, shared=False,
    )
    add_row(
        session, d=date(2025, 1, 1), description="Restituzione a member B",
        amount_cents=-68000, kind="member_transfer", category=None, shared=False,
    )
    session.commit()


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    # Engine SQLite in-memory condiviso fra tutte le sessioni del test.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, expire_on_commit=False)

    seed = TestingSession()
    _seed_golden(seed)
    seed.close()

    def override_get_session() -> Iterator[Session]:
        s = TestingSession()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_session] = override_get_session

    async def admin_claims() -> GateClaims:
        return GateClaims(
            person_id="api-test-user",
            instance="homeExpenseSplitter",
            role="admin",
            kind="person",
        )

    app.dependency_overrides[claims_dependency] = admin_claims
    monkeypatch.setattr(app_module, "SessionLocal", TestingSession)
    with TestClient(app) as c:
        c._session_factory = TestingSession  # type: ignore[attr-defined]
        yield c
    app.dependency_overrides.clear()


def test_health_routes_report_database_status_and_allow_local_frontend(
    client: TestClient,
) -> None:
    for path in ("/health", "/api/health"):
        response = client.get(path, headers={"Origin": "http://localhost:3343"})
        assert response.status_code == 200
        assert response.json()["database"] == "ok"
        assert response.headers["access-control-allow-origin"] == "http://localhost:3343"


def test_health_routes_are_503_when_database_ping_fails(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FailingSession:
        def execute(self, statement: object) -> None:
            raise RuntimeError("database unavailable")

        def close(self) -> None:
            pass

    monkeypatch.setattr(app_module, "SessionLocal", FailingSession)

    for path in ("/health", "/api/health"):
        assert client.get(path).status_code == 503


def test_summary_matches_compute_split(client: TestClient) -> None:
    # Saldo atteso calcolato col motore stesso (NON hardcoded), config 50/50.
    session = client._session_factory()  # type: ignore[attr-defined]
    expected = compute_split(session, member_a_pct=50, member_b_pct=50, escluse=ESCLUSE)
    session.close()

    resp = client.get("/api/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["divisible_cents"] == 877713
    assert body["saldo_cents"] == expected["saldo_cents"]
    assert body["net_bonifici_cents"] == 152627
    assert body["member_a_pct"] == 50 and body["member_b_pct"] == 50


def test_export_xlsx(client: TestClient) -> None:
    resp = client.get("/api/export.xlsx")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == XLSX_MEDIA
    assert len(resp.content) > 0
    # Firma file xlsx (zip): "PK"
    assert resp.content[:2] == b"PK"


def test_reimbursements_roundtrip(client: TestClient) -> None:
    r = client.put("/api/reimbursements", json={"raw_hash": "abc", "note": "reso"})
    assert r.status_code == 200 and r.json()["note"] == "reso"
    assert client.put("/api/reimbursements", json={"raw_hash": "abc"}).status_code == 200
    assert [x["raw_hash"] for x in client.get("/api/reimbursements").json()] == ["abc"]
    assert client.delete("/api/reimbursements/abc").status_code == 204
    assert client.delete("/api/reimbursements/abc").status_code == 404


def test_summary_is_503_when_finance_is_down(client: TestClient, monkeypatch) -> None:
    import httpx

    def refuse(request):
        raise httpx.ConnectError("refused", request=request)

    real_client = httpx.Client
    monkeypatch.setattr(
        "home_expense_splitter.split.sources.httpx.Client",
        lambda **kw: real_client(transport=httpx.MockTransport(refuse), **kw),
    )
    monkeypatch.setenv("HOMEEXPENSESPLITTER_SPLIT_SOURCE", "finance")
    r = client.get("/api/summary")
    assert r.status_code == 503


def test_shared_expenses_include_reimbursed_finance_rows(client: TestClient, monkeypatch) -> None:
    import httpx

    rows = [
        {
            "raw_hash": "older",
            "kind": "spesa_condivisa",
            "status": "confermato",
            "date": "2025-01-02",
            "description": "Older expense",
            "category": "CASA",
            "amount_cents": 1500,
            "member_b_share_bp": None,
        },
        {
            "raw_hash": "newer",
            "kind": "spesa_condivisa",
            "status": "confermato",
            "date": "2025-02-03",
            "description": "Newer expense",
            "category": "ALIMENTARI",
            "amount_cents": 2300,
            "member_b_share_bp": 4000,
        },
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        params = request.url.params
        assert params["kind"] == "spesa_condivisa"
        assert params["status"] == "confermato"
        return httpx.Response(200, json={"items": rows, "total": len(rows)})

    real_client = httpx.Client
    monkeypatch.setattr(
        "home_expense_splitter.split.sources.httpx.Client",
        lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw),
    )
    monkeypatch.setenv("HOMEEXPENSESPLITTER_SPLIT_SOURCE", "finance")
    assert client.put(
        "/api/reimbursements", json={"raw_hash": "older", "at": "2025-02-04", "note": "paid"}
    ).status_code == 200

    response = client.get("/api/shared-expenses")

    assert response.status_code == 200
    assert response.json() == [
        {
            "raw_hash": "newer",
            "date": "2025-02-03",
            "description": "Newer expense",
            "category": "ALIMENTARI",
            "amount_cents": 2300,
            "member_b_share_bp": 4000,
            "reimbursed": False,
            "reimbursed_at": None,
            "reimbursed_note": None,
        },
        {
            "raw_hash": "older",
            "date": "2025-01-02",
            "description": "Older expense",
            "category": "CASA",
            "amount_cents": 1500,
            "member_b_share_bp": None,
            "reimbursed": True,
            "reimbursed_at": "2025-02-04",
            "reimbursed_note": "paid",
        },
    ]


def test_shared_expenses_is_503_when_finance_is_down(client: TestClient, monkeypatch) -> None:
    import httpx

    def refuse(request: httpx.Request) -> None:
        raise httpx.ConnectError("refused", request=request)

    real_client = httpx.Client
    monkeypatch.setattr(
        "home_expense_splitter.split.sources.httpx.Client",
        lambda **kw: real_client(transport=httpx.MockTransport(refuse), **kw),
    )
    monkeypatch.setenv("HOMEEXPENSESPLITTER_SPLIT_SOURCE", "finance")

    assert client.get("/api/shared-expenses").status_code == 503


@pytest.mark.parametrize("path", ["/api/summary", "/api/shared-expenses"])
def test_malformed_finance_body_without_items_is_503(
    client: TestClient, monkeypatch, path: str
) -> None:
    import httpx

    real_client = httpx.Client
    monkeypatch.setattr(
        "home_expense_splitter.split.sources.httpx.Client",
        lambda **kw: real_client(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"total": 0})),
            **kw,
        ),
    )
    monkeypatch.setenv("HOMEEXPENSESPLITTER_SPLIT_SOURCE", "finance")

    response = client.get(path)

    assert response.status_code == 503
    assert "items" in response.json()["detail"]


@pytest.mark.parametrize("path", ["/api/summary", "/api/shared-expenses"])
def test_malformed_finance_row_without_raw_hash_is_503(
    client: TestClient, monkeypatch, path: str
) -> None:
    import httpx

    row = {
        "kind": "spesa_condivisa",
        "status": "confermato",
        "category": "CASA",
        "amount_cents": 100,
    }
    real_client = httpx.Client
    monkeypatch.setattr(
        "home_expense_splitter.split.sources.httpx.Client",
        lambda **kw: real_client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json={"items": [row], "total": 1})
            ),
            **kw,
        ),
    )
    monkeypatch.setenv("HOMEEXPENSESPLITTER_SPLIT_SOURCE", "finance")

    response = client.get(path)

    assert response.status_code == 503
    assert "raw_hash" in response.json()["detail"]


def test_finance_client_is_closed_after_each_request(client: TestClient, monkeypatch) -> None:
    import httpx

    closed: list[bool] = []

    class TrackingMockTransport(httpx.MockTransport):
        def close(self) -> None:
            closed.append(True)
            super().close()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"items": [], "total": 0})

    real_client = httpx.Client
    monkeypatch.setattr(
        "home_expense_splitter.split.sources.httpx.Client",
        lambda **kw: real_client(transport=TrackingMockTransport(handler), **kw),
    )
    monkeypatch.setenv("HOMEEXPENSESPLITTER_SPLIT_SOURCE", "finance")

    assert client.get("/api/summary").status_code == 200
    assert client.get("/api/shared-expenses").status_code == 200
    assert closed == [True, True]


def test_shared_expenses_ledger_orders_rows_and_reflects_reimbursement_deletion(
    client: TestClient,
) -> None:
    session = client._session_factory()  # type: ignore[attr-defined]
    session.add_all(
        [
            Transaction(
                raw_hash="ledger-b",
                date=date(2026, 1, 2),
                description="B",
                amount_cents=2,
                source="test",
                category="CASA",
                kind="spesa_condivisa",
                status="confermato",
            ),
            Transaction(
                raw_hash="ledger-a",
                date=date(2026, 1, 2),
                description="A",
                amount_cents=1,
                source="test",
                category="CASA",
                kind="spesa_condivisa",
                status="confermato",
            ),
            Transaction(
                raw_hash="ledger-none",
                date=None,
                description="No date",
                amount_cents=3,
                source="test",
                category="CASA",
                kind="spesa_condivisa",
                status="confermato",
            ),
        ]
    )
    session.commit()
    session.close()

    assert client.put("/api/reimbursements", json={"raw_hash": "ledger-a"}).status_code == 200
    initial = client.get("/api/shared-expenses")
    assert initial.status_code == 200
    rows = initial.json()
    assert [row["raw_hash"] for row in rows[:2]] == ["ledger-a", "ledger-b"]
    assert rows[-1]["raw_hash"] == "ledger-none"
    assert next(row for row in rows if row["raw_hash"] == "ledger-a")["reimbursed"] is True

    assert client.delete("/api/reimbursements/ledger-a").status_code == 204
    rows_after_delete = client.get("/api/shared-expenses").json()
    reimbursed_row = next(row for row in rows_after_delete if row["raw_hash"] == "ledger-a")
    assert reimbursed_row["reimbursed"] is False


def test_ledger_endpoints_are_gone(client: TestClient) -> None:
    """The ledger lives in finance (issue #4): this node exposes no expense writes."""
    assert client.get("/api/transactions").status_code == 404
    assert client.post("/api/transactions", json={}).status_code in (404, 405)
    for path in ("/api/categories", "/api/tags", "/api/stats/by-category", "/api/stats/by-month"):
        assert client.get(path).status_code == 404
