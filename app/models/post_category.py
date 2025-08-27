import re
import unicodedata
from datetime import datetime

from ..extensions import db
from .base import BaseModel


class PostCategory(BaseModel):
    __tablename__ = 'post_categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('post_categories.id'))
    parent = db.relationship('PostCategory', remote_side=[id], backref='children')
    description = db.Column(db.Text)
    meta_title = db.Column(db.String(255))
    meta_description = db.Column(db.Text)
    meta_keywords = db.Column(db.String(255))
    sort_order = db.Column(db.Integer, default=0)
    image_id = db.Column(db.Integer, db.ForeignKey('images.id'), nullable=True)  # привязанная картинка
    is_indexed = db.Column(db.Boolean, default=True)
    image = db.relationship('Image', backref='post_categories', lazy='joined')

    def __repr__(self):
        return f"<PostCategory {self.name}>"

    @staticmethod
    def slugify(value):
        """
        Простейшая функция для генерации slug:
        - Приводим к нижнему регистру
        - Удаляем диакритические знаки (unicode normalization)
        - Убираем все небуквенно-цифровые символы на дефисы
        - Убираем лишние дефисы
        """
        value = unicodedata.normalize('NFKD', value)
        value = value.encode('ascii', 'ignore').decode('ascii')  # убрать не-ASCII символы
        value = re.sub(r'[^a-zA-Z0-9]+', '-', value.lower())
        value = value.strip('-')
        return value

    def generate_slug(self, base_slug=None):
        if not base_slug:
            base_slug = self.slugify(self.name)
        slug = base_slug
        counter = 1
        while PostCategory.query.filter_by(slug=slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1
        self.slug = slug

    def __eq__(self, other):
        if not isinstance(other, PostCategory):
            return False
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)