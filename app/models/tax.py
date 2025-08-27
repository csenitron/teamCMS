from datetime import datetime
from ..extensions import db
from .base import BaseModel

class TaxRate(BaseModel):
    __tablename__ = 'tax_rates'

    name = db.Column(db.String(255), nullable=False)
    rate = db.Column(db.Numeric(5,2), default=0)
    region_id = db.Column(db.Integer, db.ForeignKey('regions.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    region = db.relationship('Region', backref='tax_rates')
