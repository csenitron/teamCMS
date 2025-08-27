import os

from sqlalchemy.dialects.mysql import JSON

from .category import getSybCategoryByID
from ..extensions import db
from .base import BaseModel
from datetime import datetime
import re
import unicodedata
from unidecode import unidecode

product_images = db.Table(
    'product_images',
    db.Column('product_id', db.Integer, db.ForeignKey('products.id'), primary_key=True),
    db.Column('image_id', db.Integer, db.ForeignKey('images.id'), primary_key=True,default=0),
    db.Column('order', db.Integer)
)


class Product(BaseModel):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), index=True, nullable=False)
    slug = db.Column(db.String(255), unique=True)  # Slug
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    stock = db.Column(db.Integer, nullable=False, default=0)
    bonus_points = db.Column(db.Integer, nullable=False, default=0)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    main_image_id = db.Column(db.Integer, db.ForeignKey('images.id'), nullable=True)
    qr_code_path = db.Column(db.String(255), nullable=True)
    barcode = db.Column(db.String(255), nullable=True)
    is_indexed = db.Column(db.Boolean, default=True)  # Флаг индексирования
    sort_order = db.Column(db.Integer, default=0)  # Порядок сортировки
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    category = db.relationship('Category', backref='products')
    main_image = db.relationship('Image', foreign_keys=[main_image_id], backref='main_image_products')
    additional_images = db.relationship(
        'Image',
        secondary='product_images',
        backref='products'
    )

    __table_args__ = (
        db.Index('idx_product_name', 'name'),
        db.Index('idx_product_slug', 'slug'),
    )

    def total_stock(self):
        """Общее количество товара на всех складах."""
        return sum(stock.stock for stock in self.warehouse_stocks)

    def generate_qr_code(self):
        """Генерация QR-кода для товара."""
        import qrcode
        from flask import current_app

        qr_url = f"/products/{self.id}"  # Замените на реальный URL
        qr = qrcode.QRCode(box_size=10, border=4)
        qr.add_data(qr_url)
        qr.make(fit=True)

        path = f"qr_codes/product_{self.id}.png"
        qr_image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], path)
        img = qr.make_image(fill="black", back_color="white")
        img.save(qr_image_path)

        self.qr_code_path = path

    def generate_barcode(self):
        """Генерация штрих-кода."""
        from barcode import EAN13
        from barcode.writer import ImageWriter
        from flask import current_app

        code = f"{self.id:012}"  # EAN-13 требует 12-значного кода
        path = f"barcodes/product_{self.id}.png"
        barcode_image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], path)

        barcode = EAN13(code, writer=ImageWriter())
        barcode.save(barcode_image_path)

        self.barcode = code

    def process_slug(self):
        """
        Если slug пустой, генерируем на основе name.
        Если slug уже есть — проверяем уникальность.
        Если занято, добавляем -1, -2 и т.д.
        """

        # Внутренняя вспомогательная функция, чтобы не импортировать из views.py
        def _slugify(value):
            try:
                from unidecode import unidecode
                value = unidecode(value)
            except ImportError:
                # Fallback если unidecode не установлен
                value = unicodedata.normalize('NFKD', value)
                value = value.encode('ascii', 'ignore').decode('ascii')
            value = re.sub(r'[^a-zA-Z0-9]+', '-', value.lower())
            return value.strip('-')

        if not self.slug:
            # Генерируем из self.name
            base = _slugify(self.name) or 'product'
        else:
            # Пользователь мог ввести вручную slug, но мы его тоже "приведём"
            base = _slugify(self.slug)
            if not base:
                base = 'product'

        # Проверяем, нет ли уже в БД товара с таким же slug
        unique_slug = base
        counter = 1

        from .product import Product  # или from ..models.product import Product
        # Ищем, не занят ли уже unique_slug (учитываем текущий self.id).
        existing = Product.query.filter(Product.slug == unique_slug, Product.id != self.id).first()

        while existing:
            # Если нашли конфликт, добавляем -1, -2, ...
            counter += 1
            unique_slug = f"{base}-{counter}"
            existing = Product.query.filter(Product.slug == unique_slug, Product.id != self.id).first()

        # Присваиваем в slug результат
        self.slug = unique_slug
def get_all_subcategory_ids(category_id):
    ids = [category_id]
    subcategories = getSybCategoryByID(category_id)
    for subcat in subcategories:
        ids.extend(get_all_subcategory_ids(subcat.id))
    return ids

def getProductsByCategoryID(category_id):
    category_ids = get_all_subcategory_ids(category_id)
    products = Product.query.filter(Product.category_id.in_(category_ids)).all()
    return products


def getProductBySlug(product_slug):
    product = Product.query.filter(Product.slug == product_slug).first()
    return product


# Модель для связанных товаров
class RelatedProduct(BaseModel):
    __tablename__ = 'related_products'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    related_product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    link_text = db.Column(db.String(255), nullable=False)  # Текст ссылки (например, "детям", "мужское")
    sort_order = db.Column(db.Integer, default=0)  # Порядок сортировки
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Отношения
    product = db.relationship('Product', foreign_keys=[product_id], backref='related_products')
    related_product = db.relationship('Product', foreign_keys=[related_product_id], backref='related_to_products')
    
    __table_args__ = (
        db.Index('idx_related_product', 'product_id'),
        db.Index('idx_related_related_product', 'related_product_id'),
        db.UniqueConstraint('product_id', 'related_product_id', name='unique_related_product'),
    )
