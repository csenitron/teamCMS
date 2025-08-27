"""order shipping method and comments

Revision ID: 4c4a2243b79b
Revises: 80fc1246e455
Create Date: 2025-08-11 23:31:27.819737

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '4c4a2243b79b'
down_revision = '80fc1246e455'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('shipping_method_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('shipping_method_name', sa.String(length=255), nullable=True))
        batch_op.create_foreign_key(None, 'shipping_methods', ['shipping_method_id'], ['id'])


def downgrade():
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_column('shipping_method_name')
        batch_op.drop_column('shipping_method_id')
