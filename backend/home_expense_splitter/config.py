# home_expense_splitter/config.py
from __future__ import annotations

import os
import tomllib
from pathlib import Path

from dotenv import load_dotenv

APP_ROOT = Path(__file__).resolve().parent.parent      # backend/  (in container /app/backend)
REPO_ROOT = APP_ROOT.parent                            # repo root in dev (HomeExpenseSplitter)
CONFIG_DIR = APP_ROOT / "config"                       # i TOML si spostano con home_expense_splitter/ sotto backend/
DATA_DIR = REPO_ROOT / "data"                          # sqlite resta alla root del repo (gitignored)
DB_PATH = DATA_DIR / "conti.sqlite"

# Alias retrocompat: importato da home_expense_splitter_bot/bot.py e tests/test_config.py
PROJECT_ROOT = REPO_ROOT

# DB runtime: Postgres (db `homeexpensesplitter` nel container condiviso `personal_db`) se
# HOMEEXPENSESPLITTER_DATABASE_URL è valorizzata in .env, altrimenti SQLite locale (default per
# test e per il rebuild deterministico).
load_dotenv(REPO_ROOT / ".env")
# Precedenza: DATABASE_URL generico (iniettato dal deploy/ compose Life, che punta
# al Postgres del nodo homeexpensesplitter-db su personal-net) → HOMEEXPENSESPLITTER_DATABASE_URL
# (host dev, .env) → SQLite locale (test / rebuild deterministico).
DATABASE_URL = (
    os.environ.get("DATABASE_URL")
    or os.environ.get("HOMEEXPENSESPLITTER_DATABASE_URL")
    or f"sqlite:///{DB_PATH}"
)


def load_split_config() -> dict:
    with open(CONFIG_DIR / "split_config.toml", "rb") as fh:
        return tomllib.load(fh)


def member_names(cfg: dict | None = None) -> tuple[str, str]:
    """Display names of the two household members.

    Defaults come from split_config.toml ([persone] member_a/member_b — generic
    "Member A"/"Member B"). A device-local, UNTRACKED alias layer can override
    them at runtime via the MEMBER_ALIASES_JSON env var in .env, e.g.
    MEMBER_ALIASES_JSON={"member_a": "Alice", "member_b": "Bob"}.
    Personal names must never appear in tracked files.
    """
    import json

    cfg = cfg or load_split_config()
    persone = cfg.get("persone", {})
    a = persone.get("member_a", "Member A")
    b = persone.get("member_b", "Member B")
    raw = os.environ.get("MEMBER_ALIASES_JSON", "")
    if raw:
        try:
            aliases = json.loads(raw)
            a = aliases.get("member_a", a)
            b = aliases.get("member_b", b)
        except (ValueError, AttributeError):
            pass  # malformed alias JSON: keep generic defaults
    return a, b

