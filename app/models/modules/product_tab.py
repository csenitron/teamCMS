# app/models/modules/tabs.py
from ...extensions import db
from ..base import BaseModel


class TabsModuleInstance(BaseModel):
    __tablename__ = 'tabs_instances'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    module_instance_id = db.Column(db.Integer, db.ForeignKey('module_instances.id'), nullable=False, index=True)

    title = db.Column(db.String(255), nullable=False, default="Модуль с табами")

    module_instance = db.relationship('ModuleInstance', backref=db.backref('tabs_instance', uselist=False))

    def __repr__(self):
        return f"<TabsModuleInstance id={self.id} title={self.title}>"


class TabItem(BaseModel):
    __tablename__ = 'tabs_items'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tabs_id = db.Column(db.Integer, db.ForeignKey('tabs_instances.id'), nullable=False, index=True)

    tab_title = db.Column(db.String(255), nullable=False, default="Вкладка")
    mode = db.Column(db.String(20), default="category")
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    limit_count = db.Column(db.Integer, default=8)

    product_ids = db.Column(db.Text, nullable=True)  # храним "1,2,3" или JSON: '["1","2","3"]'
    button_text = db.Column(db.String(255), nullable=True)  # текст кнопки для вкладки

    # связи
    tabs = db.relationship('TabsModuleInstance', backref=db.backref('items', lazy=True, cascade="all,delete"))
    category = db.relationship('Category', backref='tabs_category', lazy=True)

    def __repr__(self):
        return f"<TabItem id={self.id} title={self.tab_title}>"
