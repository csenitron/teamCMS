# gallery.py
from ...extensions import db
from ..base import BaseModel

class GalleryModuleInstance(BaseModel):
    __tablename__ = 'gallery_instances'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    module_instance_id = db.Column(db.Integer, db.ForeignKey('module_instances.id'), nullable=False, index=True)

    title = db.Column(db.String(255), nullable=False, default="Моя галерея")
    description = db.Column(db.Text)

    module_instance = db.relationship('ModuleInstance', backref=db.backref('gallery_instance', uselist=False))

    def __repr__(self):
        return f"<GalleryModuleInstance id={self.id} title={self.title}>"


class GalleryItem(BaseModel):
    __tablename__ = 'gallery_items'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    gallery_id = db.Column(db.Integer, db.ForeignKey('gallery_instances.id'), nullable=False, index=True)
    image_id = db.Column(db.Integer, db.ForeignKey('images.id'), nullable=False)
    caption = db.Column(db.String(255), nullable=True)

    gallery = db.relationship('GalleryModuleInstance', backref=db.backref('items', lazy=True, cascade="all, delete"))
    image = db.relationship('Image', backref=db.backref('gallery_image', lazy=True))

    def __repr__(self):
        return f"<GalleryItem id={self.id}>"
