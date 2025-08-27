from datetime import datetime
from ..extensions import db
from .base import BaseModel

class AuditLog(BaseModel):
    __tablename__ = 'audit_log'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action_type = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45))

    user = db.relationship('User')
