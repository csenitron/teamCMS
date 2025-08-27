from ..extensions import db
from datetime import datetime
from .base import BaseModel

class Directory(BaseModel):
    __tablename__ = 'directories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('directories.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    parent = db.relationship('Directory', remote_side=[id], backref=db.backref('subdirectories', lazy='select'))
    images = db.relationship('Image', backref='directory', lazy='select')
    
    @property
    def children(self):
        return self.subdirectories
