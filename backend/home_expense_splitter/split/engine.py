# home_expense_splitter/split/engine.py
"""Split/settlement engine (Fase 3).

saldo (member B owes member A) = member_b_quota - net_bonifici
- member_b_quota = somma, per ogni spesa condivisa divisibile, della quota del member B:
  la quota esplicita della riga se c'è (`member_b_share_bp`), altrimenti la regola di
  casa (`member_b_pct` di `split_config.toml`)
- divisible = somma degli importi delle spese condivise divise (vedi `_is_divided`)
- net_bonifici = somma degli importi dei bonifici del member B (già segnati)

Il mestiere di questo nodo è DIVIDERE (issue #4): il calcolo non sa da dove arrivano le
uscite. Le legge da una `SharedExpenseSource` — il libro mastro locale (`LedgerSource`)
o il nodo `finance` (Life#81, `sources.FinanceSource`), scelti da configurazione — e resta
sostituibile da un finto nei test.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_DOWN, Decimal
from typing import Iterable, Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from home_expense_splitter.store.tables import Transaction

BP_FULL = 10_000  # basis points in 100%


@dataclass(frozen=True)
class SharedExpense:
    """Una uscita condivisa, confermata, come la vede il divisore."""

    category: str | None
    amount_cents: int
    # Quota esplicita del member B in basis points (6667 = 66,67%); None = regola di casa.
    member_b_share_bp: int | None = None


class SharedExpenseSource(Protocol):
    """Da dove il divisore legge cosa dividere. Contratto verso `finance` (Life#81)."""

    def shared_expenses(self) -> Iterable[SharedExpense]: ...

    def shared_rows(self) -> list[dict]: ...

    def net_member_transfers_cents(self) -> int: ...


class LedgerSource:
    """Adattatore sul libro mastro storico locale (`transactions`, status `rimborsato` incluso)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def shared_expenses(self) -> Iterable[SharedExpense]:
        rows = self._session.execute(
            select(
                Transaction.category,
                Transaction.amount_cents,
                Transaction.member_b_share_bp,
            ).where(
                Transaction.kind == "spesa_condivisa",
                Transaction.status == "confermato",
            )
        ).all()
        return [SharedExpense(cat, amount or 0, bp) for cat, amount, bp in rows]

    def shared_rows(self) -> list[dict]:
        """Return confirmed shared-expense rows in the finance API shape."""
        rows = self._session.execute(
            select(
                Transaction.raw_hash,
                Transaction.date,
                Transaction.description,
                Transaction.category,
                Transaction.amount_cents,
                Transaction.member_b_share_bp,
            ).where(
                Transaction.kind == "spesa_condivisa",
                Transaction.status == "confermato",
            )
        ).mappings()
        return [dict(row) for row in rows]

    def net_member_transfers_cents(self) -> int:
        return self._session.scalar(
            select(func.coalesce(func.sum(Transaction.amount_cents), 0)).where(
                Transaction.kind == "member_transfer",
                Transaction.status == "confermato",
            )
        ) or 0


def _is_excluded(category: str | None, escluse: list[str]) -> bool:
    """Una categoria è esclusa se CONTIENE come sottostringa uno dei token escluse."""
    if category is None:
        return False
    return any(token in category for token in escluse)


def _is_divided(expense: SharedExpense, escluse: list[str]) -> bool:
    """Una quota esplicita vince sull'esclusione di categoria: chi l'ha calcolata
    (es. Health sulle dosi reali) ha già deciso che quella spesa si divide, e in che
    proporzione. L'esclusione è la regola di casa, e vale solo dove la quota non c'è."""
    if expense.member_b_share_bp is not None:
        return True
    return not _is_excluded(expense.category, escluse)


def split_expenses(
    source: SharedExpenseSource,
    *,
    member_a_pct: int,
    member_b_pct: int,
    escluse: list[str],
) -> dict:
    """Calcolo puro della divisione su una sorgente qualsiasi. Importi in centesimi."""
    default_bp = member_b_pct * BP_FULL // 100
    per_category_totals: dict[str | None, int] = {}
    divisible_cents = 0
    # Somma ESATTA delle quote (cent × bp), arrotondata una volta sola alla fine:
    # sommare quote già arrotondate per riga accumulerebbe errori di mezzo cent.
    quota_cent_bp = 0
    for expense in source.shared_expenses():
        if not _is_divided(expense, escluse):
            continue
        bp = default_bp if expense.member_b_share_bp is None else expense.member_b_share_bp
        per_category_totals[expense.category] = (
            per_category_totals.get(expense.category, 0) + expense.amount_cents
        )
        divisible_cents += expense.amount_cents
        quota_cent_bp += expense.amount_cents * bp

    per_category = sorted(per_category_totals.items(), key=lambda item: item[1], reverse=True)
    net_bonifici_cents = source.net_member_transfers_cents()

    # Metà di un totale con cent dispari cade esattamente su X,5 cent: il tie va
    # arrotondato VERSO IL BASSO (a favore del member B), non col banker's rounding
    # di round(). Es. divisibile 12.588,43 → quota 6.294,21 (non 6.294,22).
    member_b_quota_cents = int(
        (Decimal(quota_cent_bp) / Decimal(BP_FULL)).quantize(
            Decimal("1"), rounding=ROUND_HALF_DOWN
        )
    )
    saldo_cents = member_b_quota_cents - net_bonifici_cents

    return {
        "member_a_pct": member_a_pct,
        "member_b_pct": member_b_pct,
        "divisible_cents": divisible_cents,
        "member_b_quota_cents": member_b_quota_cents,
        "net_bonifici_cents": net_bonifici_cents,
        "saldo_cents": saldo_cents,
        "per_category": per_category,
    }


def compute_split(
    session: Session,
    *,
    member_a_pct: int,
    member_b_pct: int,
    escluse: list[str],
) -> dict:
    """Divisione sulla sorgente configurata (`split/sources.py`). Nessuna scrittura sul DB."""
    from home_expense_splitter.split.sources import source_for  # avoids an import cycle

    source = source_for(session)
    try:
        return split_expenses(
            source,
            member_a_pct=member_a_pct,
            member_b_pct=member_b_pct,
            escluse=escluse,
        )
    finally:
        close = getattr(source, "close", None)
        if close is not None:
            close()
