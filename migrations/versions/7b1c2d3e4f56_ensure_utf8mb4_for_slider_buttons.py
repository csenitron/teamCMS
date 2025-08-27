"""ensure utf8mb4 for slider_buttons table

Revision ID: 7b1c2d3e4f56
Revises: 610a7a658fc3
Create Date: 2025-08-12
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = '7b1c2d3e4f56'
down_revision = '610a7a658fc3'
branch_labels = None
depends_on = None


def upgrade():
    # Ensure table and its string columns are utf8mb4
    try:
        op.execute("ALTER TABLE slider_buttons CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    except Exception:
        # ignore if table doesn't exist or already in utf8mb4
        pass


def downgrade():
    # No-op: we won't downgrade charset
    pass


