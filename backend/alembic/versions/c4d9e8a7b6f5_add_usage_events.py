"""add usage events

Revision ID: c4d9e8a7b6f5
Revises: b8e4d2f6a1c3
Create Date: 2026-11-14 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'c4d9e8a7b6f5'
down_revision: Union[str, Sequence[str], None] = 'b8e4d2f6a1c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'usage_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('conversation_id', sa.String(length=36), nullable=False),
        # Deliberately not a foreign key: usage outlives a regenerated answer.
        sa.Column('message_id', sa.String(length=36), nullable=True),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('mode', sa.String(length=16), nullable=False),
        sa.Column('category', sa.String(length=32), nullable=True),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('error_code', sa.String(length=32), nullable=True),
        sa.Column('fallback_from', sa.String(length=120), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=False),
        sa.Column('input_tokens', sa.Integer(), nullable=True),
        sa.Column('output_tokens', sa.Integer(), nullable=True),
        sa.Column('token_source', sa.String(length=16), nullable=True),
        sa.Column('estimated_cost_usd', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_usage_events_user_id', 'usage_events', ['user_id'])
    op.create_index('ix_usage_events_conversation_id', 'usage_events', ['conversation_id'])
    op.create_index('ix_usage_events_message_id', 'usage_events', ['message_id'])
    op.create_index('ix_usage_events_created_at', 'usage_events', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_usage_events_created_at', table_name='usage_events')
    op.drop_index('ix_usage_events_message_id', table_name='usage_events')
    op.drop_index('ix_usage_events_conversation_id', table_name='usage_events')
    op.drop_index('ix_usage_events_user_id', table_name='usage_events')
    op.drop_table('usage_events')
