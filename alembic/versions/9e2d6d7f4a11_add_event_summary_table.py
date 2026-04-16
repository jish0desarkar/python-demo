"""add event summary table

Revision ID: 9e2d6d7f4a11
Revises: c3b8f6a1d2e4
Create Date: 2026-04-15 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9e2d6d7f4a11"
down_revision: Union[str, None] = "c3b8f6a1d2e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "event_summary",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("summary", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )
    with op.batch_alter_table("event_summary", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_event_summary_account_id"),
            ["account_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_event_summary_event_id"),
            ["event_id"],
            unique=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("event_summary", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_event_summary_event_id"))
        batch_op.drop_index(batch_op.f("ix_event_summary_account_id"))
    op.drop_table("event_summary")
