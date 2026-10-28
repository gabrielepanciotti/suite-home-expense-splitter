"""add explicit per-row member B share (basis points)

A shared expense may carry its own split (e.g. Health computes 67/33 on real
doses) instead of the house rule in split_config.toml. NULL keeps the house
rule, so every existing row is unchanged. Additive only.

Revision ID: 0004
Revises: 0003
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column("member_b_share_bp", sa.Integer(), nullable=True),
    )
    # SQLite cannot ADD CONSTRAINT via ALTER TABLE; the API validates the range anyway.
    if _is_postgres():
        op.create_check_constraint(
            "ck_transactions_member_b_share_bp",
            "transactions",
            "member_b_share_bp IS NULL OR member_b_share_bp BETWEEN 0 AND 10000",
        )


def downgrade() -> None:
    if _is_postgres():
        op.drop_constraint("ck_transactions_member_b_share_bp", "transactions", type_="check")
    with op.batch_alter_table("transactions") as b:
        b.drop_column("member_b_share_bp")
