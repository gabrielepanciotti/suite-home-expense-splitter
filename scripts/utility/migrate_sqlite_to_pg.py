"""RESTORE DELIBERATO: SQLite locale -> Postgres `homeexpensesplitter` (SOVRASCRIVE il live).

⚠️ PERICOLOSO. Da quando i conti si modificano dal vivo (dashboard/CLI), la fonte
di verità è il **Postgres**, non lo SQLite. Questo script CANCELLA il Postgres e lo
riscrive dallo SQLite: usalo SOLO per un restore voluto da un backup conosciuto.
Per il backup normale (direzione sicura) usa `backup_pg_to_sqlite.py`.

Richiede `--force` per girare, così non clobbera il live per sbaglio.

    .venv/Scripts/python.exe scripts/utility/migrate_sqlite_to_pg.py --force
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import create_engine, insert, select, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from home_expense_splitter.config import DATABASE_URL  # noqa: E402
from home_expense_splitter.split.engine import compute_split  # noqa: E402
from home_expense_splitter.store.tables import Base  # noqa: E402

SQLITE_URL = f"sqlite:///{ROOT / 'data' / 'conti.sqlite'}"


def main() -> None:
    if not DATABASE_URL.startswith("postgresql"):
        raise SystemExit(f"HOMEEXPENSESPLITTER_DATABASE_URL deve puntare a Postgres, non a {DATABASE_URL!r}")
    if "--force" not in sys.argv:
        raise SystemExit(
            "RIFIUTATO: questo script SOVRASCRIVE il Postgres live e perde le modifiche fatte\n"
            "dal vivo (dashboard/CLI). La verità ora è il Postgres.\n"
            "  - Backup normale (PG -> SQLite): scripts/utility/backup_pg_to_sqlite.py\n"
            "  - Restore deliberato (SQLite -> PG): rilancia con --force."
        )

    src = create_engine(SQLITE_URL)
    dst = create_engine(DATABASE_URL)

    Base.metadata.drop_all(dst)
    Base.metadata.create_all(dst)

    with src.connect() as sc, dst.begin() as dc:
        for table in Base.metadata.sorted_tables:
            rows = [dict(r._mapping) for r in sc.execute(select(table))]
            if rows:
                dc.execute(insert(table), rows)
            print(f"  {table.name:14s} {len(rows):>4d} righe")

    # Allinea le sequence: gli id sono stati inseriti espliciti.
    with dst.begin() as dc:
        for table in Base.metadata.sorted_tables:
            if "id" in table.c:
                dc.execute(text(
                    f"SELECT setval(pg_get_serial_sequence('{table.name}', 'id'), "
                    f"COALESCE((SELECT MAX(id) FROM {table.name}), 1))"
                ))

    # Verifica saldo dalla destinazione Postgres.
    from home_expense_splitter.config import load_split_config
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
    print(f"  bonifici member B (netto): {res['net_bonifici_cents']/100:,.2f} EUR")
    print(f"  MEMBER B DEVE A MEMBER A: {res['saldo_cents']/100:,.2f} EUR  (atteso 4.767,94)")


if __name__ == "__main__":
    main()
