import re
import unicodedata
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.fields.choices import SelectField, SelectMultipleField
from wtforms.fields.datetime import DateTimeField
from wtforms.fields.form import FormField
from wtforms.fields.list import FieldList
from wtforms.fields.numeric import IntegerField, DecimalField
from wtforms.fields.simple import HiddenField, BooleanField, PasswordField
from wtforms.validators import DataRequired, Optional, ValidationError, URL
from wtforms_sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField

from ..models.image import Image
from ..models.category import Category
from ..extensions import db
from unidecode import unidecode
from ..models.attribute import Attribute
from ..models.directory import Directory
from ..models.post_category import PostCategory
from ..models.product import Product
from ..models.productOptions import ProductOption, ProductOptionValue, ProductVariation
from ..models.post import Post
from ..models.page import Page
from ..models.user import *
from ..models.role import *

def slugify(value):
    """
    Используем unidecode для транслитерации.
    """
    value = unidecode(value)
    value = re.sub(r'[^a-zA-Z0-9]+', '-', value.lower())
    value = value.strip('-')
    return value


def generate_unique_slug(base_slug):
    slug = base_slug
    counter = 1
    while Category.query.filter_by(slug=slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


#                Категории
class CategoryForm(FlaskForm):
    name = StringField('Название', validators=[DataRequired()])
    slug = StringField('Slug', validators=[Optional()])
    sort_order = IntegerField('Порядок сортировки', default=0)
    is_indexed = BooleanField('Индексировать', default=False)

    # Вместо QuerySelectField — hidden field
    image_id = HiddenField('image_id')
    # Можно хранить ID выбранного изображения
    description = TextAreaField('Описание')  # Новое поле
    meta_title = StringField('SEO Title')
    meta_description = TextAreaField('SEO Description')
    meta_keywords = StringField('SEO Keywords')

    parent = QuerySelectField(
        'Родительская категория',
        query_factory=lambda: [cat for cat, _ in get_hierarchical_categories()],
        get_label=lambda cat: next((display_name for c, display_name in get_hierarchical_categories() if c.id == cat.id), cat.name),
        allow_blank=True,
        blank_text='(Нет родительской)'
    )
    submit = SubmitField('Сохранить')

    def validate_slug(self, field):
        if field.data:
            existing = Category.query.filter_by(slug=field.data).first()
            category_id = getattr(self, 'category_id', None)
            if existing and (category_id is None or existing.id != category_id):
                raise ValidationError('Slug уже используется, выберите другой.')

    def process_slug(self, cat_id=None):
        if not self.slug.data:
            # Если slug не указан, генерируем из названия
            base_slug = slugify(self.name.data)
            if not base_slug:
                base_slug = 'category'
            self.slug.data = generate_unique_slug(base_slug)
        else:
            # Если slug указан, транслитерируем его на латиницу
            base_slug = slugify(self.slug.data)
            if not base_slug:
                # Если после транслитерации slug стал пустым, генерируем из названия
                base_slug = slugify(self.name.data) or 'category'
                self.slug.data = generate_unique_slug(base_slug)
            else:
                # Проверяем, не занят ли slug другой категорией
                if Category.query.filter(
                        Category.slug == base_slug,
                        Category.id != cat_id  # <-- не совпадает с текущим id
                ).first():
                    self.slug.data = generate_unique_slug(base_slug)
                else:
                    self.slug.data = base_slug


#                Каталоги

class DirectoryForm(FlaskForm):
    name = StringField('Название каталога', validators=[DataRequired()])
    parent_id = HiddenField()  # Будем скрыто задавать родителя
    submit = SubmitField('Сохранить')


#                Изображения
class ImageUploadForm(FlaskForm):
    image = FileField('Изображение', validators=[FileRequired(),
                                                 FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'svg', 'webp'],
                                                             'Только изображения!')])
    alt = StringField('Alt-текст', validators=[Optional()])
    directory_id = HiddenField()  # Скрыто зададим каталог
    submit = SubmitField('Загрузить')


