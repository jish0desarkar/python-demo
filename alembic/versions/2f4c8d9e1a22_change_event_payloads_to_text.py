"""change event payloads to text

Revision ID: 2f4c8d9e1a22
Revises: 9e2d6d7f4a11
Create Date: 2026-04-15 16:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2f4c8d9e1a22"
down_revision: Union[str, None] = "9e2d6d7f4a11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("events", schema=None) as batch_op:
        batch_op.alter_column(
            "payload",
            existing_type=sa.JSON(),
            type_=sa.Text(),
            existing_nullable=False,
        )

    with op.batch_alter_table("queued_event_requests", schema=None) as batch_op:
        batch_op.alter_column(
            "payload",
            existing_type=sa.JSON(),
            type_=sa.Text(),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("queued_event_requests", schema=None) as batch_op:
        batch_op.alter_column(
            "payload",
            existing_type=sa.Text(),
            type_=sa.JSON(),
            existing_nullable=False,
        )

    with op.batch_alter_table("events", schema=None) as batch_op:
        batch_op.alter_column(
            "payload",
            existing_type=sa.Text(),
            type_=sa.JSON(),
            existing_nullable=False,
        )
