"""⚠️ BOOTSTRAP STORICO — NON è più la fonte di verità.

Da quando i conti si modificano dal vivo (dashboard/CLI sul Postgres `homeexpensesplitter`), la
verità è il **Postgres**. Questo script ri-deriva lo SQLite dai SOLI file fixture e
NON conosce le modifiche manuali fatte dopo: il suo risultato è ormai DISALLINEATO
dal live (es. categorie spostate, riclassifiche). Tienilo solo come ricostruzione
d'emergenza del bootstrap iniziale. **Non migrarlo mai sul Postgres live** (vedi il
guard in `migrate_sqlite_to_pg.py`). Per un backup fedele usa `backup_pg_to_sqlite.py`.

Ricostruisce `data/conti.sqlite` da zero, in modo deterministico e riproducibile.

Il DB è un artefatto DERIVATO (gitignored): questa è la pipeline completa che lo
genera dai file sorgente versionati/forniti. Replica tutte le decisioni prese con
l'utente (giu 2026). Re-eseguibile: cancella e ricrea il DB.

    .venv/Scripts/python.exe scripts/utility/rebuild_db.py

Fonti richieste (tutte versionate come fixture):
- tests/fixtures/spese_storico.xlsx              (storico Excel)
- tests/fixtures/bank_bbva.xlsx                  (estratto BBVA, copia di 14-06-2026.xlsx)

Il CSV PayPal originale è andato perso nella migrazione DB: le 35 righe PayPal
vengono ricostruite per importo dalla mappa ``PAYPAL35`` (derivata a suo tempo dal
CSV + PDF Cronologia). I due addebiti da 100,00 € si disambiguano per data.
"""
from __future__ import annotations

import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# The tracked fixtures are sanitized: counterparties use FICTIONAL names.
# The bank importer matches them via the same env vars used on a real device.
import os

os.environ.setdefault("BANK_SELF_NAMES", "alex sample")
os.environ.setdefault("BANK_MEMBER_B_NAMES", "blake sample")
sys.path.insert(0, str(ROOT / "backend"))
DB = ROOT / "data" / "conti.sqlite"
PY = ROOT / ".venv" / "Scripts" / "python.exe"

# Il file banca è versionato come fixture (copia di 14-06-2026.xlsx); lo storico idem.
EXCEL = ROOT / "tests" / "fixtures" / "spese_storico.xlsx"
BANK = ROOT / "tests" / "fixtures" / "bank_bbva.xlsx"

# Mappatura dei 35 addebiti PayPal (da CSV PayPal + PDF Cronologia, analisi giu 2026).
# chiave = importo in centesimi -> (descrizione, categoria, shared). I 100,00 € sono
# due (KoRo vs AndreaZurlini) e si disambiguano per data (vedi _paypal_map).
PAYPAL35 = {
    45493: ("LDR S.P.A. (PayPal)", "ALTRO PERSONALE", 0),
    17233: ("DAMINELLI PIETRO (Paga in 3, rimb.parz. 119 in PayPal)", "ALTRO PERSONALE", 0),
    12000: ("Yash Raja (PayPal)", "ALTRO PERSONALE", 0),
    11284: ("CTRIP/Trip.com volo (Paga in 3, rimb.parz. in PayPal)", "VIAGGI - VOLI/PRENOTAZIONI", 1),
    8532: ("Ryanair (PayPal)", "VIAGGI - VOLI/PRENOTAZIONI", 1),
    7522: ("CTRIP volo (Paga in 3, rimb.parz. in PayPal)", "VIAGGI - VOLI/PRENOTAZIONI", 1),
    7472: ("Ryanair (Paga in 3)", "VIAGGI - VOLI/PRENOTAZIONI", 1),
    6833: ("Jungle Hobbies Ltd (Paga in 3)", "ALTRO PERSONALE", 0),
    6548: ("Booking.com (PayPal)", "VIAGGI - VOLI/PRENOTAZIONI", 1),
    6299: ("PROJECT WEB (Paga in 3)", "ALTRO PERSONALE", 0),
    5000: ("SERGIO GINI (PayPal)", "ALTRO PERSONALE", 0),
    4715: ("DFRobot (Paga in 3)", "TECNOLOGIA / ELETTRONICA", 0),
    4010: ("Mattia Bruni (PayPal)", "VERDURE MATTIA BRUNI (PayPal)", 1),
    3751: ("Airbnb (PayPal)", "VIAGGI - VOLI/PRENOTAZIONI", 1),
    3400: ("Booking.com (PayPal)", "VIAGGI - VOLI/PRENOTAZIONI", 1),
    3387: ("Player Srl (Paga in 3)", "TECNOLOGIA / ELETTRONICA", 0),
    3373: ("KoRo Handels (Paga in 3)", "KORO ALIMENTARI (PayPal)", 1),
    3372: ("KoRo Handels (Paga in 3)", "KORO ALIMENTARI (PayPal)", 1),
    2973: ("eBay (Paga in 3)", "ALTRO PERSONALE", 0),
    2660: ("DHL Express (Paga in 3)", "ALTRO PERSONALE", 0),
    2510: ("Mattia Bruni (PayPal)", "VERDURE MATTIA BRUNI (PayPal)", 1),
    2480: ("Mattia Bruni (PayPal)", "VERDURE MATTIA BRUNI (PayPal)", 1),
    2402: ("Payment Escrow Inc. (PayPal)", "ALTRO PERSONALE", 0),
    1988: ("IDROCORP (Paga in 3)", "ALTRO PERSONALE", 0),
    1987: ("IDROCORP (Paga in 3)", "ALTRO PERSONALE", 0),
    1850: ("Mattia Bruni (PayPal)", "VERDURE MATTIA BRUNI (PayPal)", 1),
    1675: ("Mattia Bruni (PayPal)", "VERDURE MATTIA BRUNI (PayPal)", 1),
    735: ("eBay (Paga in 3)", "ALTRO PERSONALE", 0),
    499: ("DisneyPlus (PayPal)", "ABBONAMENTI PERSONALI", 0),
    471: ("DeepSeek (PayPal)", "ABBONAMENTI PERSONALI", 0),
}


