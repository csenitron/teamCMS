"""
add is_main to menu_instances

Revision ID: 8f1c_main_menu_flag
Revises: 364945993833
Create Date: 2025-08-12
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8f1c_main_menu_flag'
down_revision = '364945993833'
branch_labels = None
depends_on = None


def upgrade():
    try:
        with op.batch_alter_table('menu_instances') as batch_op:
            batch_op.add_column(sa.Column('is_main', sa.Boolean(), nullable=False, server_default=sa.false()))
            batch_op.alter_column('is_main', server_default=None)
    except Exception:
        pass


def downgrade():
    try:
        with op.batch_alter_table('menu_instances') as batch_op:
            batch_op.drop_column('is_main')
    except Exception:
        pass


