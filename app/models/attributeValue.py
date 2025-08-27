from ..extensions import db
from .base import BaseModel

class AttributeValue(BaseModel):
    __tablename__ = 'attribute_values'

    attribute_id = db.Column(db.Integer, db.ForeignKey('attributes.id'), nullable=False)
    value = db.Column(db.String(255), nullable=False)

    attribute = db.relationship('Attribute', backref='values')

    __table_args__ = (
        db.UniqueConstraint('attribute_id', 'value', name='unique_attribute_value'),
    )