def _orm_steps() -> None:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker

    from sqlalchemy import select

    from home_expense_splitter.cli import import_bank_into, load_workbook_into
    from home_expense_splitter.store import repo
    from home_expense_splitter.store.tables import Base, Transaction

    engine = create_engine(f"sqlite:///{DB}")
    Base.metadata.create_all(engine)
    s = sessionmaker(engine)()

    # 1. Storico Excel -> 316 confermate
    load_workbook_into(s, str(EXCEL))
    s.commit()

    # 2. Correzioni una-tantum (decisioni utente)
    repo.reclassify(s, description="Decathlon Foligno",
                    in_category="ACQUISTI VARI (condivisi)", delete=True)
    repo.add_manual(s, d=date(2026, 5, 1), description="Spesa fissa maggio", amount_cents=10000,
                    kind="spesa_condivisa", category="SPESA FISSA MENSILE (100 EUR/mese)", shared=True)
    repo.add_manual(s, d=date(2026, 6, 1), description="Spesa fissa giugno", amount_cents=10000,
                    kind="spesa_condivisa", category="SPESA FISSA MENSILE (100 EUR/mese)", shared=True)
    repo.add_manual(s, d=date(2026, 6, 6), description="Vacanza Abruzzo", amount_cents=15000,
                    kind="spesa_condivisa", category="VIAGGI - ABRUZZO", shared=True)
    s.commit()

    # 3. Estratto BBVA (classify on) -> 170 proposte
    import_bank_into(s, str(BANK), classify_on=True)
    s.commit()

    # 4. Dettaglio PayPal: rinomina le 35 righe "PayPal (da dettagliare)" per importo
    #    (il CSV è perso → mappa PAYPAL35). I due 100,00 € si disambiguano per data:
    #    07/04 = KoRo (condivisa), 24/04 = Andrea Zurlini (personale).
    paypal_by_date = {
        (10000, date(2026, 4, 7)): ("KoRo Handels 100€ (PayPal)", "KORO ALIMENTARI (PayPal)", 1),
        (10000, date(2026, 4, 24)): ("Andrea Zurlini (PayPal)", "ALTRO PERSONALE", 0),
    }
    proposals = s.scalars(
        select(Transaction).where(
            Transaction.source == "banca",
            Transaction.status == "proposto",
            Transaction.description == "PayPal (da dettagliare)",
        )
    ).all()
    for t in proposals:
        mapped = paypal_by_date.get((t.amount_cents, t.date)) or PAYPAL35.get(t.amount_cents)
        if not mapped:
            continue  # nessuna corrispondenza nota → resta proposta (lo segnala _verify)
        desc, cat, sh = mapped
        t.description, t.category, t.shared = desc, cat, bool(sh)
        t.kind = "spesa_condivisa" if sh else "spesa_personale"
        t.status = "confermato"
    s.commit()

    # 5. "affitto e spese - <account holder>" (+10,01) = bonifico ricevuto -> entrata
    #    (così non viene preso dal batch spese come AFFITTO condivisa)
    s.execute(text("update transactions set kind='entrata', category='RIMBORSI / ENTRATE VARIE' "
                   "where description like 'affitto e spese%' and amount_cents>0"))
    s.commit()
    s.close()


