# tests/test_split_regression_a.py
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from home_expense_splitter.split.engine import compute_split
from tests.archive_rows import add_row
from home_expense_splitter.store.tables import Base


def _session():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return Session(eng)


def test_buoni_do_not_change_divisible():
    s = _session()
    # 50,00 condivisa, 16,00 buoni → divisibile conta 50,00 (costo pieno)
    add_row(
        s,
        d=date(2026, 1, 1),
        description="super",
        amount_cents=5000,
        kind="spesa_condivisa",
        category="SUPERMERCATO",
        shared=True,
        payment_method="misto",
        buoni_cents=1600,
        status="confermato",
    )
    s.flush()
    res = compute_split(s, member_a_pct=50, member_b_pct=50, escluse=[])
    assert res["divisible_cents"] == 5000
    assert res["member_b_quota_cents"] == 2500
