"""Pre-classificazione assistita (batch) delle spese-carta in stato 'proposto'.

Uso:
    python scripts/utility/suggest_card_classification.py            # mostra + scrive TSV
    python scripts/utility/suggest_card_classification.py --apply    # applica il TSV (eventualmente corretto a mano)

Il TSV `data/review/card_suggestions.tsv` ha una riga per transazione proposta
(non-PayPal, kind spesa_*). Colonne editabili: `category`, `shared` (1/0), `kind`.
In `--apply` ogni riga viene confermata via repo.resolve_proposal e il merchant
(token normalizzato) viene appreso in merchant_map per i prossimi import.
"""
from __future__ import annotations

import argparse
import csv
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "data" / "conti.sqlite"
TSV = ROOT / "data" / "review" / "card_suggestions.tsv"

# (substring in MAIUSCOLO, categoria, shared) — prima corrispondenza vince.
RULES: list[tuple[str, str, bool]] = [
    # Affitto (era finito come spesa_personale dal bonifico) -> condiviso
    ("AFFITTO", "AFFITTO", True),
    # Merchant PayPal noti (dettagliati da import-paypal)
    ("KORO", "KORO ALIMENTARI (PayPal)", True),
    ("MATTIA BRUNI", "VERDURE MATTIA BRUNI (PayPal)", True),
    ("RYANAIR", "VIAGGI - VOLI/PRENOTAZIONI", True),
    ("BOOKING", "VIAGGI - VOLI/PRENOTAZIONI", True),
    ("AIRBNB", "VIAGGI - VOLI/PRENOTAZIONI", True),
    ("DISNEY", "ABBONAMENTI PERSONALI", False),
    ("深度求索", "ABBONAMENTI PERSONALI", False),  # DeepSeek (API AI)
    # Supermercato / alimentari
    ("UNICOOP", "SUPERMERCATO / ALIMENTARI", True),
    ("CONVENIENZA", "SUPERMERCATO / ALIMENTARI", True),
    ("BAVICCHI", "SUPERMERCATO / ALIMENTARI", True),
    ("ACQUA & SAPONE", "SUPERMERCATO / ALIMENTARI", True),
    ("MENCHETTI", "SUPERMERCATO / ALIMENTARI", True),
    ("AGRIDEE", "SUPERMERCATO / ALIMENTARI", True),
    ("GALA", "SUPERMERCATO / ALIMENTARI", True),
    # Animali / Micia
    ("MIGLIO+GRANO", "ANIMALI / MICIA (condivisa)", True),
    # Carburante / stazioni di servizio
    ("STAZIONE DI SERVIZIO", "CARBURANTE (quotidiano)", False),
    ("STAZIONE Q8", "CARBURANTE (quotidiano)", False),
    ("AUTOMIGLIORGAS", "CARBURANTE (quotidiano)", False),
    ("IP PV", "CARBURANTE (quotidiano)", False),
    ("NILDE IOTTI", "CARBURANTE (quotidiano)", False),
    ("PV 44714", "CARBURANTE (quotidiano)", False),
    ("PV4894", "CARBURANTE (quotidiano)", False),
    # Auto / trasporti (pedaggi, parcheggi, autogrill)
    ("ASPIT", "AUTO / TRASPORTI", False),
    ("AUTOGRILL", "AUTO / TRASPORTI", False),
    ("PARKOS", "AUTO / TRASPORTI", False),
    # Salute / farmacia
    ("AFAM", "SALUTE / FARMACIA", False),
    ("OSTEOPATA", "SALUTE / FARMACIA", False),
    ("FARMAC", "SALUTE / FARMACIA", False),
    ("SIDAP", "SALUTE / FARMACIA", False),
    # Abbigliamento / moda
    ("MAURY", "ABBIGLIAMENTO / MODA", False),
    ("VINTED", "ABBIGLIAMENTO / MODA", False),
    ("BARBERIA", "ABBIGLIAMENTO / MODA", False),
    # Viaggi
    ("RENTALCARS", "VIAGGI - VOLI/PRENOTAZIONI", True),
    ("TRIP.COM", "VIAGGI - VOLI/PRENOTAZIONI", True),
    # Bollette / utenze
    ("STARLINK", "BOLLETTE / UTENZE", True),
    ("ABRUZZO ENERGY", "BOLLETTE / UTENZE", True),
    ("VIMALGEST", "BOLLETTE / UTENZE", True),
    # Abbonamenti personali / telefono / cloud
    ("ANTHROPIC", "ABBONAMENTI PERSONALI", False),
    ("GOOGLE CLOUD", "ABBONAMENTI PERSONALI", False),
    ("HO-MOBILE", "ABBONAMENTI PERSONALI", False),
    ("GOOGLE PLAY", "GOOGLE PLAY APPS", True),
    # Spettacoli / eventi
    ("SHOTGUN", "SPETTACOLI / CINEMA", True),
    ("FESTIVAL", "SPETTACOLI / CINEMA", True),
    ("FONDAZIONE IL GIARDINO", "SPETTACOLI / CINEMA", True),
    # Amazon -> personale (scelta utente 2026-06-14: acquisti misti, non a carico del member B)
    ("AMZN", "AMAZON (personale)", False),
    ("AMAZON.IT", "AMAZON (personale)", False),
    # Ristoranti / bar (locale)
    ("RESTAURANT", "RISTORANTI / BAR (locale)", True),
    ("RISTORANTE", "RISTORANTI / BAR (locale)", True),
    ("RISTO", "RISTORANTI / BAR (locale)", True),
    ("TRATTORIA", "RISTORANTI / BAR (locale)", True),
    ("PIZZERIA", "RISTORANTI / BAR (locale)", True),
    ("STREET FOOD", "RISTORANTI / BAR (locale)", True),
    ("MARGHEREAT", "RISTORANTI / BAR (locale)", True),
    ("BELLA NAPOLI", "RISTORANTI / BAR (locale)", True),
    ("MORE BAR", "RISTORANTI / BAR (locale)", True),
    ("BAR ", "RISTORANTI / BAR (locale)", True),
    ("YOGURTERIA", "RISTORANTI / BAR (locale)", True),
    ("PASTICCERIA", "RISTORANTI / BAR (locale)", True),
    ("DELIZIA", "RISTORANTI / BAR (locale)", True),
    ("NATOMA", "RISTORANTI / BAR (locale)", True),
    ("MANCINI", "RISTORANTI / BAR (locale)", True),
    ("CARLETTI", "RISTORANTI / BAR (locale)", True),
    ("FERRI DI FER", "RISTORANTI / BAR (locale)", True),
    ("D161 TREVI", "RISTORANTI / BAR (locale)", True),
    ("RESTAURANT SUN", "RISTORANTI / BAR (locale)", True),
    ("STILNOVO", "RISTORANTI / BAR (locale)", True),
    ("DELLO SPORT", "RISTORANTI / BAR (locale)", True),
    ("PLANET 71", "RISTORANTI / BAR (locale)", True),
]


