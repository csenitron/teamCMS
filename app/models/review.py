from datetime import datetime
from ..extensions import db
from .base import BaseModel

class Review(BaseModel):
    __tablename__ = 'reviews'

    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    guest_name = db.Column(db.String(255), nullable=True)
    guest_email = db.Column(db.String(255), nullable=True)
    # Дополнительные индикаторы
    sizing_score = db.Column(db.Integer, nullable=True)     # 1..5: Маломерит → В размер → Большемерит
    quality_score = db.Column(db.Integer, nullable=True)    # 1..5: Низкое → Высокое
    comfort_score = db.Column(db.Integer, nullable=True)    # 1..5: Низкий → Высокий
    # Новые поля
    recommend = db.Column(db.Boolean, nullable=True)        # Рекомендует товар
    likes = db.Column(db.Integer, default=0, nullable=False)
    dislikes = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved = db.Column(db.Boolean, default=False)

    product = db.relationship('Product', backref='reviews')
