from datetime import date
from home_expense_splitter.store.tables import Transaction


def test_can_persist_transaction(session):
    t = Transaction(
        date=date(2026, 1, 13),
        description="Farine (bonifico)",
        amount_cents=18690,
        source="banca",
        category="SUPERMERCATO / ALIMENTARI",
        kind="spesa_condivisa",
        shared=True,
        payer="member_a",
        status="confermato",
        raw_hash="abc123",
    )
    session.add(t)
    session.commit()
    assert t.id is not None
    assert session.query(Transaction).count() == 1
