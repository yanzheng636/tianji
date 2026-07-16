"""add chat sessions

Revision ID: a1b2c3d4e5f6
Revises: fd157a1fa9f2
Create Date: 2026-07-16 09:00:00.000000
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'a1b2c3d4e5f6'
down_revision: str | None = 'fd157a1fa9f2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'chat_sessions',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('user_id', sa.String(length=32), nullable=False),
        sa.Column('title', sa.String(length=60), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_chat_session_user_updated', 'chat_sessions', ['user_id', 'updated_at'], unique=False)

    # 先加可空列，回填历史后再收紧为非空。
    op.add_column('chat_messages', sa.Column('session_id', sa.String(length=32), nullable=True))

    # 每个有历史消息的用户，聚合出一条「历史对话」会话（id = md5(user_id)，稳定且唯一）。
    op.execute(
        """
        INSERT INTO chat_sessions (id, user_id, title, created_at, updated_at)
        SELECT md5(user_id), user_id, '历史对话', MIN(created_at), MAX(created_at)
        FROM chat_messages
        GROUP BY user_id
        """
    )
    # 旧消息全部归入本用户的历史会话。
    op.execute("UPDATE chat_messages SET session_id = md5(user_id) WHERE session_id IS NULL")

    op.alter_column('chat_messages', 'session_id', existing_type=sa.String(length=32), nullable=False)
    op.create_foreign_key(
        'fk_chat_messages_session', 'chat_messages', 'chat_sessions',
        ['session_id'], ['id'], ondelete='CASCADE',
    )
    op.create_index('ix_chat_session_created', 'chat_messages', ['session_id', 'created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_chat_session_created', table_name='chat_messages')
    op.drop_constraint('fk_chat_messages_session', 'chat_messages', type_='foreignkey')
    op.drop_column('chat_messages', 'session_id')
    op.drop_index('ix_chat_session_user_updated', table_name='chat_sessions')
    op.drop_table('chat_sessions')
