"""add variation and selected_options to order_items

Revision ID: 80fc1246e455
Revises: 37d5a8abc451
Create Date: 2025-08-11 22:57:48.438685

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '80fc1246e455'
down_revision = '37d5a8abc451'
branch_labels = None
depends_on = None


def upgrade():
    # Only alter order_items table
    with op.batch_alter_table('order_items', schema=None) as batch_op:
        batch_op.add_column(sa.Column('variation_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('selected_options', sa.Text(), nullable=True))
        batch_op.create_foreign_key(None, 'product_variations', ['variation_id'], ['id'])


def downgrade():
    # Revert only order_items changes
    with op.batch_alter_table('order_items', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_column('selected_options')
        batch_op.drop_column('variation_id')
