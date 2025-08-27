"""make review.customer_id nullable

Revision ID: 312bdc0bfeb7
Revises: 5381929e9aaf
Create Date: 2025-08-12 04:11:29.761325

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '312bdc0bfeb7'
down_revision = '5381929e9aaf'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('reviews', schema=None) as batch_op:
        batch_op.alter_column('customer_id', existing_type=mysql.INTEGER(display_width=11), nullable=True)


def downgrade():
    with op.batch_alter_table('reviews', schema=None) as batch_op:
        batch_op.alter_column('customer_id', existing_type=mysql.INTEGER(display_width=11), nullable=False)
