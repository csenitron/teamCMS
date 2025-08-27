from ..extensions import db
from .base import BaseModel
from sqlalchemy.dialects.mysql import JSON

class Role(BaseModel):
    __tablename__ = 'roles'

    name = db.Column(db.String(255), unique=True, nullable=False)
    permissions = db.Column(JSON)