class ImageEditForm(FlaskForm):
    alt = StringField('Alt-текст', validators=[Optional()])
    directory = QuerySelectField(
        'Каталог',
        query_factory=lambda: Directory.query.all(),
        get_label='name',
        allow_blank=True,
        blank_text='(Нет каталога)'
    )
    submit = SubmitField('Сохранить')


#               Атрибуты
class AttributeForm(FlaskForm):
    """Форма для атрибута"""
    attribute_name = StringField('Название атрибута', validators=[DataRequired()])
    attribute_value = StringField('Значение атрибута', validators=[DataRequired()])


def get_sorted_categories():
    categories = Category.query.all()

    def get_level1_sort_key(cat):
        # Если есть родитель, возвращаем его имя (1 уровень), иначе своё имя
        return cat.parent.name if cat.parent else cat.name

    # Сортируем сначала по 1-му уровню, потом по полному имени
    return sorted(categories, key=lambda c: (get_level1_sort_key(c).lower(), c.full_name().lower()))

def get_hierarchical_categories():
    """
    Возвращает категории с иерархической структурой для выбора родительской категории.
    Использует функцию build_category_list из модели Category.
    """
    from app.models.category import build_category_list
    categories_with_levels = build_category_list()
    
    # Создаем список с отступами для отображения иерархии
    hierarchical_categories = []
    for category, level in categories_with_levels:
        # Добавляем отступы для визуализации иерархии
        indent = "— " * level
        display_name = f"{indent}{category.name}"
        hierarchical_categories.append((category, display_name))
    
    return hierarchical_categories

def get_hierarchical_post_categories():
    """
    Возвращает категории постов с иерархической структурой для выбора родительской категории.
    """
    from app.models.post_category import PostCategory
    
    def build_post_category_list(parent_id=None, level=0):
        """
        Возвращает список кортежей (cat, level), где cat - объект PostCategory,
        а level - уровень вложения.
        """
        results = []
        query = PostCategory.query.filter_by(parent_id=parent_id).order_by(PostCategory.sort_order, PostCategory.id)
        for cat in query:
            results.append((cat, level))
            # рекурсивно добавляем дочерние
            results.extend(build_post_category_list(cat.id, level + 1))
        return results
    
    categories_with_levels = build_post_category_list()
    
    # Создаем список с отступами для отображения иерархии
    hierarchical_categories = []
    for category, level in categories_with_levels:
        # Добавляем отступы для визуализации иерархии
        indent = "— " * level
        display_name = f"{indent}{category.name}"
        hierarchical_categories.append((category, display_name))
    
    return hierarchical_categories

class ProductForm(FlaskForm):
    name = StringField('Название', validators=[DataRequired()])
    slug = StringField('Slug', validators=[Optional()])
    description = TextAreaField('Описание', validators=[Optional()])
    price = DecimalField('Цена', places=2, validators=[DataRequired()])
    stock = IntegerField('Количество на складе', validators=[DataRequired()])
    bonus_points = IntegerField('Бонусные баллы', default=0)
    sort_order = IntegerField('Порядок сортировки', default=0)
    is_indexed = BooleanField('Индексировать', default=True)

    # Поля SEO
    meta_title = StringField('SEO Title', validators=[Optional()])
    meta_description = TextAreaField('SEO Description', validators=[Optional()])
    meta_keywords = StringField('SEO Keywords', validators=[Optional()])

    # Выбор категории
    category = QuerySelectField(
        'Категория',
        query_factory=get_sorted_categories,
        get_label=lambda c: c.full_name(),
        allow_blank=True,
        blank_text='(Нет категории)'
    )

    # Поля для изображений
    main_image_id = HiddenField('ID главного изображения', validators=[DataRequired(message='Пожалуйста, выберите главное изображение.')])
    additional_image_ids = HiddenField('ID дополнительных изображений')

    submit = SubmitField('Сохранить')


