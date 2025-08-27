from datetime import datetime
from ..extensions import db
from .base import BaseModel


class CustomerAddress(BaseModel):
    __tablename__ = 'customer_addresses'
    __table_args__ = {
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_unicode_ci',
    }

    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False, index=True)
    full_name = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(50), nullable=True)
    address_line1 = db.Column(db.String(255), nullable=False)
    address_line2 = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(100), nullable=False)
    postcode = db.Column(db.String(20), nullable=True)
    country = db.Column(db.String(100), nullable=False, default='Россия')
    is_default_shipping = db.Column(db.Boolean, default=False)
    is_default_billing = db.Column(db.Boolean, default=False)

    customer = db.relationship(
        'Customer',
        back_populates='addresses',
        foreign_keys=[customer_id],
    )

    def __repr__(self):
        return f"<CustomerAddress {self.full_name}, {self.city}>"


