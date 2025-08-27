"""guest fields for reviews

Revision ID: 5381929e9aaf
Revises: 4efa055441f7
Create Date: 2025-08-12 04:09:29.208886

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '5381929e9aaf'
down_revision = '4efa055441f7'
branch_labels = None
depends_on = None


def upgrade():
    # Only add guest fields to reviews
    with op.batch_alter_table('reviews', schema=None) as batch_op:
        batch_op.add_column(sa.Column('guest_name', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('guest_email', sa.String(length=255), nullable=True))


def downgrade():
    with op.batch_alter_table('reviews', schema=None) as batch_op:
        batch_op.drop_column('guest_email')
        batch_op.drop_column('guest_name')