def merchant_token(desc: str) -> str:
    """Token merchant normalizzato (pattern per merchant_map): toglie codici/citta finali."""
    d = re.sub(r"\s+", " ", desc).strip()
    d = d.split(" — ")[0]  # toglie "... — Nome" dei bonifici
    d = re.sub(r"\*.*$", "", d)  # toglie "AMZN Mktp IT*NA56..." -> "AMZN Mktp IT"
    return d.strip()


def suggest(desc: str) -> tuple[str, bool]:
    up = re.sub(r"\s+", " ", desc).upper()
    for needle, cat, shared in RULES:
        if needle in up:
            return cat, shared
    return "ALTRO PERSONALE", False  # default prudente: personale


def load_rows() -> list[tuple[int, str, str, int]]:
    c = sqlite3.connect(DB)
    rows = c.execute(
        "select id,date,description,amount_cents from transactions "
        "where status='proposto' and kind like 'spesa_%' and description not like 'PayPal%' "
        "order by amount_cents desc"
    ).fetchall()
    c.close()
    return rows


def write_tsv(rows) -> None:
    TSV.parent.mkdir(parents=True, exist_ok=True)
    with TSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["id", "date", "description", "amount_eur", "category", "shared", "kind", "learn_pattern"])
        for tid, d, desc, a in rows:
            cat, shared = suggest(desc)
            kind = "spesa_condivisa" if shared else "spesa_personale"
            w.writerow([tid, d, desc, f"{a/100:.2f}", cat, 1 if shared else 0, kind, merchant_token(desc)])


def show(rows) -> None:
    by_cat: dict[tuple[str, bool], list[float]] = defaultdict(list)
    for _tid, _d, desc, a in rows:
        cat, shared = suggest(desc)
        by_cat[(cat, shared)].append(a / 100)
    print(f"{'CATEGORIA':40s} {'C/P':3s} {'n':>3s} {'totale':>10s}")
    for (cat, shared), amts in sorted(by_cat.items(), key=lambda kv: -sum(kv[1])):
        flag = "COND" if shared else "pers"
        print(f"{cat:40s} {flag:4s} {len(amts):>3d} {sum(amts):>10,.2f}")
    print(f"\nTOT proposte carta: {len(rows)}  somma {sum(a/100 for *_x, a in rows):,.2f} EUR")
    print(f"TSV scritto: {TSV.relative_to(ROOT)}")


def apply_tsv() -> None:
    sys.path.insert(0, str(ROOT / "backend"))
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from home_expense_splitter.store import repo
    from home_expense_splitter.store.tables import Base, Transaction

    engine = create_engine(f"sqlite:///{DB}")
    Base.metadata.create_all(engine)
    session = sessionmaker(engine)()
    n = 0
    with TSV.open(encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            txn = session.get(Transaction, int(r["id"]))
            if txn is None or txn.status != "proposto":
                continue
            shared = r["shared"].strip() in ("1", "true", "True")
            repo.resolve_proposal(
                session, txn, category=r["category"].strip(),
                kind=r["kind"].strip(), shared=shared,
                learn_pattern=(r["learn_pattern"].strip() or None),
            )
            n += 1
    session.commit()
    session.close()
    print(f"Applicate {n} proposte (confermate + merchant appresi).")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if args.apply:
        apply_tsv()
    else:
        rows = load_rows()
        write_tsv(rows)
        show(rows)
