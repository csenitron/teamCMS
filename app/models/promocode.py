from datetime import datetime
from ..extensions import db
from .base import BaseModel

class Promocode(BaseModel):
    __tablename__ = 'promocodes'

    code = db.Column(db.String(50), unique=True, nullable=False)
    discount_type = db.Column(db.String(50), nullable=False)  # 'percent' или 'fixed'
    discount_value = db.Column(db.Numeric(10,2), default=0)
    start_date = db.Column(db.DateTime, nullable=True)
    end_date = db.Column(db.DateTime, nullable=True)
    usage_limit = db.Column(db.Integer, default=0)
    used_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
