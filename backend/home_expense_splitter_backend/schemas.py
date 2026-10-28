"""Schemi Pydantic v2 del divisore. Importi SEMPRE in centesimi (int).

Le uscite non hanno schemi qui: il contratto è l'API di `finance` (issue #4).
"""
from __future__ import annotations

from datetime import date as date_t

from pydantic import BaseModel, ConfigDict, Field


class SummaryOut(BaseModel):
    saldo_cents: int
    divisible_cents: int
    member_b_quota_cents: int
    net_bonifici_cents: int
    member_a_pct: int
    member_b_pct: int
    # Display names: generic defaults from config, device-local aliases via the
    # untracked MEMBER_ALIASES_JSON env var (never tracked personal names).
    member_a_name: str = "Member A"
    member_b_name: str = "Member B"
    per_category: list[tuple[str | None, int]]


class SharedExpenseOut(BaseModel):
    raw_hash: str
    date: date_t | None
    description: str | None
    category: str | None
    amount_cents: int
    member_b_share_bp: int | None
    reimbursed: bool
    reimbursed_at: date_t | None
    reimbursed_note: str | None


class SettlementCreate(BaseModel):
    at: date_t | None = None
    member_b_owes_cents: int
    note: str | None = None


class SettlementOut(BaseModel):
    id: int = Field(..., description="id del Settlement creato")


class ReimbursementIn(BaseModel):
    # Ledger key of the shared expense member B paid back (same raw_hash in finance).
    raw_hash: str = Field(min_length=1)
    at: date_t | None = None
    note: str | None = None


class ReimbursementOut(ReimbursementIn):
    model_config = ConfigDict(from_attributes=True)
