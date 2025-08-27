import re
from datetime import datetime


from unidecode import unidecode

from ..extensions import db
from .base import BaseModel



class Post(BaseModel):
    __tablename__ = 'posts'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('post_categories.id'))
    category = db.relationship('PostCategory', backref='posts_category')
    content = db.Column(db.Text, nullable=False)
    meta_title = db.Column(db.String(255))
    meta_description = db.Column(db.Text)
    meta_keywords = db.Column(db.String(255))
    image_id = db.Column(db.Integer, db.ForeignKey('images.id'), nullable=True)  # привязанная картинка
    image = db.relationship('Image', backref='post', lazy='joined')
    published_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_published = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<Post {self.title}>"

    def generate_slug(self, base_slug=None):
        if not base_slug:
            base_slug = BaseModel.slugify(self.title)

        # Преобразуем в латиницу и заменяем пробелы на '-'
        base_slug = unidecode(base_slug).lower().replace(" ", "-")

        slug = base_slug
        counter = 1

        # Пока существует другая запись (id != self.id) с таким же slug, добавляем -1, -2 и т.д.
        while Post.query.filter(Post.slug == slug, Post.id != self.id).first():
            slug = f"{base_slug}-{counter}"
            counter += 1

        self.slug = slug
        return slug

class PostLayout(BaseModel):
    __tablename__ = 'post_layout'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    row_index = db.Column(db.Integer, nullable=False, default=0)
    col_index = db.Column(db.Integer, nullable=False, default=0)
    col_width = db.Column(db.Integer, nullable=False, default=3)
    module_instance_id = db.Column(db.Integer, db.ForeignKey('module_instances.id'))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связи
    post = db.relationship('Post', backref='post_layout')
    module_instance = db.relationship('ModuleInstance', backref='post_cells', lazy=True)

    def __repr__(self):
        return (f"<PostLayout post={self.post_id} row={self.row_index} col={self.col_index} "
                f"width={self.col_width} module={self.module_instance_id}>")
