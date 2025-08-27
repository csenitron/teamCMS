# order.py
from datetime import datetime
from ..extensions import db
from .base import BaseModel
from .product import Product
class Order(BaseModel):
    __tablename__ = 'orders'

    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='new')
    total_price = db.Column(db.Numeric(10,2), default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    referral_id = db.Column(db.Integer, db.ForeignKey('referrals.id'), nullable=True)
    tax_amount = db.Column(db.Numeric(10,2), default=0)
    shipping_cost = db.Column(db.Numeric(10,2), default=0)
    shipping_method_id = db.Column(db.Integer, db.ForeignKey('shipping_methods.id'), nullable=True)
    shipping_method_name = db.Column(db.String(255), nullable=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=True)

    # Shipping/contact fields
    shipping_full_name = db.Column(db.String(255), nullable=True)
    shipping_phone = db.Column(db.String(50), nullable=True)
    shipping_address_line1 = db.Column(db.String(255), nullable=True)
    shipping_address_line2 = db.Column(db.String(255), nullable=True)
    shipping_city = db.Column(db.String(100), nullable=True)
    shipping_postcode = db.Column(db.String(20), nullable=True)
    shipping_country = db.Column(db.String(100), nullable=True)

    # Payment fields
    payment_method = db.Column(db.String(50), nullable=True)
    payment_status = db.Column(db.String(50), nullable=False, default='pending')
    payment_reference = db.Column(db.String(255), nullable=True)

    # Customer note
    customer_comment = db.Column(db.Text, nullable=True)

    items = db.relationship('OrderItem', backref='order')

from ..extensions import db
from .base import BaseModel

class OrderItem(BaseModel):
    __tablename__ = 'order_items'

    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    price = db.Column(db.Numeric(10,2), default=0)
    variation_id = db.Column(db.Integer, db.ForeignKey('product_variations.id'), nullable=True)
    selected_options = db.Column(db.Text, nullable=True)  # JSON выбранных опций на момент заказа

    product = db.relationship('Product')


class OrderComment(BaseModel):
    __tablename__ = 'order_comments'

    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    comment = db.Column(db.Text, nullable=False)

    order = db.relationship('Order', backref='comments')