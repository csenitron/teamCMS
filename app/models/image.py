from ..extensions import db
from datetime import datetime

class Image(db.Model):
    __tablename__ = 'images'

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    alt = db.Column(db.String(255))
    directory_id = db.Column(db.Integer, db.ForeignKey('directories.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
