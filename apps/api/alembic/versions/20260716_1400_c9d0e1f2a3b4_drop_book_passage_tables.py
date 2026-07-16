"""drop book/passage tables

古籍语料改由 knowledge_wiki/graph.json 直接供数（藏经阁、问卦引用、签谱同源），
数据库不再保存语料副本。

Revision ID: c9d0e1f2a3b4
Revises: a1b2c3d4e5f6
Create Date: 2026-07-16 14:00:00.000000
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'c9d0e1f2a3b4'
down_revision: str | None = 'a1b2c3d4e5f6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index('ix_passage_book_sort', table_name='passages')
    op.drop_table('passages')
    op.drop_index(op.f('ix_books_slug'), table_name='books')
    op.drop_table('books')


def downgrade() -> None:
    # 仅恢复表结构；语料内容不可恢复（当年由 app.seed / ingest 写入，均已移除）。
    op.create_table(
        'books',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('slug', sa.String(length=40), nullable=False),
        sa.Column('char', sa.String(length=4), nullable=False),
        sa.Column('name', sa.String(length=40), nullable=False),
        sa.Column('meta', sa.String(length=80), nullable=False),
        sa.Column('sort', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_books_slug'), 'books', ['slug'], unique=True)
    op.create_table(
        'passages',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('book_id', sa.String(length=32), nullable=False),
        sa.Column('chapter', sa.String(length=60), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('plain', sa.Text(), nullable=False),
        sa.Column('topic', sa.String(length=20), nullable=False),
        sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('embedding', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('sort', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_passage_book_sort', 'passages', ['book_id', 'sort'], unique=False)
