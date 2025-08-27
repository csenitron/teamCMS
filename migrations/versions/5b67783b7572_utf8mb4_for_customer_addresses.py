"""utf8mb4 for customer_addresses

Revision ID: 5b67783b7572
Revises: 030920ee0e8a
Create Date: 2025-08-12 00:15:20.534358

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '5b67783b7572'
down_revision = '030920ee0e8a'
branch_labels = None
depends_on = None


def upgrade():
    # Change table charset/collation to utf8mb4
    op.execute("ALTER TABLE customer_addresses CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")


def downgrade():
    # Revert back to utf8 (best-effort; adjust if your previous collation differs)
    op.execute("ALTER TABLE customer_addresses CONVERT TO CHARACTER SET utf8 COLLATE utf8_unicode_ci;")
