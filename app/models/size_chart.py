from ..extensions import db
from .base import BaseModel
from datetime import datetime


class SizeChart(BaseModel):
    __tablename__ = 'size_charts'
    __table_args__ = {
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_unicode_ci'
    }

    title = db.Column(db.String(255), nullable=False)
    image_id = db.Column(db.Integer, db.ForeignKey('images.id'), nullable=True)
    description = db.Column(db.Text, nullable=True)
    # Храним таблицу как JSON: { "columns": ["UK","US",...], "rows": [ {"label": "XXS", "values": ["4–6","0–2", ...] }, ... ] }
    table_json = db.Column(db.JSON, nullable=True)

    image = db.relationship('Image')


class ProductSizeChart(BaseModel):
    __tablename__ = 'product_size_chart'
    __table_args__ = {
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_unicode_ci'
    }

    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    size_chart_id = db.Column(db.Integer, db.ForeignKey('size_charts.id'), nullable=False, index=True)

    product = db.relationship('Product', backref=db.backref('size_chart_link', uselist=False))
    size_chart = db.relationship('SizeChart', backref='product_links')


