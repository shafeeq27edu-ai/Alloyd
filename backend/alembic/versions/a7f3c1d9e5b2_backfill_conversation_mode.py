"""backfill conversations.mode

Revision ID: a7f3c1d9e5b2
Revises: 677b3b6bbe6a
Create Date: 2026-11-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'a7f3c1d9e5b2'
down_revision: Union[str, Sequence[str], None] = '677b3b6bbe6a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Treat conversations created before routing modes as Auto."""
    op.execute("UPDATE conversations SET mode = 'auto' WHERE mode IS NULL")


def downgrade() -> None:
    """No-op: the original NULL rows cannot be distinguished from Auto rows."""
    pass
