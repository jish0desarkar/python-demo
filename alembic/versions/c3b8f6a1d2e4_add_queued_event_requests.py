"""add queued event requests

Revision ID: c3b8f6a1d2e4
Revises: b7e1e3b1c9a2
Create Date: 2026-04-15 13:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3b8f6a1d2e4"
down_revision: Union[str, None] = "b7e1e3b1c9a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "queued_event_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("error_message", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("queued_event_requests", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_queued_event_requests_account_id"),
            ["account_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_queued_event_requests_event_id"),
            ["event_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_queued_event_requests_source_id"),
            ["source_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_queued_event_requests_status"),
            ["status"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("queued_event_requests", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_queued_event_requests_status"))
        batch_op.drop_index(batch_op.f("ix_queued_event_requests_source_id"))
        batch_op.drop_index(batch_op.f("ix_queued_event_requests_event_id"))
        batch_op.drop_index(batch_op.f("ix_queued_event_requests_account_id"))
    op.drop_table("queued_event_requests")
