"""
@file: app/models/modules/menu.py
@description: Модели для модуля навигационного меню сайта
@dependencies: Menu, MenuItem, Image, Category, Page, Post, PostCategory
@created: 2024-12-21
"""

from ...extensions import db
from ..base import BaseModel
from sqlalchemy.dialects.mysql import JSON

__all__ = ['MenuModuleInstance', 'MenuItemExtended']


class MenuModuleInstance(BaseModel):
    """Экземпляр модуля меню, привязанный к ModuleInstance"""
    __tablename__ = 'menu_instances'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    module_instance_id = db.Column(db.Integer, db.ForeignKey('module_instances.id'), nullable=False, index=True)
    menu_id = db.Column(db.Integer, db.ForeignKey('menus.id'), nullable=False)

    title = db.Column(db.String(255), nullable=False, default="Меню сайта")
    show_icons = db.Column(db.Boolean, default=True)
    max_depth = db.Column(db.Integer, default=3)
    enable_videos = db.Column(db.Boolean, default=False)
    menu_style = db.Column(db.String(50), default='horizontal')  # horizontal, vertical, mega, mobile
    custom_css_class = db.Column(db.String(255), default='')  # Пользовательские CSS классы
    target_blank = db.Column(db.Boolean, default=False)  # Открывать ссылки в новой вкладке
    enable_auto_catalog = db.Column(db.Boolean, default=True)  # автогенерация каталога
    is_main = db.Column(db.Boolean, default=False, nullable=False)  # Главное меню (header)

    # Связи
    module_instance = db.relationship('ModuleInstance', backref=db.backref('menu_instance', uselist=False))
    menu = db.relationship('Menu', backref='menu_instances')

    def __repr__(self):
        return f"<MenuModuleInstance {self.title}>"


