# home_expense_splitter_backend/db.py
"""Engine + session dependency per la dashboard.

L'engine è creato a livello di modulo da `home_expense_splitter.config.DATABASE_URL`, ma SENZA
alcuna scrittura/`create_all` all'import: la app deve restare pura. Nei test la
dependency `get_session` viene sovrascritta con `app.dependency_overrides`.
"""
from __future__ import annotations

from collections.abc import Iterator
from importlib.util import find_spec

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from suite_backend_core.vista import MemoryPreferenceStore, PreferenceStore, SqlPreferenceStore

from home_expense_splitter.config import DATABASE_URL

engine: Engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

# The node's regular data access is synchronous.  View preferences are the sole
# async consumer and use this separate engine.  SQLite uses the installed
# aiosqlite driver; local process-memory storage remains a fallback if it is
# unavailable.
_preference_engine: AsyncEngine | None = None
_preference_sessionmaker: async_sessionmaker[AsyncSession] | None = None
_memory_preference_store = MemoryPreferenceStore()


def _preference_database_url() -> str | None:
    if DATABASE_URL.startswith("sqlite://"):
        if find_spec("aiosqlite") is None:
            return None
        return DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://", 1)
    if DATABASE_URL.startswith("postgresql://"):
        # The bare scheme means psycopg2, which has no asyncio support.
        return DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
    if DATABASE_URL.startswith("postgresql+psycopg2://"):
        # psycopg2 is synchronous; the async engine requires psycopg 3.
        return DATABASE_URL.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
    return DATABASE_URL


def preference_store() -> PreferenceStore:
    """Return SQL-backed preferences, or memory storage for SQLite without aiosqlite."""
    global _preference_engine, _preference_sessionmaker
    url = _preference_database_url()
    if url is None:
        return _memory_preference_store
    if _preference_sessionmaker is None:
        _preference_engine = create_async_engine(url)
        _preference_sessionmaker = async_sessionmaker(_preference_engine, expire_on_commit=False)
    return SqlPreferenceStore(_preference_sessionmaker)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: apre una Session e la chiude a fine richiesta."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
