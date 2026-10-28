"""create role-aware UI preferences

Revision ID: 0006_ui_preference
Revises: 0005
Create Date: 2026-10-26
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op
from suite_backend_core.vista import create_ui_preference_table

revision: str = "0006_ui_preference"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Offline SQL has a MockConnection, which SQLAlchemy cannot inspect.
    if context.is_offline_mode() or not sa.inspect(op.get_bind()).has_table("ui_preference"):
        create_ui_preference_table(op)


def downgrade() -> None:
    # This migration is deliberately additive: user preferences are never dropped.
    pass
