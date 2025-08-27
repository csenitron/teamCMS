from datetime import datetime
from ..extensions import db
from .base import BaseModel

class ShippingZone(BaseModel):
    __tablename__ = 'shipping_zones'

    name = db.Column(db.String(255), nullable=False)
    region_id = db.Column(db.Integer, db.ForeignKey('regions.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    region = db.relationship('Region', backref='shipping_zones')
    methods = db.relationship('ShippingMethod', backref='zone')

class ShippingMethod(BaseModel):
    __tablename__ = 'shipping_methods'

    zone_id = db.Column(db.Integer, db.ForeignKey('shipping_zones.id'), nullable=False)
    method_name = db.Column(db.String(255), nullable=False)
    cost = db.Column(db.Numeric(10,2), default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
