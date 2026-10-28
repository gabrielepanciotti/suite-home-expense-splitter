# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from home_expense_splitter.store.tables import Base

# Device-local env (loaded from the untracked .env by config.py) must never
# leak into tests: tests always run against the generic defaults.
_DEVICE_LOCAL_VARS = [
    "MEMBER_ALIASES_JSON",
    "BANK_SELF_NAMES",
    "BANK_MEMBER_B_NAMES",
    "LEGACY_SHARED_SHEET",
    "LEGACY_PERSONAL_SHEET",
    "DEPERSONALIZE_TOKENS_JSON",
    "HOMEEXPENSESPLITTER_SPLIT_SOURCE",
    "FINANCE_URL",
]


@pytest.fixture(autouse=True)
def _neutral_device_env(monkeypatch):
    for var in _DEVICE_LOCAL_VARS:
        monkeypatch.delenv(var, raising=False)
    # Tests seed the local archive, so they split on it. Code default is `finance`
    # (see test_source_for_default_is_finance); tests opt into it explicitly.
    monkeypatch.setenv("HOMEEXPENSESPLITTER_SPLIT_SOURCE", "ledger")


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    try:
        yield s
    finally:
        s.close()
