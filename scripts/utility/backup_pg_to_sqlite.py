"""Backup del Postgres `homeexpensesplitter` (LIVE, fonte di verità) -> SQLite locale.

Direzione SICURA: legge il Postgres live e riscrive `data/conti.sqlite` come copia
fedele. NON tocca mai il Postgres. È l'inverso di `migrate_sqlite_to_pg.py` (che è
pericoloso e va usato solo per un restore deliberato).

    .venv/Scripts/python.exe scripts/utility/backup_pg_to_sqlite.py

Da quando i conti si modificano dal vivo (dashboard/CLI), la verità è il Postgres:
questo script serve solo a tenere un backup locale aggiornato, non a ri-derivare.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import create_engine, insert, select  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from home_expense_splitter.config import DATABASE_URL, load_split_config  # noqa: E402
from home_expense_splitter.split.engine import compute_split  # noqa: E402
from home_expense_splitter.store.tables import Base  # noqa: E402

SQLITE_PATH = ROOT / "data" / "conti.sqlite"
SQLITE_URL = f"sqlite:///{SQLITE_PATH}"


def main() -> None:
    if not DATABASE_URL.startswith("postgresql"):
        raise SystemExit(
            f"HOMEEXPENSESPLITTER_DATABASE_URL deve puntare al Postgres live, non a {DATABASE_URL!r}"
        )

    src = create_engine(DATABASE_URL)  # LIVE Postgres (sola lettura)
    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    dst = create_engine(SQLITE_URL)  # backup locale (riscritto)

    Base.metadata.drop_all(dst)
    Base.metadata.create_all(dst)

    with src.connect() as sc, dst.begin() as dc:
        for table in Base.metadata.sorted_tables:
            rows = [dict(r._mapping) for r in sc.execute(select(table))]
            if rows:
                dc.execute(insert(table), rows)
            print(f"  {table.name:14s} {len(rows):>4d} righe")

    cfg = load_split_config()
    s = sessionmaker(dst)()
    res = compute_split(
        s,
        member_a_pct=cfg["percentuali"]["member_a"],
        member_b_pct=cfg["percentuali"]["member_b"],
        escluse=cfg["escluse"],
    )
    s.close()
    print(f"\n  divisibile: {res['divisible_cents']/100:,.2f} EUR")
    print(f"  MEMBER B DEVE A MEMBER A: {res['saldo_cents']/100:,.2f} EUR  (backup di Postgres live)")


if __name__ == "__main__":
    main()
