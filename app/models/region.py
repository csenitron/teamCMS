from datetime import datetime
from ..extensions import db
from .base import BaseModel

class Region(BaseModel):
    __tablename__ = 'regions'

    name = db.Column(db.String(255), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    settings = db.relationship('RegionSettings', uselist=False, backref='region')

class RegionSettings(BaseModel):
    __tablename__ = 'region_settings'

    region_id = db.Column(db.Integer, db.ForeignKey('regions.id'), nullable=False)
    currency = db.Column(db.String(10))
    language = db.Column(db.String(10))
    tax_rate_id = db.Column(db.Integer, db.ForeignKey('tax_rates.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tax_rate = db.relationship('TaxRate')