class ProductOptionForm(FlaskForm):
    """
    Форма для создания/редактирования опции (напр. 'Цвет', 'Размер').
    """
    name = StringField('Название опции', validators=[DataRequired()])

    # Тип отображения (select, radio, checkbox и т.п.)
    display_type = SelectField(
        'Тип отображения',
        choices=[('select', 'Select'), ('radio', 'Radio'), ('checkbox', 'Checkbox')],
        default='select',
        validators=[DataRequired()]
    )

    # При необходимости: флаг для фильтрации
    # is_filterable = BooleanField('Использовать в фильтрах', default=True)

    submit = SubmitField('Сохранить опцию')


class ProductOptionValueForm(FlaskForm):
    """
    Форма для создания/редактирования значения опции
    (например, 'Красный' для 'Цвет').
    """
    value = StringField('Значение', validators=[DataRequired()])

    option = QuerySelectField(
        'Опция',
        query_factory=lambda: ProductOption.query.order_by(ProductOption.name).all(),
        get_label='name',
        allow_blank=False  # пользователь обязан выбрать какую-то опцию
    )

    submit = SubmitField('Сохранить значение')


class ProductVariationForm(FlaskForm):
    """
    Форма для создания/редактирования вариации товара.
    (SKU, цена, stock, SEO, + выбор значений опций)
    """
    sku = StringField('SKU', validators=[DataRequired()])
    price = DecimalField('Цена', places=2, validators=[DataRequired()])
    stock = IntegerField('Количество на складе', validators=[DataRequired()])
    slug = StringField('Slug', validators=[Optional()])

    # SEO поля
    seo_title = StringField('SEO Title', validators=[Optional()])
    seo_description = TextAreaField('SEO Description', validators=[Optional()])
    # Если нужно:
    # seo_keywords = StringField('SEO Keywords', validators=[Optional()])

    # Выбор значений опций (каждый entry в FieldList – один QuerySelectField)
    option_values = FieldList(
        QuerySelectField(
            'Значение опции',
            query_factory=lambda: ProductOptionValue.query.order_by(ProductOptionValue.value).all(),
            get_label='value',
            allow_blank=True
        ),
        min_entries=1,
        label='Значения опций'
    )

    submit = SubmitField('Сохранить вариацию')

    def validate_slug(self, field):
        if field.data:
            existing = ProductVariation.query.filter_by(slug=field.data).first()
            # Проверяем, не редактируем ли мы ту же вариацию
            # (Если нужно, сравниваем self.id, если форму передаём с hidden id)
            if existing:
                raise ValidationError('Этот slug уже используется для другой вариации.')


class ProductVariationNestedForm(FlaskForm):
    """
    Форма для списка вариаций.
    Позволяет редактировать/создавать несколько вариаций сразу.
    """
    variations = FieldList(
        FormField(ProductVariationForm),
        min_entries=1
    )

    submit = SubmitField('Сохранить все вариации')


class ExistingOptionForm(FlaskForm):
    option = StringField(
        'Существующая опция',
        render_kw={"list": "option-list", "autocomplete": "off"},
        validators=[Optional()]
    )
    display_type = SelectField(
        'Тип отображения',
        choices=[('select', 'Select'), ('radio', 'Radio'), ('checkbox', 'Checkbox'), ('color', 'Color')],
        validators=[DataRequired()]
    )
    values = SelectMultipleField(
        'Существующие значения',
        choices=[],
        validators=[Optional()],
        render_kw={"class": "select2"}
    )

    def __init__(self, *args, **kwargs):
        super(ExistingOptionForm, self).__init__(*args, **kwargs)
        self.option.choices = [(option.name, option.name) for option in
                               ProductOption.query.order_by(ProductOption.name).all()]

    def update_values(self, option_id):
        self.values.choices = [(value.id, value.value) for value in
                               ProductOptionValue.query.filter_by(product_option_id=option_id).order_by(
                                   ProductOptionValue.value).all()]


