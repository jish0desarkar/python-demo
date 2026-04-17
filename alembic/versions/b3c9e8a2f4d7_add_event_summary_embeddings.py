"""add event_summary_embeddings table

Revision ID: b3c9e8a2f4d7
Revises: a8c2d4f6e1b3
Create Date: 2026-04-17 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b3c9e8a2f4d7"
down_revision: Union[str, None] = "a8c2d4f6e1b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "event_summary_embeddings",
        sa.Column("model_key", sa.String(length=100), nullable=False),
        sa.Column("event_summary_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["event_summary_id"],
            ["event_summary.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("model_key", "event_summary_id"),
    )
    with op.batch_alter_table("event_summary_embeddings", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_event_summary_embeddings_event_summary_id"),
            ["event_summary_id"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("event_summary_embeddings", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_event_summary_embeddings_event_summary_id"))
    op.drop_table("event_summary_embeddings")
