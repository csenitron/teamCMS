from datetime import datetime
from ..extensions import db
from .base import BaseModel

class Menu(BaseModel):
    __tablename__ = 'menus'

    name = db.Column(db.String(255), nullable=False)
    language = db.Column(db.String(10), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = db.relationship('MenuItem', backref='menu', order_by='MenuItem.position')

class MenuItem(BaseModel):
    __tablename__ = 'menu_items'

    menu_id = db.Column(db.Integer, db.ForeignKey('menus.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(255), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=True)
    position = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    parent = db.relationship('MenuItem', remote_side='MenuItem.id', backref='subitems')