class PostCategoryForm(FlaskForm):
    name = StringField('Название', validators=[DataRequired()])
    slug = StringField('Slug', validators=[Optional()])
    parent = QuerySelectField(
        'Родительская категория',
        query_factory=lambda: [cat for cat, _ in get_hierarchical_post_categories()],
        get_label=lambda cat: next((display_name for c, display_name in get_hierarchical_post_categories() if c.id == cat.id), cat.name),
        allow_blank=True,
        blank_text='(Нет родительской категории)'
    )
    sort_order = IntegerField('Порядок сортировки', default=0)
    is_indexed = BooleanField('Индексировать', default=True)
    description = TextAreaField('Описание')
    meta_title = StringField('SEO Title')
    meta_description = TextAreaField('SEO Description')
    meta_keywords = StringField('SEO Keywords')
    submit = SubmitField('Сохранить')

    # Добавляем поле для хранения ID изображения
    image_id = HiddenField('Image ID', validators=[Optional()])

    def validate_slug(self, field):
        if field.data:
            existing = PostCategory.query.filter_by(slug=field.data).first()
            if existing:
                raise ValidationError("Slug уже используется, выберите другой.")

    def process_slug(self, category_id=None):
        if not self.slug.data:
            base_slug = slugify(self.name.data)
            self.slug.data = generate_unique_slug(base_slug)


class PostForm(FlaskForm):
    title = StringField("Заголовок", validators=[DataRequired()])
    category = QuerySelectField(
        'Категория',
        query_factory=lambda: PostCategory.query.all(),
        get_label='name',
        allow_blank=True,
        blank_text='(Нет категории)'
    )
    slug = StringField("Slug (URL)", validators=[])
    content = TextAreaField("Содержимое", validators=[])
    meta_title = StringField("SEO Title", validators=[Optional()])
    meta_description = TextAreaField("SEO Description", validators=[Optional()])
    meta_keywords = StringField("SEO Keywords", validators=[Optional()])
    image = FileField("Изображение", validators=[Optional(), FileAllowed(['jpg', 'png', 'gif', 'jpeg'], "Только изображения")])
    published_at = DateTimeField("Дата публикации", format="%Y-%m-%d %H:%M:%S", validators=[Optional()])
    is_published = BooleanField("Опубликовано", default=False)
    submit = SubmitField("Сохранить")
    image_id = HiddenField('image_id')

    def validate_slug(self, field):
        if field.data:
            existing = Post.query.filter_by(slug=field.data).first()
            if existing:
                raise ValidationError("Slug уже используется, выберите другой.")

    def process_slug(self):
        if not self.slug.data:
            base_slug = slugify(self.title.data)
            self.slug.data = generate_unique_slug(base_slug)



class SocialLinkForm(FlaskForm):
    platform = StringField("Платформа", validators=[DataRequired()])
    url = StringField("URL", validators=[DataRequired(), URL()])
    icon_id = HiddenField("Иконка ID", validators=[Optional()])
    submit = SubmitField("Сохранить")
    icon = HiddenField("иконка", validators=[Optional()])


class SiteSettingsForm(FlaskForm):
    title = StringField("Название сайта", validators=[DataRequired()])
    image_id = HiddenField('Логотип ID', validators=[Optional()])
    address = StringField("Адрес", validators=[Optional()])
    email = StringField("Email", validators=[Optional()])
    phone = StringField("Телефон", validators=[Optional()])
    owner = StringField("Владелец", validators=[Optional()])
    working_hours = StringField("Режим работы", validators=[Optional()])
    social_links = FieldList(FormField(SocialLinkForm), min_entries=1, max_entries=5)
    additional_info = TextAreaField("Дополнительная информация", validators=[Optional()])
    home_page_id = QuerySelectField(
        'Домашняя страница',
        query_factory=lambda: Page.query.all(),
        get_label='title',
        allow_blank=True,
        blank_text='(Нет страниц)'
    )
    map_locations = StringField("Карта", validators=[Optional()])
    submit = SubmitField("Сохранить")

class UserForm(FlaskForm):
    user_id = HiddenField('Идентификатор',  validators=[Optional()])
    username = StringField('Имя пользовате', validators=[DataRequired()])
    email = StringField('Email', validators=[Optional()])
    password = PasswordField('Пароль')
    role = QuerySelectField('Роль',
                            query_factory=lambda: Role.query.all(),
                            get_label='name',
                            allow_blank=True)
    submit = SubmitField("Сохранить")