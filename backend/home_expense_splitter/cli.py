# home_expense_splitter/cli.py
"""CLI del divisore (issue #4): divide le uscite condivise lette dalla sorgente configurata.

Le uscite non si registrano qui: si scrivono in `finance` (Life#81), direttamente o via
ExpenseTracker (Life#82). Qui restano la regola di casa, i settlements e i rimborsi.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from typing import Iterator

import typer
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from home_expense_splitter.config import DATABASE_URL, DATA_DIR, load_split_config, member_names
from home_expense_splitter.split.engine import compute_split
from home_expense_splitter.store.tables import Base, Reimbursement, Settlement

app = typer.Typer(help="HomeExpenseSplitter — divisione delle spese condivise")


@contextmanager
def _session() -> Iterator[Session]:
    if DATABASE_URL.startswith("sqlite"):
        DATA_DIR.mkdir(exist_ok=True)
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)
    session = sessionmaker(engine)()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _parse_date(value: str) -> date:
    """Accetta dd/mm/yyyy oppure ISO (yyyy-mm-dd)."""
    try:
        value = value.strip()
        if "/" in value:
            day, month, year = (int(p) for p in value.split("/"))
            return date(year, month, day)
        return date.fromisoformat(value)
    except ValueError as exc:
        raise typer.BadParameter(f"data non valida: {value}") from exc


@app.command("split")
def split(
    save: bool = typer.Option(False, "--save", help="Salva il saldo come Settlement nel DB"),
    date_str: str = typer.Option(None, "--date", help="Data del settlement dd/mm/yyyy (default: nessuna)"),
    note: str = typer.Option(None, "--note", help="Nota per il settlement salvato"),
):
    """Divide le spese condivise e calcola quanto il member B deve al member A."""
    cfg = load_split_config()
    perc = cfg.get("percentuali", {})
    member_a_pct = int(perc.get("member_a", 50))
    member_b_pct = int(perc.get("member_b", 50))
    name_a, name_b = member_names(cfg)
    escluse = list(cfg.get("escluse", []))

    at = None
    if date_str:
        at = _parse_date(date_str)

    with _session() as session:
        result = compute_split(session, member_a_pct=member_a_pct, member_b_pct=member_b_pct, escluse=escluse)

        typer.echo("Spese condivise divisibili:")
        for category, cents in result["per_category"]:
            typer.echo(f"  {category or '(senza categoria)':45s} {cents / 100:>12,.2f} EUR")
        typer.echo(f"  {'─' * 45} {'─' * 12}")
        typer.echo(f"  {'TOTALE DIVISIBILE':45s} {result['divisible_cents'] / 100:>12,.2f} EUR")
        typer.echo("")
        typer.echo(
            f"Quota {name_b} ({member_b_pct}%):           "
            f"{result['member_b_quota_cents'] / 100:>12,.2f} EUR"
        )
        typer.echo(
            f"Bonifici già dati da {name_b} (netto):   "
            f"{result['net_bonifici_cents'] / 100:>12,.2f} EUR"
        )
        typer.echo(f"  {'─' * 45} {'─' * 12}")
        saldo = result["saldo_cents"] / 100
        typer.echo(f"{name_b.upper()} DEVE A {name_a.upper()}:               {saldo:>12,.2f} EUR")

        if save:
            session.add(Settlement(at=at, member_b_owes_cents=result["saldo_cents"], note=note))
            session.commit()
            quando = f" al {at}" if at else ""
            typer.echo(f"\nSettlement salvato{quando}: {saldo:,.2f} EUR.")


@app.command("export-excel")
def export_excel(
    path: str = typer.Option(
        None, "--path", help="Percorso .xlsx di output (default: data/Household_Expenses.xlsx)"
    )
):
    """Genera il .xlsx del Riepilogo Finale (i fogli di dettaglio li esporta finance)."""
    from home_expense_splitter.export.excel import export_workbook

    out = path or str(DATA_DIR / "Household_Expenses.xlsx")
    with _session() as session:
        saved = export_workbook(session, out)
    typer.echo(f"Excel generato: {saved}")


@app.command("rimborso")
def rimborso(
    raw_hash: str = typer.Argument(..., help="raw_hash della spesa condivisa in finance"),
    date_str: str = typer.Option(None, "--date", help="Data del rimborso dd/mm/yyyy"),
    note: str = typer.Option(None, "--note", help="Nota"),
    annulla: bool = typer.Option(False, "--annulla", help="Toglie il segno di rimborso"),
):
    """Segna (o, con --annulla, toglie) una spesa condivisa come già rimborsata dal member B."""
    with _session() as session:
        row = session.get(Reimbursement, raw_hash)
        if annulla:
            if row is None:
                typer.echo("Nessun rimborso registrato per questa spesa.")
                raise typer.Exit(1)
            session.delete(row)
            session.commit()
            typer.echo("Rimborso tolto: la spesa torna nella divisione.")
            return
        if row is None:
            row = Reimbursement(raw_hash=raw_hash)
            session.add(row)
        row.at = _parse_date(date_str) if date_str else None
        row.note = note
        session.commit()
        typer.echo("Spesa segnata come rimborsata: esce dalla divisione.")


@app.command("export-contribution")
def export_contribution(
    out: str = typer.Option(
        "dist/contribution-bundle.json",
        "--out",
        help="Percorso file JSON di output (default: dist/contribution-bundle.json)",
    )
):
    """Esporta le righe public dei dati di questo nodo (settlements) in un bundle JSON.

    Le uscite e i tag appartengono a `finance`: il loro bundle lo produce quel nodo.
    Solo righe con visibility='public' vengono incluse.
    """
    import json
    from pathlib import Path

    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with _session() as session:
        setts = list(session.scalars(select(Settlement).where(Settlement.visibility == "public")))
        bundle = {
            "generated_at": str(date.today()),
            "settlements": [
                {
                    "id": s.id,
                    "at": s.at.isoformat() if s.at else None,
                    "member_b_owes_cents": s.member_b_owes_cents,
                    "note": s.note,
                    "visibility": s.visibility,
                }
                for s in setts
            ],
        }

    out_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    typer.echo(f"settlements  : {len(setts)} righe pubbliche — bundle scritto in {out_path}")


if __name__ == "__main__":
    app()
