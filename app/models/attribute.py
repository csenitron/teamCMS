from sqlalchemy.dialects.mysql import JSON
from ..extensions import db
from .base import BaseModel
from datetime import datetime

class Attribute(BaseModel):
    __tablename__ = 'attributes'

    name = db.Column(db.String(255), nullable=False, unique=True, index=True)  # Название атрибута
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
