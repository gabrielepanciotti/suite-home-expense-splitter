# tests/test_split_explicit_share.py
"""Issue #4: the divider reads from a replaceable source and honours an explicit
per-row member B share instead of always applying the house rule."""
from __future__ import annotations

from datetime import date

from home_expense_splitter.split.engine import SharedExpense, compute_split, split_expenses
from tests.archive_rows import add_row

ESCLUSE = ["AMAZON"]


class FakeSource:
    """Stand-in for the future `finance` node: no DB, no network."""

    def __init__(self, expenses: list[SharedExpense], transfers_cents: int = 0) -> None:
        self._expenses = expenses
        self._transfers = transfers_cents

    def shared_expenses(self):
        return self._expenses

    def net_member_transfers_cents(self) -> int:
        return self._transfers


def _split(source, pct_b: int = 30) -> dict:
    return split_expenses(source, member_a_pct=100 - pct_b, member_b_pct=pct_b, escluse=ESCLUSE)


def test_fake_source_house_rule_only():
    res = _split(FakeSource([SharedExpense("CASA", 100000)], transfers_cents=10000))
    assert res["divisible_cents"] == 100000
    assert res["member_b_quota_cents"] == 30000
    assert res["saldo_cents"] == 20000


def test_explicit_share_overrides_house_rule():
    # Integratore preso in rapporto 2:1 → member B paga 1/3 (3333 bp), non il 30%.
    res = _split(FakeSource([SharedExpense("SALUTE", 3000, member_b_share_bp=3333)]))
    assert res["member_b_quota_cents"] == 1000  # 3000 * 0.3333 = 999.9 → 1000


def test_mixed_rows_are_summed_exactly_then_rounded_once():
    res = _split(FakeSource([
        SharedExpense("CASA", 100001),                          # 30% → 30000.3
        SharedExpense("SALUTE", 3000, member_b_share_bp=6667),  # → 2000.1
    ]))
    assert res["divisible_cents"] == 103001
    assert res["member_b_quota_cents"] == 32000  # 32000.4, one rounding only


def test_explicit_share_wins_over_excluded_category():
    res = _split(FakeSource([
        SharedExpense("AMAZON (vari)", 5000),                           # house rule: out
        SharedExpense("AMAZON (vari)", 2000, member_b_share_bp=5000),  # explicit: in
    ]))
    assert res["divisible_cents"] == 2000
    assert res["member_b_quota_cents"] == 1000
    assert res["per_category"] == [("AMAZON (vari)", 2000)]


def test_zero_and_full_shares():
    res = _split(FakeSource([
        SharedExpense("A", 1000, member_b_share_bp=0),
        SharedExpense("B", 1000, member_b_share_bp=10000),
    ]))
    assert res["member_b_quota_cents"] == 1000


def test_ledger_source_reads_explicit_share(session):
    add_row(
        session, d=date(2025, 1, 1), description="Affitto", amount_cents=100000,
        kind="spesa_condivisa", category="CASA", shared=True,
    )
    add_row(
        session, d=date(2025, 1, 2), description="Integratore", amount_cents=3000,
        kind="spesa_condivisa", category="SALUTE", shared=True, member_b_share_bp=3333,
    )
    session.flush()
    res = compute_split(session, member_a_pct=70, member_b_pct=30, escluse=ESCLUSE)
    assert res["divisible_cents"] == 103000
    assert res["member_b_quota_cents"] == 30000 + 1000
