from ..extensions import db
from .base import BaseModel
from datetime import datetime


class Category(BaseModel):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), index=True, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    slug = db.Column(db.String(255), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    description = db.Column(db.Text, nullable=True)
    # Новые поля
    sort_order = db.Column(db.Integer, default=0)  # порядок сортировки
    is_indexed = db.Column(db.Boolean, default=False)  # флаг индексации
    image_id = db.Column(db.Integer, db.ForeignKey('images.id'), nullable=True)  # привязанная картинка

    parent = db.relationship('Category', remote_side='Category.id', backref='subcategories')

    # Связь с моделью Image (если таковая есть)
    image = db.relationship('Image', backref='categories', lazy='joined')

    @staticmethod
    def get_category_tree(parent_id=None):
        """
        Возвращает список dict, где каждая dict:
          {
            'category': <Category>,
            'children': [ {...}, {...} ]
          }
        """
        nodes = []
        # обходим по sort_order
        query = Category.query.filter_by(parent_id=parent_id).order_by(Category.sort_order, Category.id)
        for cat in query:
            node = {
                'category': cat,
                'children': Category.get_category_tree(cat.id)  # рекурсивный вызов
            }
            nodes.append(node)
        return nodes

    def full_name(self):
        if self.parent:
            return f"{self.parent.full_name()} > {self.name}"
        return self.name


def build_category_list(parent_id=None, level=0):
    """
    Возвращает список кортежей (cat, level), где cat - объект Category,
    а level - уровень вложения. Сортируем по sort_order, затем по id.
    """
    results = []
    query = Category.query.filter_by(parent_id=parent_id).order_by(Category.sort_order, Category.id)
    for cat in query:
        results.append((cat, level))
        # рекурсивно добавляем дочерние
        results.extend(build_category_list(cat.id, level + 1))
    return results

def getPcats():
    query = Category.query.filter_by(parent_id=None).order_by(Category.sort_order, Category.id)
    results = []
    for cat in query:
        results.append({'name':cat.name, 'slug':cat.slug})

    return results

def getCategoryBySlug(slug):
    category = Category.query.filter_by(slug=slug).order_by(Category.sort_order, Category.id).first()
    return category

def getSybCategoryByID(parent_id):
    subCategories = Category.query.filter_by(parent_id=parent_id).order_by(Category.sort_order, Category.id)
    return subCategories