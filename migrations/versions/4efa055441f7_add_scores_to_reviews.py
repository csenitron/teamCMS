"""add scores to reviews

Revision ID: 4efa055441f7
Revises: 070f92360bfd
Create Date: 2025-08-12 03:45:17.233494

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '4efa055441f7'
down_revision = '070f92360bfd'
branch_labels = None
depends_on = None


def upgrade():
    # Only add columns to reviews; do not touch unrelated tables
    with op.batch_alter_table('reviews', schema=None) as batch_op:
        batch_op.add_column(sa.Column('sizing_score', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('quality_score', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('comfort_score', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('reviews', schema=None) as batch_op:
        batch_op.drop_column('comfort_score')
        batch_op.drop_column('quality_score')
        batch_op.drop_column('sizing_score')
