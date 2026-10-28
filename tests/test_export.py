# tests/test_export.py
from __future__ import annotations

from datetime import date

from home_expense_splitter.config import load_split_config
from home_expense_splitter.export.excel import build_workbook
from home_expense_splitter.split.engine import compute_split
from tests.archive_rows import add_row


def _seed(session) -> None:
    add_row(session, d=date(2025, 1, 1), description="Affitto",
                    amount_cents=500000, kind="spesa_condivisa", category="CASA", shared=True)
    add_row(session, d=date(2025, 1, 2), description="Cuffie",
                    amount_cents=99999, kind="spesa_personale", category="AMAZON (vari)", shared=False)
    add_row(session, d=date(2025, 1, 3), description="Bonifico da member B",
                    amount_cents=152627, kind="member_transfer", category=None, shared=False)


def test_workbook_has_expected_sheets(session):
    _seed(session)
    wb = build_workbook(session)
    # Detail sheets are the ledger's: finance exports them (issue #4).
    assert wb.sheetnames == ["Riepilogo Finale"]


def test_riepilogo_saldo_matches_engine(session):
    _seed(session)
    cfg = load_split_config()
    expected = compute_split(
        session, member_a_pct=cfg["percentuali"]["member_a"],
        member_b_pct=cfg["percentuali"]["member_b"], escluse=cfg["escluse"],
    )["saldo_cents"] / 100

    ws = build_workbook(session)["Riepilogo Finale"]
    saldo_cells = [
        ws.cell(r, 2).value
        for r in range(1, ws.max_row + 1)
        if ws.cell(r, 1).value == "MEMBER B DEVE A MEMBER A"
    ]
    assert saldo_cells == [expected]
