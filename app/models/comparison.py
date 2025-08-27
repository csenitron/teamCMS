from datetime import datetime
from ..extensions import db
from .base import BaseModel

class ComparisonList(BaseModel):
    __tablename__ = 'comparison_lists'

    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    name = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = db.relationship('ComparisonItem', backref='comparison_list')

class ComparisonItem(BaseModel):
    __tablename__ = 'comparison_items'

    comparison_list_id = db.Column(db.Integer, db.ForeignKey('comparison_lists.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship('Product')
