# home_expense_splitter/split/sources.py
"""Where the divider reads what to split (issue #4).

- `finance` — the `finance` node (Life#81), which owns the ledger. Read-only over HTTP.
  The default: this node no longer records expenses.
- `ledger`  — the local `transactions` table (`LedgerSource`): the historical archive,
  frozen since the ledger moved to finance. Only for parity checks and tests.

Chosen by `HOMEEXPENSESPLITTER_SPLIT_SOURCE` (default `finance`). No silent fallback:
if finance is selected and unreachable, the caller gets `FinanceUnavailable` instead of
a balance computed on stale local data.
"""
from __future__ import annotations

import os
from collections.abc import Iterator

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from home_expense_splitter.split.engine import LedgerSource, SharedExpense, SharedExpenseSource
from home_expense_splitter.store.tables import Reimbursement

SOURCE_ENV = "HOMEEXPENSESPLITTER_SPLIT_SOURCE"
FINANCE_URL_ENV = "FINANCE_URL"
DEFAULT_FINANCE_URL = "http://127.0.0.1:10023"
PAGE_SIZE = 500


class FinanceUnavailable(RuntimeError):
    """The finance node could not be read; no balance should be shown."""


def _validated_items(body: object) -> tuple[list[dict], int]:
    if not isinstance(body, dict):
        raise FinanceUnavailable("finance non leggibile: risposta non e' un oggetto")
    missing = [field for field in ("items", "total") if field not in body]
    if missing:
        raise FinanceUnavailable(f"finance non leggibile: risposta senza {', '.join(missing)}")
    items = body["items"]
    if not isinstance(items, list):
        raise FinanceUnavailable("finance non leggibile: items non e' una lista")
    total = body["total"]
    if not isinstance(total, int):
        raise FinanceUnavailable("finance non leggibile: total non e' un intero")
    for row in items:
        if not isinstance(row, dict):
            raise FinanceUnavailable("finance non leggibile: riga non e' un oggetto")
        missing = [field for field in ("raw_hash", "amount_cents", "category") if field not in row]
        if missing:
            raise FinanceUnavailable(f"finance non leggibile: riga senza {', '.join(missing)}")
        if not isinstance(row["raw_hash"], str) or not row["raw_hash"]:
            raise FinanceUnavailable("finance non leggibile: raw_hash non e' una stringa non vuota")
        if not isinstance(row["amount_cents"], int) or isinstance(row["amount_cents"], bool):
            raise FinanceUnavailable("finance non leggibile: amount_cents non e' un intero")
        if row["category"] is not None and not isinstance(row["category"], str):
            raise FinanceUnavailable("finance non leggibile: category non e' una stringa o null")
    return items, total


class FinanceSource:
    """Reads confirmed shared expenses and member transfers from the finance API.

    `reimbursed_hashes`: rows the divider marked `rimborsato` (its own state, see
    `Reimbursement`). Finance only knows `proposto|confermato`, so they are dropped here.
    """

    def __init__(self, client: httpx.Client, reimbursed_hashes: set[str] | None = None) -> None:
        self._client = client
        self._reimbursed = reimbursed_hashes or set()

    def close(self) -> None:
        """Release the HTTP connection pool owned by this source."""
        self._client.close()

    def __enter__(self) -> FinanceSource:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _rows(self, kind: str) -> Iterator[dict]:
        offset = 0
        while True:
            try:
                resp = self._client.get(
                    "/api/transactions",
                    params={"kind": kind, "status": "confermato", "limit": PAGE_SIZE, "offset": offset},
                )
                resp.raise_for_status()
                body = resp.json()
            except (httpx.HTTPError, ValueError) as exc:
                raise FinanceUnavailable(f"finance non leggibile: {exc}") from exc
            items, total = _validated_items(body)
            yield from items
            offset += len(items)
            if not items or offset >= total:
                return

    def shared_expenses(self) -> list[SharedExpense]:
        return [
            SharedExpense(row["category"], row["amount_cents"], row.get("member_b_share_bp"))
            for row in self.shared_rows()
            if row["raw_hash"] not in self._reimbursed
        ]

    def shared_rows(self) -> list[dict]:
        """Return every confirmed shared-expense row, including reimbursed ones."""
        rows_by_hash: dict[str, dict] = {}
        for row in self._rows("spesa_condivisa"):
            rows_by_hash.setdefault(row["raw_hash"], row)
        return list(rows_by_hash.values())

    def net_member_transfers_cents(self) -> int:
        return sum(row["amount_cents"] for row in self._rows("member_transfer"))


def reimbursed_hashes(session: Session) -> set[str]:
    return set(session.scalars(select(Reimbursement.raw_hash)))


def source_for(session: Session) -> SharedExpenseSource:
    """The configured source. `session` still holds the divider's own state."""
    kind = os.environ.get(SOURCE_ENV, "finance").strip().lower()
    if kind == "ledger":
        return LedgerSource(session)
    if kind == "finance":
        local_reimbursed_hashes = reimbursed_hashes(session)
        base_url = os.environ.get(FINANCE_URL_ENV, DEFAULT_FINANCE_URL)
        client = httpx.Client(base_url=base_url, timeout=10.0)
        return FinanceSource(client, local_reimbursed_hashes)
    raise ValueError(f"{SOURCE_ENV} non valido: {kind!r} (ledger|finance)")
