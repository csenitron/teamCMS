from ..extensions import db
from .base import BaseModel
from datetime import datetime

class ProductAttribute(BaseModel):
    __tablename__ = 'product_attributes'

    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    attribute_value_id = db.Column(db.Integer, db.ForeignKey('attribute_values.id'), nullable=False)

    product = db.relationship('Product', backref='attributes')
    attribute_value = db.relationship('AttributeValue', backref='product_attributes')

    __table_args__ = (
        db.UniqueConstraint('product_id', 'attribute_value_id', name='unique_product_attribute_value'),
    )
