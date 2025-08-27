from ..extensions import db
from datetime import datetime
from .base import BaseModel
from sqlalchemy.dialects.mysql import JSON

class Module(BaseModel):
    """Шаблоны модулей"""
    __tablename__ = 'modules'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False, unique=True)  # Название модуля (например, "Слайдер")
    settings_schema = db.Column(JSON, nullable=False)  # Схема возможных настроек
    templates = db.Column(JSON, nullable=False)  # Список доступных шаблонов
    creation_template = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f"<Module {self.name}>"


class ModuleInstance(BaseModel):
    """Экземпляры модулей"""
    __tablename__ = 'module_instances'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id'), nullable=False, index=True)
    settings = db.Column(JSON, nullable=False)  # Настройки конкретного модуля
    content = db.Column(JSON, nullable=True)  # Контент модуля (например, изображения для галереи)
    selected_template = db.Column(db.String(255), nullable=False)  # Выбранный шаблон отображения

    module = db.relationship('Module', backref=db.backref('instances', lazy=True))

    def __repr__(self):
        return f"<ModuleInstance {self.id} of Module {self.module.name}>"