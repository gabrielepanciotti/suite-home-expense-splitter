# home_expense_splitter_bot/bot.py
"""Bot Telegram minimale per HomeExpenseSplitter (homeexpensesplitter).

Comandi:
  /start  — messaggio di benvenuto + elenco comandi
  /saldo  — quanto il member B deve al member A (riusa compute_split, sola lettura)
  /spese  — top categorie divisibili del mese corrente (sola lettura)

Token letto da .env (HOMEEXPENSESPLITTER_TELEGRAM_TOKEN). Nessun token hardcoded.
Lancio: python -m home_expense_splitter_bot.bot
"""
from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from home_expense_splitter.config import PROJECT_ROOT, load_split_config, member_names
from home_expense_splitter.split.engine import compute_split
from home_expense_splitter_backend.db import SessionLocal

load_dotenv(PROJECT_ROOT / ".env")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("home_expense_splitter_bot")

TOKEN_ENV = "HOMEEXPENSESPLITTER_TELEGRAM_TOKEN"


def _euro(cents: int) -> str:
    return f"{cents / 100:.2f} EUR"


def _summary_text() -> str:
    cfg = load_split_config()
    session = SessionLocal()
    try:
        res = compute_split(
            session,
            member_a_pct=cfg["percentuali"]["member_a"],
            member_b_pct=cfg["percentuali"]["member_b"],
            escluse=cfg["escluse"],
        )
    finally:
        session.close()
    name_a, name_b = member_names(cfg)
    return (
        "Saldo HomeExpenseSplitter\n"
        f"- Spese divisibili: {_euro(res['divisible_cents'])}\n"
        f"- Quota {name_b} ({res['member_b_pct']}%): {_euro(res['member_b_quota_cents'])}\n"
        f"- Bonifici {name_b} gia versati: {_euro(res['net_bonifici_cents'])}\n"
        f"= {name_b} deve a {name_a}: {_euro(res['saldo_cents'])}"
    )


def _spese_text(top: int = 8) -> str:
    cfg = load_split_config()
    session = SessionLocal()
    try:
        res = compute_split(
            session,
            member_a_pct=cfg["percentuali"]["member_a"],
            member_b_pct=cfg["percentuali"]["member_b"],
            escluse=cfg["escluse"],
        )
    finally:
        session.close()
    rows = res.get("per_category", [])[:top]
    lines = "\n".join(f"- {cat}: {_euro(amount)}" for cat, amount in rows)
    return "Spese divisibili per categoria:\n" + (lines or "(nessuna)")


async def cmd_start(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "HomeExpenseSplitter bot.\n"
        "Comandi disponibili:\n"
        "/saldo - saldo della divisione spese\n"
        "/spese - top categorie divisibili"
    )


async def cmd_saldo(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(_summary_text())


async def cmd_spese(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(_spese_text())


def build_application(token: str) -> Application:
    """Costruisce l'Application con gli handler (testabile senza avviare il polling)."""
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("saldo", cmd_saldo))
    app.add_handler(CommandHandler("spese", cmd_spese))
    return app


def main() -> None:
    token = os.environ.get(TOKEN_ENV)
    if not token:
        raise SystemExit(
            f"{TOKEN_ENV} non impostato in .env — aggiungi la riga "
            f"{TOKEN_ENV}=<token del bot> (mai committare il token)."
        )
    logger.info("Avvio bot HomeExpenseSplitter (polling)...")
    build_application(token).run_polling()


if __name__ == "__main__":
    main()
