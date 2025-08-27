"""order comments table

Revision ID: 2d1aa17eb319
Revises: 4c4a2243b79b
Create Date: 2025-08-11 23:34:04.629983

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2d1aa17eb319'
down_revision = '4c4a2243b79b'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'order_comments' not in inspector.get_table_names():
        op.create_table(
            'order_comments',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.Column('order_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('comment', sa.Text(), nullable=False),
            sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'])
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'order_comments' in inspector.get_table_names():
        op.drop_table('order_comments')