class MenuItemExtended(BaseModel):
    """Расширенные пункты меню с типизацией и дополнительными возможностями"""
    __tablename__ = 'menu_items_extended'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    menu_instance_id = db.Column(db.Integer, db.ForeignKey('menu_instances.id'), nullable=False, index=True)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)

    # Типизация пунктов меню
    item_type = db.Column(db.Enum(
        'page',           # Страница CMS
        'category',       # Категория товаров
        'post_category',  # Категория статей  
        'post',           # Отдельная статья
        'all_posts',      # Все статьи
        'external',       # Внешняя ссылка
        'catalog',        # Автокаталог всех категорий
        'custom',         # Произвольный пункт
        name='menu_item_types'
    ), nullable=False, default='custom')

    target_id = db.Column(db.Integer, nullable=True)  # ID целевого объекта (страницы, категории и т.д.)
    
    # Медиа контент
    icon_id = db.Column(db.Integer, db.ForeignKey('images.id'), nullable=True)  # Иконка пункта
    video_id = db.Column(db.Integer, db.ForeignKey('images.id'), nullable=True)  # Видео файл (через images)
    video_url = db.Column(db.String(500), nullable=True)  # URL видео (YouTube, Vimeo и т.д.)
    
    # Дополнительные настройки
    show_in_catalog = db.Column(db.Boolean, default=True)  # Показывать в автокаталоге
    custom_class = db.Column(db.String(100), nullable=True)  # CSS класс для стилизации
    description = db.Column(db.Text, nullable=True)  # Описание для мегаменю
    
    # Настройки отображения
    open_in_new_tab = db.Column(db.Boolean, default=False)  # Открывать в новой вкладке
    is_featured = db.Column(db.Boolean, default=False)  # Выделенный пункт
    sort_order = db.Column(db.Integer, default=0)  # Порядок сортировки

    # Связи
    menu_instance = db.relationship('MenuModuleInstance', backref=db.backref('extended_items', lazy=True, cascade="all, delete"))
    menu_item = db.relationship('MenuItem', backref='extended_item')
    icon = db.relationship('Image', foreign_keys=[icon_id], backref='menu_icons')
    video = db.relationship('Image', foreign_keys=[video_id], backref='menu_videos')

    def __repr__(self):
        return f"<MenuItemExtended {self.item_type}:{self.target_id}>"

    def get_dynamic_url(self):
        """Генерирует URL на основе типа пункта меню"""
        from ..page import Page
        from ..category import Category
        from ..post import Post
        from ..post_category import PostCategory

        if self.item_type == 'page' and self.target_id:
            page = Page.query.get(self.target_id)
            return f'/page/{page.slug}' if page else '#'
            
        elif self.item_type == 'category' and self.target_id:
            category = Category.query.get(self.target_id)
            return f'/category/{category.slug}' if category else '#'
            
        elif self.item_type == 'post_category' and self.target_id:
            post_cat = PostCategory.query.get(self.target_id)
            return f'/blog/category/{post_cat.slug}' if post_cat else '#'
            
        elif self.item_type == 'post' and self.target_id:
            post = Post.query.get(self.target_id)
            return f'/blog/{post.slug}' if post else '#'
            
        elif self.item_type == 'catalog':
            return '/catalog'
            
        elif self.item_type == 'external':
            return self.menu_item.url if self.menu_item else '#'
            
        else:
            return self.menu_item.url if self.menu_item else '#'

    def get_target_title(self):
        """Получает название целевого объекта"""
        from ..page import Page
        from ..category import Category
        from ..post import Post
        from ..post_category import PostCategory

        if self.item_type == 'page' and self.target_id:
            page = Page.query.get(self.target_id)
            return page.title if page else 'Страница не найдена'
            
        elif self.item_type == 'category' and self.target_id:
            category = Category.query.get(self.target_id)
            return category.name if category else 'Категория не найдена'
            
        elif self.item_type == 'post_category' and self.target_id:
            post_cat = PostCategory.query.get(self.target_id)
            return post_cat.name if post_cat else 'Категория статей не найдена'
            
        elif self.item_type == 'post' and self.target_id:
            post = Post.query.get(self.target_id)
            return post.title if post else 'Статья не найдена'
            
        elif self.item_type == 'catalog':
            return 'Каталог товаров'
            
        else:
            return self.menu_item.title if self.menu_item else 'Без названия'

    @staticmethod
    def generate_url_by_type(item_type, target_id):
        """Генерирует URL по типу и ID целевого объекта"""
        if not target_id:
            return '#'
            
        try:
            if item_type == 'page':
                from ..page import Page
                page = Page.query.get(target_id)
                return f'/page/{page.slug}' if page else '#'
                
            elif item_type == 'category':
                from ..category import Category
                category = Category.query.get(target_id)
                return f'/category/{category.slug}' if category else '#'
                
            elif item_type == 'post_category':
                from ..post_category import PostCategory
                post_cat = PostCategory.query.get(target_id)
                return f'/blog/category/{post_cat.slug}' if post_cat else '#'
                
            elif item_type == 'post':
                from ..post import Post
                post = Post.query.get(target_id)
                return f'/blog/{post.slug}' if post else '#'
                
        except Exception:
            return '#'
            
        return '#'

    @staticmethod
    def get_catalog_items(parent_id=None, max_depth=3, current_depth=0):
        """Генерирует структуру каталога категорий для автоменю.
        Поддерживает корневые категории с parent_id IS NULL или = 0.
        """
        from ..category import Category
        from sqlalchemy import or_

        if current_depth >= max_depth:
            return []

        # Корневой уровень: допускаем parent_id IS NULL или = 0
        if parent_id is None:
            categories = (
                Category.query
                .filter(or_(Category.parent_id.is_(None), Category.parent_id == 0))
                .order_by(Category.sort_order, Category.name)
                .all()
            )
        else:
            categories = (
                Category.query
                .filter(Category.parent_id == parent_id)
                .order_by(Category.sort_order, Category.name)
                .all()
            )
        
        catalog_items = []
        for category in categories:
            item_data = {
                'id': category.id,
                'title': category.name,
                'url': f'/category/{category.slug}',
                'slug': category.slug,
                'description': category.description,
                'image_id': category.image_id,
                'children': MenuItemExtended.get_catalog_items(
                    parent_id=category.id,
                    max_depth=max_depth,
                    current_depth=current_depth + 1,
                )
            }
            catalog_items.append(item_data)
            
        return catalog_items

    def build_menu_structure(self):
        """Строит полную структуру меню для данного экземпляра"""
        menu_items = MenuItemExtended.query.filter_by(
            menu_instance_id=self.menu_instance_id
        ).join(MenuItem).order_by(MenuItem.position, MenuItemExtended.sort_order).all()

        menu_structure = []
        
        for extended_item in menu_items:
            item_data = {
                'id': extended_item.id,
                'title': extended_item.get_target_title(),
                'url': extended_item.get_dynamic_url(),
                'type': extended_item.item_type,
                'icon_id': extended_item.icon_id,
                'video_id': extended_item.video_id,
                'description': extended_item.description,
                'custom_class': extended_item.custom_class,
                'open_in_new_tab': extended_item.open_in_new_tab,
                'is_featured': extended_item.is_featured,
                'children': []
            }

            # Для каталога добавляем автогенерируемые категории
            if extended_item.item_type == 'catalog' and extended_item.show_in_catalog:
                item_data['children'] = self.get_catalog_items(
                    max_depth=extended_item.menu_instance.max_depth
                )

            menu_structure.append(item_data)

        return menu_structure 