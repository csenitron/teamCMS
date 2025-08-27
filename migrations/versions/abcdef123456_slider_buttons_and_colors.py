"""add slider buttons table and title/description colors

Revision ID: abcdef123456
Revises: 4fc7af82dbc6_add_video_url_to_menuitemextended
Create Date: 2025-08-12
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'abcdef123456'
down_revision = '4fc7af82dbc6'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    # Add colors to slider_items if not present
    existing_cols = {c['name'] for c in inspector.get_columns('slider_items')}
    with op.batch_alter_table('slider_items', schema=None) as batch_op:
        if 'title_color' not in existing_cols:
            batch_op.add_column(sa.Column('title_color', sa.String(length=20), nullable=True))
        if 'description_color' not in existing_cols:
            batch_op.add_column(sa.Column('description_color', sa.String(length=20), nullable=True))

    # Create slider_buttons table if not exists
    existing_tables = set(inspector.get_table_names())
    if 'slider_buttons' not in existing_tables:
        op.create_table(
            'slider_buttons',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('slide_id', sa.Integer(), sa.ForeignKey('slider_items.id'), nullable=False, index=True),
            sa.Column('text', sa.String(length=255), nullable=False),
            sa.Column('url', sa.String(length=255), nullable=True),
            sa.Column('bg_color', sa.String(length=20), nullable=True),
            sa.Column('text_color', sa.String(length=20), nullable=True),
            sa.Column('order', sa.Integer(), nullable=False, server_default='0'),
        )


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if 'slider_buttons' in inspector.get_table_names():
        op.drop_table('slider_buttons')
    existing_cols = {c['name'] for c in inspector.get_columns('slider_items')}
    with op.batch_alter_table('slider_items', schema=None) as batch_op:
        if 'description_color' in existing_cols:
            batch_op.drop_column('description_color')
        if 'title_color' in existing_cols:
            batch_op.drop_column('title_color')


