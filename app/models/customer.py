from datetime import datetime
from flask_login import UserMixin
from flask_login import current_user

from ..extensions import db
from .base import BaseModel
import bcrypt
class Customer(BaseModel, UserMixin):
    __tablename__ = 'customers'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    referral_code = db.Column(db.String(50), unique=True)
    language = db.Column(db.String(10))
    currency = db.Column(db.String(10))
    region_id = db.Column(db.Integer, db.ForeignKey('regions.id'), nullable=True)
    # Дополнительно для ЛК
    phone = db.Column(db.String(50), nullable=True)
    default_shipping_address_id = db.Column(db.Integer, db.ForeignKey('customer_addresses.id'), nullable=True)
    default_payment_method = db.Column(db.String(20), nullable=True)  # cod, card, etc.

    region = db.relationship('Region', backref='customers')
    orders = db.relationship('Order', backref='customer')
    reviews = db.relationship('Review', backref='customer')
    wishlists = db.relationship('Wishlist', backref='customer')
    comparison_lists = db.relationship('ComparisonList', backref='customer')
    default_shipping_address = db.relationship(
        'CustomerAddress',
        foreign_keys=[default_shipping_address_id],
        uselist=False,
        post_update=True,
    )
    addresses = db.relationship(
        'CustomerAddress',
        back_populates='customer',
        foreign_keys='CustomerAddress.customer_id',
        cascade='all, delete-orphan',
    )


    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password.encode('utf-8'))


def hash_password(password):
    """Хеширует пароль с помощью bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def addCustomer(name, email, password):
    password_hash = hash_password(password)
    customer = Customer(
        name= name,
        email= email,
        password = password_hash
    )
    db.session.add(customer)
    db.session.commit()
    return customer
