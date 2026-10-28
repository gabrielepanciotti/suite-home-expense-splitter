"""add reimbursements (divider-owned `rimborsato` state, keyed by raw_hash)

The ledger moves to the finance node (Life#81), which only knows
proposto|confermato. Which shared expenses member B already paid back is the
divider's own state, so it gets its own table, backfilled from the rows that
are `rimborsato` today. Additive only: transactions are not touched.

Revision ID: 0005
Revises: 0004
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reimbursements",
        sa.Column("raw_hash", sa.String(), primary_key=True),
        sa.Column("at", sa.Date(), nullable=True),
        sa.Column("note", sa.String(), nullable=True),
    )
    op.execute(
        "INSERT INTO reimbursements (raw_hash) "
        "SELECT raw_hash FROM transactions WHERE status = 'rimborsato'"
    )


def downgrade() -> None:
    op.drop_table("reimbursements")
