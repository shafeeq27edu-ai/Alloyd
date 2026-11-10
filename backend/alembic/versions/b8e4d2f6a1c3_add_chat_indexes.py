"""add chat lookup indexes

Revision ID: b8e4d2f6a1c3
Revises: a7f3c1d9e5b2
Create Date: 2026-11-10 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'b8e4d2f6a1c3'
down_revision: Union[str, Sequence[str], None] = 'a7f3c1d9e5b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index('ix_conversations_user_id', 'conversations', ['user_id'])
    op.create_index('ix_messages_conversation_id', 'messages', ['conversation_id'])


def downgrade() -> None:
    op.drop_index('ix_messages_conversation_id', table_name='messages')
    op.drop_index('ix_conversations_user_id', table_name='conversations')
