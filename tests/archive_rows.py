# tests/archive_rows.py
"""Seed rows into the frozen ledger archive (`transactions`) for tests.

The node no longer writes transactions (issue #4): the ledger lives in finance. Tests
that exercise the split on local data insert archive rows directly, with the same
keyword arguments the removed `repo.add_manual` had.
"""
from __future__ import annotations

import hashlib
from datetime import date
from itertools import count

from sqlalchemy.orm import Session

from home_expense_splitter.store.tables import Transaction

_seq = count()


def add_row(
    session: Session,
    *,
    d: date,
    description: str,
    amount_cents: int,
    kind: str,
    category: str | None,
    shared: bool,
    status: str = "confermato",
    payer: str = "member_a",
    payment_method: str | None = None,
    buoni_cents: int = 0,
    member_b_share_bp: int | None = None,
) -> Transaction:
    key = f"{d}|{description}|{amount_cents}|{next(_seq)}"
    row = Transaction(
        date=d, description=description, amount_cents=amount_cents, source="manuale",
        category=category, kind=kind, shared=shared, payer=payer, status=status,
        raw_hash=hashlib.sha256(key.encode()).hexdigest(), payment_method=payment_method,
        buoni_cents=buoni_cents, member_b_share_bp=member_b_share_bp,
    )
    session.add(row)
    return row
