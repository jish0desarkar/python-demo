"""make event_filter_log rule_id nullable

Revision ID: e1f2a3b4c5d6
Revises: d5e7f8a9b0c1
Create Date: 2026-04-16 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, None] = "d5e7f8a9b0c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("event_filter_logs", schema=None) as batch_op:
        batch_op.alter_column("rule_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("event_filter_logs", schema=None) as batch_op:
        batch_op.alter_column("rule_id", existing_type=sa.Integer(), nullable=False)
