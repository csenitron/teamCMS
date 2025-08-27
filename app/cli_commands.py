from flask.cli import with_appcontext
import click
from app.extensions import db
from app.models.cart import CartItem

@click.command('clear-cart')
@with_appcontext
def clear_cart():
    """Очистить все товары из корзины"""
    try:
        # Удаляем все записи из корзины
        deleted_count = CartItem.query.delete()
        db.session.commit()
        click.echo(f'Корзина очищена. Удалено {deleted_count} товаров.')
    except Exception as e:
        db.session.rollback()
        click.echo(f'Ошибка при очистке корзины: {e}')

def register_commands(app):
    app.cli.add_command(clear_cart) 