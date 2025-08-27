"""merge heads for is_main

Revision ID: a743bf01e6fe
Revises: 7b1c2d3e4f56, 8f1c_main_menu_flag
Create Date: 2025-08-12 11:23:03.887964

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a743bf01e6fe'
down_revision = ('7b1c2d3e4f56', '8f1c_main_menu_flag')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
