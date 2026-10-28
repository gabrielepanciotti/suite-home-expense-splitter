"""add payment_method, buoni_cents, recon cols + tags tables

Revision ID: 0001
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("transactions") as b:
        b.add_column(sa.Column("payment_method", sa.String(), nullable=True))
        b.add_column(sa.Column("buoni_cents", sa.Integer(), server_default="0", nullable=False))
        b.add_column(sa.Column("recon_status", sa.String(), server_default="nessuna", nullable=False))
        b.add_column(sa.Column("recon_source", sa.String(), nullable=True))
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column("color", sa.String(), nullable=True),
    )
    op.create_table(
        "transaction_tags",
        sa.Column("transaction_id", sa.Integer(), sa.ForeignKey("transactions.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", sa.Integer(), sa.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("transaction_tags")
    op.drop_table("tags")
    with op.batch_alter_table("transactions") as b:
        b.drop_column("recon_source")
        b.drop_column("recon_status")
        b.drop_column("buoni_cents")
        b.drop_column("payment_method")
