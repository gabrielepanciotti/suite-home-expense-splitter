# home_expense_splitter_backend/app.py
"""FastAPI app del divisore HomeExpenseSplitter (issue #4).

Lettura: ogni saldo passa per `compute_split`, sulla sorgente configurata (di norma il
nodo `finance`, che possiede le uscite). Le uscite, le categorie, i tag e i report del
libro mastro non stanno qui: sono l'API di `finance`.
Scrittura: solo lo stato del divisore — settlements e rimborsi.
App pura: nessuna scrittura al DB all'import.
"""
from __future__ import annotations

import io
from typing import Annotated

from fastapi import Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic_settings import NoDecode
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from suite_backend_core import create_app
from suite_backend_core.config import Settings

from home_expense_splitter.config import load_split_config, member_names
from home_expense_splitter.export.excel import build_workbook
from home_expense_splitter.split.engine import compute_split
from home_expense_splitter.split.sources import FinanceUnavailable, source_for
from home_expense_splitter.store.tables import Reimbursement, Settlement
from home_expense_splitter_backend import db
from home_expense_splitter_backend.claims import claims_dependency
from home_expense_splitter_backend.db import SessionLocal, get_session
from home_expense_splitter_backend.schemas import (
    ReimbursementIn,
    ReimbursementOut,
    SettlementCreate,
    SettlementOut,
    SharedExpenseOut,
    SummaryOut,
)
from home_expense_splitter_backend.vista import vista_spec
from suite_backend_core.vista import make_vista_router, require_action

XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class HomeExpenseSplitterSettings(Settings):
    """Shared backend settings with this node's safe local CORS default."""

    app_name: str = "HomeExpenseSplitter"
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3343"]


def _db_ping() -> None:
    """Verify that the divider database accepts a minimal query."""
    session = SessionLocal()
    try:
        session.execute(text("SELECT 1"))
    finally:
        session.close()


app = create_app(settings=HomeExpenseSplitterSettings(), db_ping=_db_ping)
app.include_router(
    make_vista_router(vista_spec, db.preference_store(), claims_dependency, "homeExpenseSplitter")
)


@app.exception_handler(FinanceUnavailable)
def _finance_unavailable(_: Request, exc: FinanceUnavailable) -> JSONResponse:
    # No balance on stale data: the split source is finance and it cannot be read.
    return JSONResponse(status_code=503, content={"detail": str(exc)})


# --------------------------------------------------------------------------- #
# Lettura
# --------------------------------------------------------------------------- #
@app.get("/api/summary", response_model=SummaryOut)
def get_summary(session: Session = Depends(get_session)) -> SummaryOut:
    cfg = load_split_config()
    res = compute_split(
        session,
        member_a_pct=cfg["percentuali"]["member_a"],
        member_b_pct=cfg["percentuali"]["member_b"],
        escluse=cfg["escluse"],
    )
    name_a, name_b = member_names(cfg)
    return SummaryOut(**res, member_a_name=name_a, member_b_name=name_b)


@app.get("/api/shared-expenses", response_model=list[SharedExpenseOut])
def list_shared_expenses(
    session: Session = Depends(get_session),
) -> list[SharedExpenseOut]:
    """List confirmed shared expenses together with the divider reimbursement state."""
    source = source_for(session)
    try:
        source_rows = source.shared_rows()
    finally:
        close = getattr(source, "close", None)
        if close is not None:
            close()

    reimbursements = {
        reimbursement.raw_hash: reimbursement
        for reimbursement in session.scalars(select(Reimbursement)).all()
    }
    expenses = []
    for row in source_rows:
        raw_hash = row["raw_hash"]
        reimbursement = reimbursements.get(raw_hash)
        expenses.append(
            SharedExpenseOut(
                raw_hash=raw_hash,
                date=row.get("date"),
                description=row.get("description"),
                category=row.get("category"),
                amount_cents=row["amount_cents"],
                member_b_share_bp=row.get("member_b_share_bp"),
                reimbursed=reimbursement is not None,
                reimbursed_at=reimbursement.at if reimbursement else None,
                reimbursed_note=reimbursement.note if reimbursement else None,
            )
        )
    return sorted(
        expenses,
        key=lambda expense: (
            expense.date is None,
            -expense.date.toordinal() if expense.date else 0,
            expense.raw_hash,
        ),
    )


@app.get(
    "/api/export.xlsx",
    dependencies=[Depends(require_action(vista_spec, "export.scarica", claims_dependency))],
)
def export_xlsx(session: Session = Depends(get_session)) -> StreamingResponse:
    buffer = io.BytesIO()
    build_workbook(session).save(buffer)
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type=XLSX_MEDIA,
        headers={
            "Content-Disposition": 'attachment; filename="Household_Expenses.xlsx"'
        },
    )


# --------------------------------------------------------------------------- #
# Scrittura (solo stato del divisore)
# --------------------------------------------------------------------------- #
@app.post(
    "/api/settlements",
    response_model=SettlementOut,
    status_code=201,
    dependencies=[Depends(require_action(vista_spec, "saldo.salva", claims_dependency))],
)
def create_settlement(
    payload: SettlementCreate, session: Session = Depends(get_session)
) -> SettlementOut:
    row = Settlement(
        at=payload.at,
        member_b_owes_cents=payload.member_b_owes_cents,
        note=payload.note,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return SettlementOut(id=row.id)


# --------------------------------------------------------------------------- #
# Rimborsi (stato del divisore: la spesa condivisa che il member B ha già reso)
# --------------------------------------------------------------------------- #
@app.get("/api/reimbursements", response_model=list[ReimbursementOut])
def list_reimbursements(session: Session = Depends(get_session)) -> list[ReimbursementOut]:
    rows = session.scalars(select(Reimbursement).order_by(Reimbursement.raw_hash)).all()
    return [ReimbursementOut.model_validate(r) for r in rows]


@app.put(
    "/api/reimbursements",
    response_model=ReimbursementOut,
    dependencies=[Depends(require_action(vista_spec, "rimborso.segna", claims_dependency))],
)
def mark_reimbursed(
    payload: ReimbursementIn, session: Session = Depends(get_session)
) -> ReimbursementOut:
    """Idempotent: marks (or re-annotates) a shared expense as paid back."""
    row = session.get(Reimbursement, payload.raw_hash)
    if row is None:
        row = Reimbursement(raw_hash=payload.raw_hash)
        session.add(row)
    row.at = payload.at
    row.note = payload.note
    session.commit()
    return ReimbursementOut.model_validate(row)


@app.delete(
    "/api/reimbursements/{raw_hash}",
    status_code=204,
    dependencies=[Depends(require_action(vista_spec, "rimborso.annulla", claims_dependency))],
)
def unmark_reimbursed(raw_hash: str, session: Session = Depends(get_session)) -> Response:
    row = session.get(Reimbursement, raw_hash)
    if row is None:
        raise HTTPException(status_code=404, detail="reimbursement not found")
    session.delete(row)
    session.commit()
    return Response(status_code=204)
