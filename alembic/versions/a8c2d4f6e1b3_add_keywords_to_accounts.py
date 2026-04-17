"""add keywords to accounts

Revision ID: a8c2d4f6e1b3
Revises: e1f2a3b4c5d6
Create Date: 2026-04-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a8c2d4f6e1b3"
down_revision: Union[str, None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("accounts", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("keywords", sa.Text(), nullable=False, server_default="")
        )


def downgrade() -> None:
    with op.batch_alter_table("accounts", schema=None) as batch_op:
        batch_op.drop_column("keywords")
