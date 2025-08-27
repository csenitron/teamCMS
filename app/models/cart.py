from ..extensions import db
from .base import BaseModel
from datetime import datetime
import json

class CartItem(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)  # Для авторизованных, null для гостей
    session_id = db.Column(db.String(100), nullable=True)  # Для неавторизованных
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    selected_options = db.Column(db.Text, nullable=True)  # JSON строка с выбранными опциями
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    product = db.relationship('Product', backref='cart_items')  # Связь с товаром

    def get_selected_options(self):
        """Получить выбранные опции как словарь"""
        if self.selected_options:
            try:
                return json.loads(self.selected_options)
            except:
                return {}
        return {}

    def set_selected_options(self, options):
        """Установить выбранные опции"""
        self.selected_options = json.dumps(options) if options else None

    def __repr__(self):
        return f'<CartItem product_id={self.product_id} quantity={self.quantity}>'