def _suggest_classify() -> None:
    """106 spese carta + 17 merchant PayPal: ruleset merchant -> categoria/shared + conferma."""
    script = ROOT / "scripts" / "utility" / "suggest_card_classification.py"
    subprocess.run([str(PY), str(script)], check=True, cwd=str(ROOT))            # scrive TSV
    subprocess.run([str(PY), str(script), "--apply"], check=True, cwd=str(ROOT))  # applica


def _sql_steps() -> None:
    import sqlite3

    c = sqlite3.connect(DB)
    cur = c.cursor()

    # 6. PayPal "Paga in 3 rate" (18 generici), risolti dal PDF Cronologia.
    payin3 = {
        7472: ("Ryanair (Paga in 3)", "VIAGGI - VOLI/PRENOTAZIONI", 1),
        6833: ("Jungle Hobbies Ltd (Paga in 3)", "ALTRO PERSONALE", 0),
        6299: ("PROJECT WEB (Paga in 3)", "ALTRO PERSONALE", 0),
        4715: ("DFRobot (Paga in 3)", "TECNOLOGIA / ELETTRONICA", 0),
        3387: ("Player Srl (Paga in 3)", "TECNOLOGIA / ELETTRONICA", 0),
        3373: ("KoRo Handels (Paga in 3)", "KORO ALIMENTARI (PayPal)", 1),
        3372: ("KoRo Handels (Paga in 3)", "KORO ALIMENTARI (PayPal)", 1),
        2973: ("eBay (Paga in 3)", "ALTRO PERSONALE", 0),
        2660: ("DHL Express (Paga in 3)", "ALTRO PERSONALE", 0),
        1988: ("IDROCORP (Paga in 3)", "ALTRO PERSONALE", 0),
        1987: ("IDROCORP (Paga in 3)", "ALTRO PERSONALE", 0),
        735: ("eBay (Paga in 3)", "ALTRO PERSONALE", 0),
        # delicati (decisione utente: rimborsi parziali in PayPal, non in banca -> contano)
        7522: ("CTRIP volo (Paga in 3, rimb.parz. in PayPal)", "VIAGGI - VOLI/PRENOTAZIONI", 1),
        11284: ("CTRIP/Trip.com volo (Paga in 3, rimb.parz. in PayPal)", "VIAGGI - VOLI/PRENOTAZIONI", 1),
        17233: ("DAMINELLI PIETRO (Paga in 3, rimb.parz. 119 in PayPal)", "ALTRO PERSONALE", 0),
    }
    for tid, a in cur.execute("select id,amount_cents from transactions "
                              "where status='proposto' and description like '%generico (da identificare)%'").fetchall():
        if a in payin3:
            desc, cat, sh = payin3[a]
            kind = "spesa_condivisa" if sh else "spesa_personale"
            cur.execute("update transactions set description=?,category=?,shared=?,kind=?,status='confermato' where id=?",
                        (desc, cat, sh, kind, tid))

    # 7. Conferma blocco ovvio + categorie entrate
    cur.execute("update transactions set category='RIMBORSI / ENTRATE VARIE' "
                "where status='proposto' and kind='entrata' and (category is null or category='AFFITTO')")
    cur.execute("update transactions set category='MEMBER TRANSFERS' where status='proposto' and kind='member_transfer'")
    cur.execute("update transactions set status='confermato' "
                "where status='proposto' and kind in ('entrata','giroconto','investimento','member_transfer')")

    # 8. Bonifici al member B da banca (apr+) -> giroconti (non contano nel saldo)
    cur.execute("update transactions set kind='giroconto', category='GIROCONTO' "
                "where kind='member_transfer' and source='banca'")

    # 9. Import bonifici storici dal foglio Excel "Bonifici" (16 righe, netto 1526,27).
    #    Salta il "01/04 Spese 300" (doppione del movimento banca +300) e riclassifica
    #    quel movimento banca da entrata -> member_transfer.
    import datetime
    import hashlib

    import openpyxl
    wb = openpyxl.load_workbook(EXCEL, data_only=True)
    ws = wb["Bonifici"]
    rows = [[ws.cell(r, col).value for col in range(1, 6)] for r in range(1, ws.max_row + 1)]

    def isdata(r):
        return (r[0] not in (None, "") and r[2] not in (None, "") and r[0] != "Data"
                and "TOTALE" not in str(r[0]) and "Totale" not in str(r[0]) and "NETTO" not in str(r[0]))

    def pdate(v):
        if isinstance(v, (datetime.date, datetime.datetime)):
            return v.date() if isinstance(v, datetime.datetime) else v
        g, m, y = str(v).split("/")
        return datetime.date(int(y), int(m), int(g))

    for r in [x for x in rows if isdata(x)]:
        d, desc, cents = pdate(r[0]), str(r[1]), round(r[2] * 100)
        src = "screenshot" if str(r[3]).lower() == "screenshot" else "banca"
        if d == datetime.date(2026, 4, 1) and cents == 30000:
            continue  # doppione del movimento banca +300
        h = hashlib.sha256(f"{d}|{desc.strip().lower()}|{cents}|{src}|0".encode()).hexdigest()
        if cur.execute("select 1 from transactions where raw_hash=?", (h,)).fetchone():
            continue
        cur.execute("insert into transactions(date,description,amount_cents,source,category,kind,shared,payer,status,raw_hash,note) "
                    "values(?,?,?,?,?,?,?,?,?,?,?)",
                    (d.isoformat(), desc, cents, src, "MEMBER TRANSFERS", "member_transfer", None, "member_a", "confermato", h, "bonifico storico (Excel)"))
    # movimento banca +300 "SPESE" del 1 apr: entrata -> member_transfer
    cur.execute("update transactions set kind='member_transfer', category='MEMBER TRANSFERS' "
                "where description like 'SPESE%' and amount_cents=30000 and date='2026-04-01'")

    # 10b. Decisione utente (2026-06-15): AMAZON, CASA/ARREDAMENTO, TECNOLOGIA e
    #      Funghi sono spese PERSONALI del member A (contano ma NON si dividono col member B).
    #      Riclassifica le righe condivise di quelle categorie -> spesa_personale.
    cur.execute(
        "update transactions set kind='spesa_personale', shared=0 "
        "where kind='spesa_condivisa' and ("
        "  category like 'AMAZON%'"
        "  or category = 'CASA / ARREDAMENTO'"
        "  or category like 'TECNOLOGIA / ELETTRONICA%'"
        "  or category like '%ungh%')"
    )

    # 10. Pulizia: il flag shared non ha senso su entrate/giroconti/investimenti/bonifici
    cur.execute("update transactions set shared=null "
                "where kind in ('entrata','giroconto','investimento','member_transfer') and shared is not null")
    c.commit()
    c.close()


