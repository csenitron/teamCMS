from datetime import datetime
from ..extensions import db
from .base import BaseModel

class SocialLink(BaseModel):
    __tablename__ = 'social_links'

    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(255), nullable=False)  # Название платформы (например, "facebook")
    url = db.Column(db.String(255), nullable=False)  # URL на соцсеть
    icon_id = db.Column(db.Integer, db.ForeignKey('images.id'), nullable=True)  # Иконка соцсети (изображение)
    icon = db.relationship('Image', backref='social_icons', lazy='joined')  # Связь с изображением иконки
    site_settings_id = db.Column(db.Integer, db.ForeignKey('site_settings.id'))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<SocialLink {self.platform} ({self.url})>"



class SiteSettings(BaseModel):
    __tablename__ = 'site_settings'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(255), nullable=False)  # Название сайта
    logo_id = db.Column(db.Integer, db.ForeignKey('images.id'), nullable=True)  # Логотип, привязанное изображение
    logo = db.relationship('Image', backref='site_logo', lazy='joined')
    address = db.Column(db.String(255), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(255), nullable=True)
    owner = db.Column(db.String(255), nullable=True)
    working_hours = db.Column(db.String(255), nullable=True)
    map_locations = db.Column(db.JSON, nullable=True)

    # Ссылки на соцсети
    social_links = db.relationship('SocialLink', backref='site_settings', lazy='joined')

    additional_info = db.Column(db.Text, nullable=True)
    home_page_id = db.Column(db.Integer, db.ForeignKey('pages.id'), nullable=True)  # Домашняя страница

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<SiteSettings {self.title}>"

def getSiteSettings():
    settings = db.session.query(SiteSettings).first()
    return settings
