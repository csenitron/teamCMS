"""size charts

Revision ID: 3d6c60c3ed26
Revises: 5b67783b7572
Create Date: 2025-08-12 02:20:02.169253

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '3d6c60c3ed26'
down_revision = '5b67783b7572'
branch_labels = None
depends_on = None


def upgrade():
    # Безопасно удаляем пустые таблицы, если они уже были созданы вручную/автогеном
    op.execute('DROP TABLE IF EXISTS product_size_chart')
    op.execute('DROP TABLE IF EXISTS size_charts')

    op.create_table(
        'size_charts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.String(length=255, collation='utf8mb4_unicode_ci'), nullable=False),
        sa.Column('image_id', sa.Integer(), nullable=True),
        sa.Column('description', sa.Text(collation='utf8mb4_unicode_ci'), nullable=True),
        sa.Column('table_json', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['image_id'], ['images.id']),
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )

    op.create_table(
        'product_size_chart',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('size_chart_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.id']),
        sa.ForeignKeyConstraint(['size_chart_id'], ['size_charts.id']),
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )


def downgrade():
    op.drop_table('product_size_chart')
    op.drop_table('size_charts')
