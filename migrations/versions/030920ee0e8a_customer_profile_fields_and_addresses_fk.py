"""customer profile fields and addresses fk

Revision ID: 030920ee0e8a
Revises: 2d1aa17eb319
Create Date: 2025-08-12 00:02:46.404495

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '030920ee0e8a'
down_revision = '2d1aa17eb319'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('customers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('phone', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('default_shipping_address_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('default_payment_method', sa.String(length=20), nullable=True))
        batch_op.create_foreign_key(None, 'customer_addresses', ['default_shipping_address_id'], ['id'])


def downgrade():
    with op.batch_alter_table('customers', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_column('default_payment_method')
        batch_op.drop_column('default_shipping_address_id')
        batch_op.drop_column('phone')
