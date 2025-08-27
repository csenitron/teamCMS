from ...extensions import db
from ..base import BaseModel
from sqlalchemy.dialects.mysql import JSON


class BannerModuleInstance(BaseModel):
    """Экземпляр слайд-баннера, привязанный к ModuleInstance"""
    __tablename__ = 'banner_instances'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    module_instance_id = db.Column(db.Integer, db.ForeignKey('module_instances.id'), nullable=False, index=True)

    title = db.Column(db.String(255), nullable=False)  # Название слайд-баннера
    cards_in_row = db.Column(db.Integer, default=3)  # Количество карточек в строке

    module_instance = db.relationship('ModuleInstance', backref=db.backref('banner_instance', uselist=False))

    def __repr__(self):
        return f"<BannerModuleInstance {self.title}>"


class BannerItem(BaseModel):
    """Элемент слайд-баннера с изображением и текстом"""
    __tablename__ = 'banner_items'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    banner_id = db.Column(db.Integer, db.ForeignKey('banner_instances.id'), nullable=False, index=True)

    background_image_id = db.Column(db.Integer, db.ForeignKey('images.id'), nullable=False)
    text = db.Column(db.Text, nullable=True)         # Текст баннера
    link_text = db.Column(db.String(255), nullable=True)  # Текст ссылки
    link_url = db.Column(db.String(255), nullable=True)   # URL ссылки

    banner = db.relationship('BannerModuleInstance',
                             backref=db.backref('banner_items', lazy=True, cascade="all, delete"))
    background_image = db.relationship('Image',
                                       foreign_keys=[background_image_id],
                                       backref=db.backref('banner_images', lazy=True))

    def __repr__(self):
        return f"<BannerItem {self.text}>"
