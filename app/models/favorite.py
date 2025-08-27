from datetime import datetime
from symtable import Class
from ..extensions import db
from .base import BaseModel


class Favorite(BaseModel):
    __tablename__ = 'favorite'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    product = db.relationship('Product', backref='favorites', lazy=True)
    
    # Уникальный индекс для предотвращения дублирования
    __table_args__ = (
        db.UniqueConstraint('product_id', 'customer_id', name='unique_favorite_product_customer'),
    )

def getFavorites(customer_id):
    return Favorite.query.filter_by(customer_id=customer_id).all()

def addFavorite(customer_id, product_id):
    # Проверяем, не существует ли уже такая запись
    existing_favorite = Favorite.query.filter_by(
        customer_id=customer_id, 
        product_id=product_id
    ).first()
    
    if existing_favorite:
        return existing_favorite  # Возвращаем существующую запись
    
    favorite = Favorite(product_id=product_id, customer_id=customer_id)
    db.session.add(favorite)
    db.session.commit()
    return favorite

def deleteFavorite(customer_id, product_id):
    Favorite.query.filter_by(customer_id=customer_id, product_id=product_id).delete()
    db.session.commit()

def checkFavorite(customer_id, product_id):
    favorite =Favorite.query.filter_by(customer_id=customer_id, product_id=product_id).first()
    if favorite:
        return True
    else:
        return False


