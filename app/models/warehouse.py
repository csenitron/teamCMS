from datetime import datetime
from ..extensions import db
from .base import BaseModel

class Warehouse(BaseModel):
    __tablename__ = 'warehouses'

    name = db.Column(db.String(255), nullable=False)
    region_id = db.Column(db.Integer, db.ForeignKey('regions.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    region = db.relationship('Region', backref='warehouses')
    stocks = db.relationship('WarehouseStock', backref='warehouse')


class WarehouseStock(BaseModel):
    __tablename__ = 'warehouse_stocks'

    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    stock = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_warehouse_product', 'warehouse_id', 'product_id'),  # Индекс для склада и товара
    )

