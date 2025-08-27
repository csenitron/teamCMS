"""utf8mb4 for size_charts tables

Revision ID: 070f92360bfd
Revises: 3d6c60c3ed26
Create Date: 2025-08-12 03:24:38.138153

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '070f92360bfd'
down_revision = '3d6c60c3ed26'
branch_labels = None
depends_on = None


def upgrade():
    # Convert only size_charts related tables to utf8mb4
    op.execute("ALTER TABLE size_charts CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    op.execute("ALTER TABLE product_size_chart CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")


def downgrade():
    # Revert collations back if needed (optional)
    op.execute("ALTER TABLE product_size_chart CONVERT TO CHARACTER SET utf8 COLLATE utf8_general_ci")
    op.execute("ALTER TABLE size_charts CONVERT TO CHARACTER SET utf8 COLLATE utf8_general_ci")