def _verify() -> None:
    import sqlite3
    c = sqlite3.connect(DB)
    tot = c.execute("select count(*) from transactions").fetchone()[0]
    prop = c.execute("select count(*) from transactions where status='proposto'").fetchone()[0]
    escluse = ["AMAZON", "TECNOLOGIA / ELETTRONICA (condivisa)", "ACQUISTI VARI (condivisi)"]
    rows = c.execute("select category,amount_cents from transactions where kind='spesa_condivisa'").fetchall()
    div = sum(a for cat, a in rows if not any(t in (cat or "") for t in escluse))
    net = c.execute("select coalesce(sum(amount_cents),0) from transactions where kind='member_transfer'").fetchone()[0]
    from decimal import ROUND_HALF_DOWN, Decimal
    quota = int((Decimal(div * 50) / Decimal(100)).quantize(Decimal("1"), rounding=ROUND_HALF_DOWN))
    saldo = quota - net
    print(f"transazioni: {tot}  (proposte residue: {prop})")
    print(f"divisibile condivise: {div/100:,.2f}  (atteso 12.588,43)")
    print(f"netto bonifici member B: {net/100:,.2f}  (atteso 1.526,27)")
    print(f"SALDO 50/50 member B deve: {saldo/100:,.2f}  (atteso 4.767,94)")
    c.close()


if __name__ == "__main__":
    if DB.exists():
        DB.unlink()
    _orm_steps()
    _suggest_classify()
    _sql_steps()
    _verify()
