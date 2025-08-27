"""add_unique_constraint_to_favorites

Revision ID: 25c5762d5ee1
Revises: 55a681c91e2b
Create Date: 2025-08-07 16:08:38.372956

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '25c5762d5ee1'
down_revision = '55a681c91e2b'
branch_labels = None
depends_on = None


def upgrade():
    # Удаляем дублирующиеся записи перед добавлением уникального индекса
    connection = op.get_bind()
    
    # Находим и удаляем дубли
    connection.execute(sa.text("""
        DELETE f1 FROM favorite f1
        INNER JOIN favorite f2 
        WHERE f1.id > f2.id 
        AND f1.customer_id = f2.customer_id 
        AND f1.product_id = f2.product_id
    """))
    
    # Добавляем уникальный индекс
    op.create_unique_constraint('unique_favorite_product_customer', 'favorite', ['product_id', 'customer_id'])


def downgrade():
    # Удаляем уникальный индекс
    op.drop_constraint('unique_favorite_product_customer', 'favorite', type_='unique')
