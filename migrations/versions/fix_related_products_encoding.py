"""fix related_products encoding

Revision ID: fix_related_products_encoding
Revises: 070f92360bfd
Create Date: 2025-08-25 12:50:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'fix_related_products_encoding'
down_revision = '070f92360bfd'
branch_labels = None
depends_on = None


def upgrade():
    # Convert related_products table to utf8mb4
    op.execute("ALTER TABLE related_products CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")


def downgrade():
    # Revert collation back if needed (optional)
    op.execute("ALTER TABLE related_products CONVERT TO CHARACTER SET utf8 COLLATE utf8_general_ci")


