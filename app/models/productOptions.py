from ..extensions import db
from datetime import datetime
from .base import BaseModel

# --------------------------------
#  M2M: Товар – Опция
# --------------------------------
product_option_association = db.Table(
    'product_option_association',
    db.Column('product_id', db.Integer, db.ForeignKey('products.id'), primary_key=True),
    db.Column('option_id', db.Integer, db.ForeignKey('product_options.id'), primary_key=True),
    db.Index('idx_product_option_association_pid_oid', 'product_id', 'option_id'),
    db.Index('idx_product_option_association_oid_pid', 'option_id', 'product_id')
)

# --------------------------------
#  M2M: Товар – Значение Опции (ограничивает допустимые значения для товара)
# --------------------------------
product_option_value_association = db.Table(
    'product_option_value_association',
    db.Column('product_id', db.Integer, db.ForeignKey('products.id'), primary_key=True),
    db.Column('option_value_id', db.Integer, db.ForeignKey('product_option_values.id'), primary_key=True),
    db.Index('idx_product_option_value_association_pid_ovid', 'product_id', 'option_value_id'),
    db.Index('idx_product_option_value_association_ovid_pid', 'option_value_id', 'product_id')
)


class ProductOption(BaseModel):
    __tablename__ = 'product_options'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, index=True)
    display_type = db.Column(db.String(50), nullable=False, default='select')
    is_filterable = db.Column(db.Boolean, default=True)
    has_individual_photos = db.Column(db.Boolean, default=False)  # Новое поле для индивидуальных фото
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Список возможных значений (One-to-Many)
    values = db.relationship(
        'ProductOptionValue',
        backref='option',
        cascade='all, delete-orphan'
    )

    @classmethod
    def get_options_by_product_id(cls, product_id):
        # Получаем все значения опций, связанные с данным продуктом
        option_values = db.session.query(ProductOptionValue).join(
            product_option_value_association,
            (product_option_value_association.c.option_value_id == ProductOptionValue.id)
        ).filter(
            product_option_value_association.c.product_id == product_id
        ).all()
        # Создаем словарь для хранения опций и их значений
        options_dict = {}

        for value in option_values:
            option_id = value.option.id
            option_name = value.option.name
            optin_type = value.option.display_type
            has_individual_photos = value.option.has_individual_photos
            if option_id not in options_dict:
                options_dict[option_id] = {
                    'id': option_id,
                    'name': option_name,
                    'display_type': optin_type,
                    'has_individual_photos': has_individual_photos,
                    'values': []
                }
            # Загружаем фотографии для этого значения опции
            photos = []
            if value.images:
                for img_rel in value.images:
                    if img_rel.image:
                        photos.append({
                            'id': img_rel.image.id,
                            'path': img_rel.image.filename,  # Используем filename вместо path
                            'order': img_rel.order,
                            'is_main': img_rel.is_main
                        })
            
            options_dict[option_id]['values'].append({
                'id': value.id,
                'value': value.value,
                'photos': photos
            })

        # Возвращаем список словарей с id, name и values опций
        return list(options_dict.values())


