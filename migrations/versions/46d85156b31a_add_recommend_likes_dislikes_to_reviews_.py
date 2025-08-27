"""add recommend likes dislikes to reviews and review_votes table

Revision ID: 46d85156b31a
Revises: 312bdc0bfeb7
Create Date: 2025-08-12 05:58:06.982158

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '46d85156b31a'
down_revision = '312bdc0bfeb7'
branch_labels = None
depends_on = None


def upgrade():
    # Добавляем поля к таблице reviews
    with op.batch_alter_table('reviews', schema=None) as batch_op:
        batch_op.add_column(sa.Column('recommend', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('likes', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('dislikes', sa.Integer(), nullable=False, server_default='0'))

    # Создаем таблицу review_votes для антидублей
    op.create_table(
        'review_votes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('review_id', sa.Integer(), sa.ForeignKey('reviews.id', ondelete='CASCADE'), nullable=False),
        sa.Column('voter_key', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        mysql_engine='InnoDB',
        mysql_default_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
    )
    op.create_unique_constraint('uq_review_votes_review_voter', 'review_votes', ['review_id', 'voter_key'])


def downgrade():
    # Откат новых объектов
    op.drop_constraint('uq_review_votes_review_voter', 'review_votes', type_='unique')
    op.drop_table('review_votes')
    with op.batch_alter_table('reviews', schema=None) as batch_op:
        batch_op.drop_column('dislikes')
        batch_op.drop_column('likes')
        batch_op.drop_column('recommend')
