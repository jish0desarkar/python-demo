"""convert sources to many-to-many

Revision ID: b7e1e3b1c9a2
Revises: f15b9bbf547e
Create Date: 2026-04-15 11:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7e1e3b1c9a2"
down_revision: Union[str, None] = "f15b9bbf547e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("event_logs")
    op.drop_table("events")
    op.drop_table("sources")

    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", name="uq_sources_key"),
    )
    op.create_table(
        "account_sources",
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("account_id", "source_id"),
    )
    with op.batch_alter_table("account_sources", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_account_sources_account_id"), ["account_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_account_sources_source_id"), ["source_id"], unique=False)

    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("events", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_events_account_id"), ["account_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_events_source_id"), ["source_id"], unique=False)

    op.create_table(
        "event_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("event_logs", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_event_logs_event_id"), ["event_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_event_logs_source_id"), ["source_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("event_logs", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_event_logs_source_id"))
        batch_op.drop_index(batch_op.f("ix_event_logs_event_id"))
    op.drop_table("event_logs")

    with op.batch_alter_table("events", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_events_source_id"))
        batch_op.drop_index(batch_op.f("ix_events_account_id"))
    op.drop_table("events")

    with op.batch_alter_table("account_sources", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_account_sources_source_id"))
        batch_op.drop_index(batch_op.f("ix_account_sources_account_id"))
    op.drop_table("account_sources")

    op.drop_table("sources")

    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", "key", name="uq_sources_account_key"),
    )
    with op.batch_alter_table("sources", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_sources_account_id"), ["account_id"], unique=False)

    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("events", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_events_account_id"), ["account_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_events_source_id"), ["source_id"], unique=False)

    op.create_table(
        "event_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("event_logs", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_event_logs_event_id"), ["event_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_event_logs_source_id"), ["source_id"], unique=False)
