"""add rules and event_filter_logs tables

Revision ID: a1b2c3d4e5f6
Revises: 2f4c8d9e1a22
Create Date: 2026-04-16 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "2f4c8d9e1a22"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("rule_text", sa.Text(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("rules", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_rules_source_id"), ["source_id"], unique=False)

    op.create_table(
        "event_filter_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("rule_id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["rule_id"], ["rules.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("event_filter_logs", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_event_filter_logs_rule_id"), ["rule_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_event_filter_logs_event_id"), ["event_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("event_filter_logs", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_event_filter_logs_event_id"))
        batch_op.drop_index(batch_op.f("ix_event_filter_logs_rule_id"))

    op.drop_table("event_filter_logs")

    with op.batch_alter_table("rules", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_rules_source_id"))

    op.drop_table("rules")
