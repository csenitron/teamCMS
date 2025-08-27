from datetime import datetime
from ..extensions import db
from .base import BaseModel

class Theme(BaseModel):
    __tablename__ = 'themes'

    name = db.Column(db.String(255), unique=True, nullable=False)
    directory = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