class ProductOptionValue(BaseModel):
    """
    Глобальное значение опции (напр. 'Красный' для 'Цвет'),
    которое может использоваться в разных товарах.
    """
    __tablename__ = 'product_option_values'
    id = db.Column(db.Integer, primary_key=True)
    option_id = db.Column(db.Integer, db.ForeignKey('product_options.id'), nullable=False, index=True)
    value = db.Column(db.String(255), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Связка с вариациями (через таблицу product_variation_option_values)
    variations = db.relationship(
        'ProductVariationOptionValue',
        backref='option_value',
        cascade='all, delete-orphan'
    )
    # Связь с фотографиями значений опций
    images = db.relationship(
        'ProductOptionValueImage',
        backref='option_value',
        cascade='all, delete-orphan'
    )


class ProductOptionValueImage(BaseModel):
    """
    Фотографии для значений опций (например, фото красного цвета товара)
    """
    __tablename__ = 'product_option_value_images'
    id = db.Column(db.Integer, primary_key=True)
    option_value_id = db.Column(db.Integer, db.ForeignKey('product_option_values.id'), nullable=False, index=True)
    image_id = db.Column(db.Integer, db.ForeignKey('images.id'), nullable=False)
    order = db.Column(db.Integer, default=0)  # Порядок отображения фото
    is_main = db.Column(db.Boolean, default=False)  # Главное фото для этого значения
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связь с изображением
    image = db.relationship('Image', backref='option_value_images')
    
    __table_args__ = (
        db.Index('idx_option_value_image', 'option_value_id', 'image_id'),
    )


class ProductVariation(BaseModel):
    """
    Вариация товара (напр. 'Футболка, Цвет=Красный, Размер=M').
    - Ссылается на products.id (товар уже существует в вашем проекте).
    - У каждой вариации свои SKU, цена, склад, SEO.
    """
    __tablename__ = 'product_variations'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    # Уникальный артикул/код
    sku = db.Column(db.String(255), nullable=True, index=True)
    # Цена и остаток конкретно для этой вариации
    price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    stock = db.Column(db.Integer, nullable=True, default=0)
    # SEO-поля
    slug = db.Column(db.String(255), nullable=True, unique=True, index=True)
    seo_title = db.Column(db.String(255), nullable=True)
    seo_keys = db.Column(db.String(255), nullable=True)
    seo_description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    image_id = db.Column(db.Integer, db.ForeignKey('images.id'), nullable=True)
    variation_image = db.relationship('Image', foreign_keys=[image_id])
    # Связь "Вариация – Значения опций"
    option_values = db.relationship(
        'ProductVariationOptionValue',
        backref='variation',
        cascade='all, delete-orphan'
    )

    @classmethod
    def get_variations_by_product_id(cls, product_id):
        variations = db.session.query(cls).filter(cls.product_id == product_id).all()
        variations_dict = {}

        for variation in variations:
            # Собираем HTML для опций
            combo_html = ""
            option_value_ids = []  # Добавляем список ID значений опций
            combo_ids_list = []  # Пары option_id/value_id для каждой выбранной опции
            
            for pvov in variation.option_values:
                # pvov.option_value => объект ProductOptionValue
                # pvov.option_value.option => объект ProductOption
                option_name = pvov.option_value.option.name if pvov.option_value and pvov.option_value.option else ""
                option_value = pvov.option_value.value if pvov.option_value else ""
                # Если нужно пропустить пустые:
                if not option_name or not option_value:
                    continue
                combo_html += f"<strong>{option_name}:</strong> {option_value}<br>"
                option_value_ids.append(pvov.option_value.id)
                # Сохраняем пару IDшников, чтобы уметь восстанавливать скрытые inputs без регенерации
                if pvov.option_value and pvov.option_value.option:
                    combo_ids_list.append({
                        'option_id': pvov.option_value.option.id,
                        'value_id': pvov.option_value.id
                    })

            # Обрабатываем изображение вариации
            variation_image_data = None
            if variation.variation_image:
                variation_image_data = {
                    'id': variation.variation_image.id,
                    'filename': variation.variation_image.filename,
                    'path': variation.variation_image.filename  # используем filename как path
                }

            variations_dict[variation.id] = {
                'id': variation.id,
                'price': float(variation.price) if variation.price else 0,
                'sku': variation.sku or '',
                'slug': variation.slug or '',
                'stock': variation.stock or 0,
                'seo_title': variation.seo_title or '',
                'seo_description': variation.seo_description or '',
                'seo_keywords': variation.seo_keys or '',
                'image_id': variation.image_id,
                'variation_image': variation_image_data,
                'option_value_ids': option_value_ids,  # Добавляем список ID значений опций
                'combo_ids': combo_ids_list,  # Добавляем пары option_id/value_id
                # Добавляем наш combo_html
                'combo_html': combo_html
            }

        return variations_dict

    # Пример метода для автогенерации slug
    def generate_slug(self):
        if not self.slug:
            # Собираем названия значений опций, например: "color-red-size-l"
            option_value_names = [ov.option_value.value for ov in self.option_values]
            base_slug = f"product-{self.product_id}-{'-'.join(option_value_names)}"
        else:
            base_slug = self.slug

        unique_slug = base_slug
        counter = 1
        existing = ProductVariation.query.filter(
            ProductVariation.slug.like(f"{base_slug}%"),
            ProductVariation.id != self.id
        ).first()

        while existing:
            counter += 1
            unique_slug = f"{base_slug}-{counter}"
            existing = ProductVariation.query.filter(
                ProductVariation.slug == unique_slug,
                ProductVariation.id != self.id
            ).first()

        self.slug = unique_slug


class ProductVariationOptionValue(BaseModel):
    """
    Промежуточная сущность, указывающая, какие именно
    'option_value' (значения опции) участвуют в данной вариации.
    Например, вариант "Красный" для опции "Цвет".
    """
    __tablename__ = 'product_variation_option_values'
    id = db.Column(db.Integer, primary_key=True)
    variation_id = db.Column(db.Integer, db.ForeignKey('product_variations.id'), nullable=False, index=True)
    option_value_id = db.Column(db.Integer, db.ForeignKey('product_option_values.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # При желании можно добавить индекс:
    __table_args__ = (
        db.Index('idx_variation_option_value', 'variation_id', 'option_value_id'),
    )
