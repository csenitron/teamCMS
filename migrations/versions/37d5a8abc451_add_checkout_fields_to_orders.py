"""add checkout fields to orders

Revision ID: 37d5a8abc451
Revises: 3bbc913e5e61
Create Date: 2025-08-11 20:39:41.975688

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '37d5a8abc451'
down_revision = '3bbc913e5e61'
branch_labels = None
depends_on = None


def upgrade():
    # Only add checkout fields to orders
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('shipping_full_name', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('shipping_phone', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('shipping_address_line1', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('shipping_address_line2', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('shipping_city', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('shipping_postcode', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('shipping_country', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('payment_method', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('payment_status', sa.String(length=50), nullable=False))
        batch_op.add_column(sa.Column('payment_reference', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('customer_comment', sa.Text(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # Only drop checkout fields from orders
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_column('customer_comment')
        batch_op.drop_column('payment_reference')
        batch_op.drop_column('payment_status')
        batch_op.drop_column('payment_method')
        batch_op.drop_column('shipping_country')
        batch_op.drop_column('shipping_postcode')
        batch_op.drop_column('shipping_city')
        batch_op.drop_column('shipping_address_line2')
        batch_op.drop_column('shipping_address_line1')
        batch_op.drop_column('shipping_phone')
        batch_op.drop_column('shipping_full_name')
    # ### end Alembic commands ###
