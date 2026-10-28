# tests/test_split.py
from __future__ import annotations

from datetime import date

from home_expense_splitter.split.engine import compute_split
from tests.archive_rows import add_row

ESCLUSE = ["AMAZON", "TECNOLOGIA / ELETTRONICA (condivisa)", "ACQUISTI VARI (condivisi)"]


def _shared(session, *, description: str, amount_cents: int, category: str) -> None:
    add_row(
        session,
        d=date(2025, 1, 1),
        description=description,
        amount_cents=amount_cents,
        kind="spesa_condivisa",
        category=category,
        shared=True,
    )


def _bonifico(session, *, description: str, amount_cents: int) -> None:
    add_row(
        session,
        d=date(2025, 1, 1),
        description=description,
        amount_cents=amount_cents,
        kind="member_transfer",
        category=None,
        shared=False,
    )


def _seed_golden(session) -> None:
    """Divisible categories summing to 8777.13 € (877713 cents) across
    non-excluded categories, one excluded AMAZON category that must NOT count,
    and member_transfer rows netting to 1526.27 € (152627 cents)."""
    # Divisible: 500000 + 300000 + 77713 = 877713 cents (8777.13 €)
    _shared(session, description="Affitto", amount_cents=500000, category="CASA")
    _shared(session, description="Spesa", amount_cents=300000, category="ALIMENTARI")
    _shared(session, description="Bollette", amount_cents=77713, category="UTENZE")
    # Excluded — must NOT count toward divisible
    _shared(session, description="Cuffie", amount_cents=99999, category="AMAZON (vari - per casa?)")
    # Member transfers netting to 152627 cents: +220627 received, -68000 sent
    _bonifico(session, description="Bonifico da member B", amount_cents=220627)
    _bonifico(session, description="Restituzione a member B", amount_cents=-68000)


def test_golden_70_30(session):
    _seed_golden(session)
    result = compute_split(session, member_a_pct=70, member_b_pct=30, escluse=ESCLUSE)
    assert result["divisible_cents"] == 877713
    assert result["member_b_quota_cents"] == 263314  # round(877713 * 0.30) = 263314
    assert result["net_bonifici_cents"] == 152627
    assert result["saldo_cents"] == 110687  # 263314 - 152627 → 1106.87 €


def test_50_50(session):
    _seed_golden(session)
    result = compute_split(session, member_a_pct=50, member_b_pct=50, escluse=ESCLUSE)
    # divisible 877713 is odd → round(877713 * 0.5) = round(438856.5) = 438856
    # (banker's rounding lands on the even 438856)
    expected_quota = round(877713 * 50 / 100)
    assert result["member_b_quota_cents"] == expected_quota
    assert result["saldo_cents"] == expected_quota - 152627


def test_excluded_category_does_not_count(session):
    """A category containing an escluse token (AMAZON) is excluded from divisible."""
    _shared(session, description="Affitto", amount_cents=100000, category="CASA")
    _shared(session, description="Cuffie", amount_cents=50000, category="AMAZON (vari)")
    result = compute_split(session, member_a_pct=70, member_b_pct=30, escluse=ESCLUSE)
    assert result["divisible_cents"] == 100000
    cats = {c for c, _ in result["per_category"]}
    assert "CASA" in cats
    assert "AMAZON (vari)" not in cats


def test_giroconto_and_other_kinds_ignored(session):
    """giroconto / spesa_personale / entrata do NOT affect divisible or net."""
    _shared(session, description="Affitto", amount_cents=100000, category="CASA")
    add_row(
        session, d=date(2025, 1, 1), description="Giroconto", amount_cents=999999,
        kind="giroconto", category="GIRO", shared=False,
    )
    add_row(
        session, d=date(2025, 1, 1), description="Personale", amount_cents=55555,
        kind="spesa_personale", category="HOBBY", shared=False,
    )
    add_row(
        session, d=date(2025, 1, 1), description="Stipendio", amount_cents=300000,
        kind="entrata", category="REDDITO", shared=False,
    )
    _bonifico(session, description="Bonifico da member B", amount_cents=10000)
    result = compute_split(session, member_a_pct=70, member_b_pct=30, escluse=ESCLUSE)
    assert result["divisible_cents"] == 100000
    assert result["net_bonifici_cents"] == 10000
    assert result["saldo_cents"] == round(100000 * 30 / 100) - 10000


def test_non_confermato_excluded(session):
    """Le spese condivise con status 'rimborsato'/'skipped' NON contano nella divisione
    (es. voci rimborsate o 'da non contare'); contano solo quelle 'confermato'."""
    _shared(session, description="Affitto", amount_cents=100000, category="CASA")
    add_row(
        session, d=date(2025, 1, 1), description="Rimborsato", amount_cents=50000,
        kind="spesa_condivisa", category="CASA", shared=True, status="rimborsato",
    )
    add_row(
        session, d=date(2025, 1, 1), description="Da non contare", amount_cents=30000,
        kind="spesa_condivisa", category="CASA", shared=True, status="skipped",
    )
    result = compute_split(session, member_a_pct=70, member_b_pct=30, escluse=ESCLUSE)
    assert result["divisible_cents"] == 100000


def test_compute_split_is_pure(session):
    """compute_split performs no writes (no Settlement created)."""
    from home_expense_splitter.store.tables import Settlement

    _seed_golden(session)
    before = session.query(Settlement).count()
    compute_split(session, member_a_pct=70, member_b_pct=30, escluse=ESCLUSE)
    after = session.query(Settlement).count()
    assert before == after == 0


def test_per_category_totals(session):
    _seed_golden(session)
    result = compute_split(session, member_a_pct=70, member_b_pct=30, escluse=ESCLUSE)
    per_cat = dict(result["per_category"])
    assert per_cat["CASA"] == 500000
    assert per_cat["ALIMENTARI"] == 300000
    assert per_cat["UTENZE"] == 77713
    assert sum(per_cat.values()) == result["divisible_cents"]
