# home_expense_splitter/store/tables.py
"""Schema of the divider's DB.

Owned and written here: `settlements`, `reimbursements`.
Archive, read-only: `transactions`, `merchant_map`, `categories`, `imports`, `tags`,
`transaction_tags` — the historical ledger, moved to the finance node (issue #4, Finance#1).
Kept (never dropped) for parity checks and history; nothing in this node writes them.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import CheckConstraint, Index, String, Integer, Boolean, Date, UniqueConstraint, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Transaction(Base):
    __tablename__ = "transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str] = mapped_column(String)
    amount_cents: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String)
    category: Mapped[str | None] = mapped_column(String, nullable=True)
    kind: Mapped[str | None] = mapped_column(String, nullable=True)
    shared: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    payer: Mapped[str] = mapped_column(String, default="member_a")
    status: Mapped[str] = mapped_column(String, default="proposto")
    raw_hash: Mapped[str] = mapped_column(String)
    note: Mapped[str | None] = mapped_column(String, nullable=True)
    payment_method: Mapped[str | None] = mapped_column(String, nullable=True)
    buoni_cents: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    recon_status: Mapped[str] = mapped_column(String, default="nessuna", server_default="nessuna", nullable=False)
    recon_source: Mapped[str | None] = mapped_column(String, nullable=True)
    # Explicit member B share in basis points (0..10000), set by whoever computed it
    # (e.g. Health on real doses). NULL = house rule from split_config.toml.
    member_b_share_bp: Mapped[int | None] = mapped_column(Integer, nullable=True)
    visibility: Mapped[str] = mapped_column(
        String(7), nullable=False, default="private", server_default="private"
    )
    __table_args__ = (
        UniqueConstraint("raw_hash", name="uq_transactions_raw_hash"),
        CheckConstraint("visibility IN ('public', 'private')", name="ck_transactions_visibility"),
        CheckConstraint(
            "member_b_share_bp IS NULL OR member_b_share_bp BETWEEN 0 AND 10000",
            name="ck_transactions_member_b_share_bp",
        ),
        Index("ix_transactions_visibility", "visibility"),
    )


class MerchantMap(Base):
    __tablename__ = "merchant_map"
    id: Mapped[int] = mapped_column(primary_key=True)
    pattern: Mapped[str] = mapped_column(String, unique=True)
    category: Mapped[str] = mapped_column(String)
    kind: Mapped[str] = mapped_column(String)
    shared: Mapped[bool] = mapped_column(Boolean, default=False)
    hits: Mapped[int] = mapped_column(Integer, default=1)


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    kind: Mapped[str] = mapped_column(String)
    excluded_from_split: Mapped[bool] = mapped_column(Boolean, default=False)


class Settlement(Base):
    __tablename__ = "settlements"
    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[date | None] = mapped_column(Date, nullable=True)
    member_b_owes_cents: Mapped[int] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(String, nullable=True)
    visibility: Mapped[str] = mapped_column(
        String(7), nullable=False, default="private", server_default="private"
    )
    __table_args__ = (
        CheckConstraint("visibility IN ('public', 'private')", name="ck_settlements_visibility"),
        Index("ix_settlements_visibility", "visibility"),
    )


class Reimbursement(Base):
    """Divider state: a shared expense member B already paid back (status `rimborsato`).

    Keyed by the ledger's `raw_hash`, so it survives the ledger moving to `finance`,
    which only knows `proposto|confermato`.
    """

    __tablename__ = "reimbursements"
    raw_hash: Mapped[str] = mapped_column(String, primary_key=True)
    at: Mapped[date | None] = mapped_column(Date, nullable=True)
    note: Mapped[str | None] = mapped_column(String, nullable=True)


class ImportLog(Base):
    __tablename__ = "imports"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_file: Mapped[str] = mapped_column(String)
    rows: Mapped[int] = mapped_column(Integer)
    at: Mapped[date | None] = mapped_column(Date, nullable=True)


class KvState(Base):
    __tablename__ = "kv_state"
    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(String)


class Tag(Base):
    __tablename__ = "tags"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    color: Mapped[str | None] = mapped_column(String, nullable=True)
    visibility: Mapped[str] = mapped_column(
        String(7), nullable=False, default="private", server_default="private"
    )
    __table_args__ = (
        CheckConstraint("visibility IN ('public', 'private')", name="ck_tags_visibility"),
        Index("ix_tags_visibility", "visibility"),
    )


class TransactionTag(Base):
    __tablename__ = "transaction_tags"
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )
