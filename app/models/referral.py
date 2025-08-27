from datetime import datetime
from ..extensions import db
from .base import BaseModel

class Referral(BaseModel):
    __tablename__ = 'referrals'

    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False)
    clicks = db.Column(db.Integer, default=0)
    registrations = db.Column(db.Integer, default=0)
    orders_count = db.Column(db.Integer, default=0)
    revenue = db.Column(db.Numeric(10,2), default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = db.relationship('Customer', backref='referrals')
