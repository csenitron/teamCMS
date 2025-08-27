from ...extensions import db
from ..base import BaseModel
from sqlalchemy.dialects.mysql import JSON

class SliderModuleInstance(BaseModel):
    """Экземпляр слайдера, привязанный к ModuleInstance"""
    __tablename__ = 'slider_instances'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    module_instance_id = db.Column(db.Integer, db.ForeignKey('module_instances.id'), nullable=False, index=True)

    title = db.Column(db.String(255), nullable=False)  # Название слайдера
    width = db.Column(db.Integer, default=100)  # Ширина в %
    transition_type = db.Column(db.Enum('fade', 'slide', name="transition_types"), default="slide")  # Тип перехода
    status = db.Column(db.Boolean, default=True)  # Включен/выключен
    show_arrows = db.Column(db.Boolean, default=True)  # Показывать стрелки
    show_indicators = db.Column(db.Boolean, default=True)  # Показывать индикаторы

    module_instance = db.relationship('ModuleInstance', backref=db.backref('slider_instance', uselist=False))

    def __repr__(self):
        return f"<SliderModuleInstance {self.title}>"


class SliderItem(BaseModel):
    """Слайды внутри слайдера"""
    __tablename__ = 'slider_items'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    slider_id = db.Column(db.Integer, db.ForeignKey('slider_instances.id'), nullable=False, index=True)

    image_pc_id = db.Column(db.Integer, db.ForeignKey('images.id'), nullable=False)  # Изображение для ПК
    image_mobile_id = db.Column(db.Integer, db.ForeignKey('images.id'), nullable=True)  # Изображение для телефона
    title = db.Column(db.String(255), nullable=True)  # Заголовок слайда
    description = db.Column(db.Text, nullable=True)  # Описание слайда
    title_color = db.Column(db.String(20), nullable=True)  # Цвет заголовка (hex/rgb)
    description_color = db.Column(db.String(20), nullable=True)  # Цвет описания
    link_text = db.Column(db.String(255), nullable=True)  # Текст кнопки
    link_url = db.Column(db.String(255), nullable=True)  # URL кнопки

    slider = db.relationship('SliderModuleInstance', backref=db.backref('slides', lazy=True, cascade="all, delete"))
    image_pc = db.relationship('Image', foreign_keys=[image_pc_id], backref=db.backref('slider_pc', lazy=True))
    image_mobile = db.relationship('Image', foreign_keys=[image_mobile_id], backref=db.backref('slider_mobile', lazy=True))
    # Несколько кнопок на один слайд
    buttons = db.relationship('SliderButton', backref='slide', cascade='all, delete-orphan', order_by='SliderButton.order')

    def __repr__(self):
        return f"<SliderItem {self.title}>"


class SliderButton(BaseModel):
    """Кнопки на слайде с настройкой цветов"""
    __tablename__ = 'slider_buttons'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    slide_id = db.Column(db.Integer, db.ForeignKey('slider_items.id'), nullable=False, index=True)
    text = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(255), nullable=True)
    bg_color = db.Column(db.String(20), nullable=True)
    text_color = db.Column(db.String(20), nullable=True)
    order = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f"<SliderButton {self.text}>"
