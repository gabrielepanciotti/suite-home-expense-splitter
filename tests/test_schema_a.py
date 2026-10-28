from sqlalchemy import create_engine, inspect
from home_expense_splitter.store.tables import Base, Transaction, Tag, TransactionTag


def _engine():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng


def test_transaction_has_new_columns():
    eng = _engine()
    cols = {c["name"] for c in inspect(eng).get_columns("transactions")}
    assert {"payment_method", "buoni_cents", "recon_status", "recon_source"} <= cols


def test_tag_tables_exist():
    eng = _engine()
    names = set(inspect(eng).get_table_names())
    assert {"tags", "transaction_tags"} <= names

