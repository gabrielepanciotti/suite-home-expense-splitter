"""depersonalize member identifiers in schema and data

Member ids become generic (member_a / member_b), the per-person transfer kind
becomes `member_transfer`, and existing rows are renamed additively (UPDATE
only — no drops, no deletes). This file is tracked, so it must not contain the
legacy personal tokens either: legacy values are matched by pattern/inspection,
and the free-text scrub reads its token list from the untracked .env
(DEPERSONALIZE_TOKENS_JSON — see .env.example for fictional samples).

Revision ID: 0003
Revises: 0002
"""
from __future__ import annotations

import json
import os

import sqlalchemy as sa
from alembic import context, op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    # 1. Legacy transfer kind (the only historical `bonifico_*` value) → generic.
    for table in ("transactions", "merchant_map", "categories"):
        op.execute(
            f"UPDATE {table} SET kind = 'member_transfer' WHERE kind LIKE 'bonifico\\_%' ESCAPE '\\'"
        )

    # 2. Legacy payer short-ids → generic member ids.
    op.execute("UPDATE transactions SET payer = 'member_a' WHERE payer = 'gab'")
    op.execute(
        "UPDATE transactions SET payer = 'member_b' "
        "WHERE payer NOT IN ('member_a', 'member_b')"
    )

    # 3. Legacy transfers category label → generic.
    op.execute(
        "UPDATE transactions SET category = 'MEMBER TRANSFERS' WHERE category LIKE 'BONIFICI G%'"
    )
    op.execute(
        "UPDATE categories SET name = 'MEMBER TRANSFERS' WHERE name LIKE 'BONIFICI G%'"
    )

    # 4. settlements: rename the legacy per-person balance column to
    #    member_b_owes_cents. Inspection-based (no legacy identifier in this
    #    tracked file); online-only, offline --sql runs skip it.
    if not context.is_offline_mode():
        inspector = sa.inspect(op.get_bind())
        cols = [c["name"] for c in inspector.get_columns("settlements")]
        legacy = [c for c in cols if c.endswith("_owes_cents") and c != "member_b_owes_cents"]
        if legacy:
            op.alter_column("settlements", legacy[0], new_column_name="member_b_owes_cents")

    # 5. Scrub personal-name tokens from row text (descriptions/notes).
    #    Token list comes from the device-local untracked .env; PostgreSQL only
    #    (\m/\M word boundaries never touch words merely containing the token).
    if not context.is_offline_mode() and _is_postgres():
        raw = os.environ.get("DEPERSONALIZE_TOKENS_JSON", "")
        tokens: dict[str, list[str]] = json.loads(raw) if raw else {}
        for replacement, patterns in tokens.items():
            for token in patterns:
                pattern = r"\m" + token.replace("'", "''") + r"\M"
                repl = replacement.replace("'", "''")
                op.execute(
                    "UPDATE transactions SET description = "
                    f"regexp_replace(description, '{pattern}', '{repl}', 'gi') "
                    f"WHERE description ~* '{pattern}'"
                )
                op.execute(
                    "UPDATE transactions SET note = "
                    f"regexp_replace(note, '{pattern}', '{repl}', 'gi') "
                    f"WHERE note IS NOT NULL AND note ~* '{pattern}'"
                )


def downgrade() -> None:
    # One-way by design: generic ids stay; personal names are never reintroduced.
    pass
