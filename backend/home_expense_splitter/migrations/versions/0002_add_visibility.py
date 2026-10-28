"""add visibility column to domain data tables

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

_TABLES = ["transactions", "settlements", "tags"]


def _is_postgres() -> bool:
    bind = op.get_bind()
    return bind.dialect.name == "postgresql"


def upgrade() -> None:
    # ADD COLUMN is supported natively by both SQLite and PostgreSQL — no batch needed.
    # This keeps the generated SQL fully additive (no DROP TABLE) for the offline test.
    for table in _TABLES:
        op.add_column(
            table,
            sa.Column(
                "visibility",
                sa.String(7),
                nullable=False,
                server_default="private",
            ),
        )
        # CHECK constraint: only meaningful (and enforceable) on PostgreSQL.
        # SQLite does not support ADD CONSTRAINT via ALTER TABLE.
        if _is_postgres():
            op.create_check_constraint(
                f"ck_{table}_visibility",
                table,
                "visibility IN ('public', 'private')",
            )
        op.create_index(f"ix_{table}_visibility", table, ["visibility"])


def downgrade() -> None:
    # DROP COLUMN requires batch mode on SQLite (copy-and-move strategy).
    # Downgrade is not exercised in the --sql offline test so batch is safe here.
    for table in reversed(_TABLES):
        op.drop_index(f"ix_{table}_visibility", table_name=table)
        if _is_postgres():
            op.drop_constraint(f"ck_{table}_visibility", table, type_="check")
        with op.batch_alter_table(table) as b:
            b.drop_column("visibility")
