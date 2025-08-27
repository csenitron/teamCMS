from datetime import datetime
from ..extensions import db
from .base import BaseModel

class Wishlist(BaseModel):
    __tablename__ = 'wishlists'

    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    name = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = db.relationship('WishlistItem', backref='wishlist')

class WishlistItem(BaseModel):
    __tablename__ = 'wishlist_items'

    wishlist_id = db.Column(db.Integer, db.ForeignKey('wishlists.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship('Product')
