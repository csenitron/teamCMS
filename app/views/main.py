from click import option
from flask import Blueprint, render_template, redirect, jsonify, request, flash, url_for, session
from ..extensions import db, csrf
import json
import decimal as _decimal
import os

from ..models.productOptions import ProductOption, ProductVariation, ProductOptionValue, ProductVariationOptionValue
from ..models.category import *
from ..models.product import *
from ..models.seo_settings import *
from ..models.page import *
from ..models.site_setings import *
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from ..models.module import *
from ..models.customer import *
from ..models.favorite import *
from ..models.cart import *
from ..models.shipping import ShippingMethod
from ..models.tax import TaxRate
from ..models.order import Order, OrderItem
from ..models.customer_address import CustomerAddress
from ..models.size_chart import SizeChart, ProductSizeChart
from ..models.review import Review
from ..models.review_vote import ReviewVote
import importlib
import uuid
from urllib.parse import urlparse, urljoin

main_bp = Blueprint('main', __name__)

# Alias to satisfy linters and explicit usage
Decimal = _decimal.Decimal


def get_all_subcategories(category_id):
    """Получить все подкатегории категории (включая саму категорию)"""
    subcategories = [category_id]
    children = Category.query.filter(Category.parent_id == category_id).all()
    for child in children:
        subcategories.extend(get_all_subcategories(child.id))
    return subcategories





module_classes = {}

# Универсальная динамическая загрузка модулей (фронт и админка)
_modules_dir = os.path.join(os.path.dirname(__file__), "modules")
_module_files = [f for f in os.listdir(_modules_dir) if f.endswith('.py') and f != '__init__.py']

for _filename in _module_files:
    # Порядок важен: сначала фронт (имеет get_instance_data), затем админка
    for _ns in ("app.views.modules", "app.admin.modules"):
        _module_name = f"{_ns}.{_filename[:-3]}"
        try:
            _module = importlib.import_module(_module_name)
            print(f"Модуль загружен: {_module_name}")

            for _attr in dir(_module):
                _obj = getattr(_module, _attr)
                if isinstance(_obj, type) and (hasattr(_obj, 'get_instance_data') or hasattr(_obj, 'save_instance')):
                    _existing = module_classes.get(_attr)
                    # Не перезаписываем фронтовый класс админским; класс с get_instance_data имеет приоритет
                    if _existing is None:
                        module_classes[_attr] = _obj
                        print(f"Добавлен класс {_attr} в module_classes")
                    else:
                        has_front = hasattr(_existing, 'get_instance_data')
                        has_front_new = hasattr(_obj, 'get_instance_data')
                        if not has_front and has_front_new:
                            module_classes[_attr] = _obj
                            print(f"Заменён класс {_attr} фронтовой версией")
        except Exception as e:
            print(f"Ошибка при загрузке модуля {_module_name}: {e}")

print("Загруженные модули:", module_classes)


@main_bp.route('/')
def index():
    categories = getPcats()
    home_page = getHomePage()
    seo = SEOSettings('page', home_page.id, home_page.meta_title, home_page.meta_description, home_page.meta_keywords)
    site_settings = getSiteSettings()
    layouts = getPageLayout(home_page.id)
    auth = bool(current_user.is_authenticated and isinstance(current_user, Customer))
    print(auth)
    modules_data = []
    for layout in sorted(layouts, key=lambda x: (x.row_index, x.col_index)):
        if layout.module_instance_id:
            module_instance = ModuleInstance.query.get(layout.module_instance_id)
            if module_instance:
                # Базовые данные модуля
                # Преобразуем settings в dict, если в БД хранится JSON-строка
                try:
                    parsed_settings = (json.loads(module_instance.settings)
                                       if isinstance(module_instance.settings, str) and module_instance.settings else
                                       (module_instance.settings or {}))
                except Exception:
                    parsed_settings = {}

                module_data = {
                    'row_index': layout.row_index,
                    'col_index': layout.col_index,
                    'col_width': layout.col_width,
                    'module_name': module_instance.module.name.lower().replace(" ", "_"),
                    'template': module_instance.selected_template,
                    'settings': parsed_settings,
                    'content': module_instance.content,
                    'instance': module_instance
                }

                # Динамически определяем класс модуля
                module_class_name = module_instance.module.name  # Например, "SliderModule"
                module_class = module_classes.get(module_class_name)
                if module_class and hasattr(module_class, 'get_instance_data'):
                    # Добавляем специфичные данные модуля
                    module_data.update(module_class.get_instance_data(module_instance))
                else:
                    # Фоллбек-логика для известных модулей фронта, если фронтовый класс не загрузился
                    try:
                        if module_class_name == 'BannerModule':
                            from ..models.modules.banner import BannerModuleInstance, BannerItem
                            banner_instance = BannerModuleInstance.query.filter_by(module_instance_id=module_instance.id).first()
                            banner_items = BannerItem.query.filter_by(banner_id=banner_instance.id).all() if banner_instance else []
                            module_data.update({
                                'banner': banner_instance,
                                'banner_items': banner_items,
                            })
                        elif module_class_name == 'TabsModule':
                            from ..models.modules.product_tab import TabsModuleInstance, TabItem
                            from ..models.product import Product
                            from ..models.productOptions import ProductOption
                            tabs_instance = TabsModuleInstance.query.filter_by(module_instance_id=module_instance.id).first()
                            tab_items = TabItem.query.filter_by(tabs_id=tabs_instance.id).all() if tabs_instance else []
                            tab_products = {}
                            for tab_item in tab_items:
                                if tab_item.mode == 'category' and tab_item.category_id:
                                    products = Product.query.filter_by(category_id=tab_item.category_id).limit(tab_item.limit_count).all()
                                    for p in products:
                                        p.product_options = ProductOption.get_options_by_product_id(p.id)
                                    tab_products[tab_item.id] = products
                                elif tab_item.mode == 'custom' and tab_item.product_ids:
                                    ids = [int(pid) for pid in (tab_item.product_ids or '').split(',') if pid.strip().isdigit()]
                                    products = Product.query.filter(Product.id.in_(ids)).all() if ids else []
                                    for p in products:
                                        p.product_options = ProductOption.get_options_by_product_id(p.id)
                                    tab_products[tab_item.id] = products
                                elif tab_item.mode == 'all':
                                    products = Product.query.limit(tab_item.limit_count or 8).all()
                                    for p in products:
                                        p.product_options = ProductOption.get_options_by_product_id(p.id)
                                    tab_products[tab_item.id] = products
                                else:
                                    tab_products[tab_item.id] = []
                            module_data.update({
                                'tabs_instance': tabs_instance,
                                'tab_items': tab_items,
                                'tab_products': tab_products,
                            })
                        else:
                            print(f"Класс для модуля {module_class_name} не найден в module_classes")
                    except Exception as e:
                        print(f"Ошибка фоллбека для {module_class_name}: {e}")

                modules_data.append(module_data)

    print("Данные модулей:", modules_data)
    return render_template('index.html', categories=categories, homePage=home_page, seo=seo,
                           site_settings=site_settings, modules=modules_data, auth=auth)


@main_bp.route('/category/<category_slug>')
def category(category_slug):
    if category_slug is None:
        return redirect('/')

    auth = bool(current_user.is_authenticated and isinstance(current_user, Customer))
    category = getCategoryBySlug(category_slug)
    cat_products = getProductsByCategoryID(category.id)
    categories = getPcats()
    seo = getSEO('category', category.id)
    subCategories = getSybCategoryByID(category.id)
    site_settings = getSiteSettings()
    
    # Загружаем все изображения для товаров с правильным порядком
    from app.models.product import product_images
    from app.models.image import Image
    
    product_images_data = {}
    for product in cat_products:
        # Создаем список изображений
        images_list = []
        
        # Добавляем главное изображение в начало
        if product.main_image:
            product.main_image.order = -1  # Главное изображение будет первым
            images_list.append(product.main_image)
        
        # Получаем все дополнительные изображения товара с порядком
        images_with_order = db.session.query(Image, product_images.c.order) \
            .join(product_images, Image.id == product_images.c.image_id) \
            .filter(product_images.c.product_id == product.id) \
            .order_by(product_images.c.order) \
            .all()
        
        # Добавляем дополнительные изображения
        for img, order in images_with_order:
            # Проверяем, что это не главное изображение
            if img.id != product.main_image_id:
                img.order = order  # Добавляем order как динамический атрибут
                images_list.append(img)
        
        # Добавляем в словарь
        product_images_data[product.id] = images_list

    # Загружаем опции для всех товаров в списке
    product_options = {}
    all_options = {}  # Собираем все уникальные опции для фильтров
    all_attributes = {}  # Собираем все уникальные атрибуты для фильтров
    
    for product in cat_products:
        options = ProductOption.get_options_by_product_id(product.id)
        product_options[product.id] = options
        
        # Собираем уникальные опции для фильтров
        for option in options:
            option_name = option['name']
            if option_name not in all_options:
                all_options[option_name] = {
                    'id': option['id'],
                    'name': option_name,
                    'display_type': option['display_type'],
                    'values': {}
                }
            
            # Собираем уникальные значения опций
            for value in option['values']:
                value_id = value['id']
                if value_id not in all_options[option_name]['values']:
                    all_options[option_name]['values'][value_id] = {
                        'id': value_id,
                        'value': value['value'],
                        'count': 0
                    }
                all_options[option_name]['values'][value_id]['count'] += 1
    
    # Преобразуем в списки для удобства в шаблоне
    filter_options = []
    for option_name, option_data in all_options.items():
        option_values = list(option_data['values'].values())
        filter_options.append({
            'id': option_data['id'],
            'name': option_name,
            'display_type': option_data['display_type'],
            'option_values': option_values  # Переименовываем values в option_values
        })

    return render_template(
        'front/category.html',
        categories=categories,
        category=category,
        cat_products=cat_products,
        seo=seo,
        subCategories=subCategories,
        site_settings=site_settings,
        auth=auth,
        product_options=product_options,
        filter_options=filter_options,  # Добавляем опции для фильтров
        product_images_data=product_images_data  # Добавляем данные изображений
    )


@main_bp.route('/product/<product_slug>')
def product(product_slug):
    if product_slug is None:
        return redirect('/')

    auth = bool(current_user.is_authenticated and isinstance(current_user, Customer))
    categories = getPcats()
    product = getProductBySlug(product_slug)
    seo = getSEO('product', product.id)
    site_settings = getSiteSettings()
    options = ProductOption.get_options_by_product_id(product.id)
    variations = ProductVariation.get_variations_by_product_id(product.id)

    # Получаем до 6 других товаров из той же категории
    related_products = Product.query.filter(
        Product.category_id == product.category_id,
        Product.id != product.id  # исключаем текущий товар
    ).order_by(Product.sort_order, Product.id).limit(6).all()

    # Получаем связанные товары
    from ..models.product import RelatedProduct
    related_products_data = RelatedProduct.query.filter_by(product_id=product.id).order_by(RelatedProduct.sort_order).all()

    # Получаем опции для этих товаров
    product_options = {}
    for related in related_products:
        product_options[related.id] = ProductOption.get_options_by_product_id(related.id)

    # Вычисляем верхнюю категорию для хлебных крошек
    top_category = product.category
    try:
        guard = 0
        while getattr(top_category, 'parent', None) is not None and guard < 20:
            top_category = top_category.parent
            guard += 1
    except Exception:
        top_category = product.category

    # Готовим список атрибутов для вывода (имя -> значение)
    try:
        product_attributes_display = []
        for pa in getattr(product, 'attributes', []) or []:
            if getattr(pa, 'attribute_value', None) and getattr(pa.attribute_value, 'attribute', None):
                product_attributes_display.append({
                    'name': pa.attribute_value.attribute.name,
                    'value': pa.attribute_value.value
                })
    except Exception:
        product_attributes_display = []

    # Привязанная к товару размерная сетка
    try:
        size_chart = product.size_chart_link.size_chart if getattr(product, 'size_chart_link', None) else None
    except Exception:
        size_chart = None

    # Отзывы: только одобренные, статистика
    try:
        approved_reviews = [r for r in getattr(product, 'reviews', []) or [] if getattr(r, 'approved', False)]
        approved_reviews.sort(key=lambda r: r.created_at or datetime.min, reverse=True)
        rating_total = len(approved_reviews)
        if rating_total:
            rating_sum = sum(int(getattr(r, 'rating', 0) or 0) for r in approved_reviews)
            rating_avg = round(rating_sum / rating_total, 1)
            rating_counts = {i: 0 for i in range(1, 6)}
            for r in approved_reviews:
                val = int(getattr(r, 'rating', 0) or 0)
                if 1 <= val <= 5:
                    rating_counts[val] += 1
            # считаем долю рекомендующих (если поле recommend задано), fallback на рейтинг>=4
            recommend_votes = 0
            for r in approved_reviews:
                if getattr(r, 'recommend', None) is True:
                    recommend_votes += 1
                elif getattr(r, 'recommend', None) is None and getattr(r, 'rating', 0) >= 4:
                    recommend_votes += 1
            recommend_percent = int(round(100 * (recommend_votes / rating_total)))
        else:
            rating_avg = 0
            rating_counts = {i: 0 for i in range(1, 6)}
            recommend_percent = 0
    except Exception:
        approved_reviews = []
        rating_total = 0
        rating_avg = 0
        rating_counts = {i: 0 for i in range(1, 6)}
        recommend_percent = 0

    return render_template(
        'front/product2.html',
        product=product,
        categories=categories,
        seo=seo,
        site_settings=site_settings,
        auth=auth,
        options=options,
        variations=variations,
        cat_products=related_products,
        product_options=product_options,
        top_category=top_category,
        product_attributes=product_attributes_display,
        size_chart=size_chart,
        approved_reviews=approved_reviews,
        rating_total=rating_total,
        related_products_data=related_products_data,
        rating_avg=rating_avg,
        rating_counts=rating_counts,
        recommend_percent=recommend_percent
    )


@main_bp.route('/product/<int:product_id>/review', methods=['POST'])
def submit_review(product_id):
    # Доступно только покупателям
    # Разрешаем гостевые отзывы: имя и email обязательны для неавторизованных
    if not (current_user.is_authenticated and isinstance(current_user, Customer)):
        guest_name = request.form.get('guest_name', '').strip()
        guest_email = request.form.get('guest_email', '').strip()
        if not guest_name or not guest_email:
            msg = 'Укажите имя и email'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify(ok=False, message=msg), 400
            from ..models.product import Product
            product = Product.query.get_or_404(product_id)
            flash(msg, 'warning')
            return redirect(url_for('main.product', product_slug=product.slug))

    rating = request.form.get('rating', type=int)
    sizing_score = request.form.get('sizing_score', type=int)
    quality_score = request.form.get('quality_score', type=int)
    comfort_score = request.form.get('comfort_score', type=int)
    comment = request.form.get('comment', '').strip()
    recommend = request.form.get('recommend') == 'on'

    guest_name = request.form.get('guest_name')
    guest_email = request.form.get('guest_email')

    review = Review(
        product_id=product_id,
        customer_id=(current_user.id if (current_user.is_authenticated and isinstance(current_user, Customer)) else None),
        rating=rating or 0,
        sizing_score=sizing_score,
        quality_score=quality_score,
        comfort_score=comfort_score,
        comment=comment,
        recommend=recommend,
        approved=False,
        guest_name=guest_name,
        guest_email=guest_email,
    )
    db.session.add(review)
    db.session.commit()
    flash('Отзыв отправлен и будет опубликован после модерации', 'success')
    # Возвращаем JSON для AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(ok=True)
    # Fallback на обычный редирект
    from ..models.product import Product
    product = Product.query.get_or_404(product_id)
    return redirect(url_for('main.product', product_slug=product.slug))


@main_bp.route('/reviews/<int:review_id>/vote', methods=['POST'])
@csrf.exempt
def vote_review(review_id: int):
    review = Review.query.get_or_404(review_id)
    payload = request.get_json(silent=True) or {}
    action = payload.get('action') or request.form.get('action')
    if action not in ('like', 'dislike'):
        return jsonify(ok=False, message='invalid action'), 400

    # voter key
    if current_user.is_authenticated and isinstance(current_user, Customer):
        voter_key = (getattr(current_user, 'email', None) or str(current_user.id)).strip().lower()
    else:
        voter_key = (request.headers.get('X-Forwarded-For', request.remote_addr) or '').split(',')[0].strip()
        if not voter_key:
            return jsonify(ok=False, message='no voter key'), 400

    # dedup
    existing = ReviewVote.query.filter_by(review_id=review.id, voter_key=voter_key).first()
    if existing:
        return jsonify(ok=False, message='duplicate', likes=review.likes or 0, dislikes=review.dislikes or 0), 409

    db.session.add(ReviewVote(review_id=review.id, voter_key=voter_key))
    if action == 'like':
        review.likes = (review.likes or 0) + 1
    else:
        review.dislikes = (review.dislikes or 0) + 1
    db.session.commit()
    return jsonify(ok=True, likes=review.likes or 0, dislikes=review.dislikes or 0)


@main_bp.route('/product/<int:product_id>/reviews', methods=['GET'])
def get_product_reviews(product_id: int):
    """Возвращает порцию отзывов по товару для кнопки "Показать ещё".
    Параметры: offset, limit.
    Ответ: { ok, html, next_offset, has_more }
    """
    offset = request.args.get('offset', default=0, type=int) or 0
    limit = request.args.get('limit', default=2, type=int) or 2
    if limit < 1:
        limit = 2

    base_query = Review.query.filter_by(product_id=product_id, approved=True).order_by(Review.created_at.desc())
    total_count = base_query.count()
    reviews = base_query.offset(offset).limit(limit).all()

    html = render_template('front/_review_card.html', reviews=reviews)
    next_offset = offset + len(reviews)
    has_more = next_offset < total_count

    return jsonify(ok=True, html=html, next_offset=next_offset, has_more=has_more)

@main_bp.route('/search', methods=['GET'])
def search_products():
    query = request.args.get('query', '')  # Получаем текст поиска из запроса
    if len(query) > 3:  # Ограничение: минимум 4 символа
        # Ищем товары, где название содержит query (регистронезависимо)
        products = Product.query.filter(Product.name.ilike(f'%{query}%')).limit(10).all()
        # Преобразуем в список словарей
        results = [{'name': p.name, 'slug': p.slug, 'image': p.main_image.filename, 'price': p.price} for p in products]
        print(results)
        return jsonify(results)  # Возвращаем JSON

    return jsonify([])


@main_bp.route('/category/<category_slug>/filter', methods=['POST'])
@csrf.exempt
def filter_category_products(category_slug):
    """Применение фильтров к товарам категории"""
    try:
        data = request.get_json()
        filters = data.get('filters', {})
        sort = data.get('sort', 'popular')
        
        print(f"=== FILTER REQUEST ===")
        print(f"Category: {category_slug}")
        print(f"Filters: {filters}")
        print(f"Sort: {sort}")
        
        # Получаем категорию
        category = Category.query.filter_by(slug=category_slug).first()
        if not category:
            return jsonify({'error': 'Category not found'}), 404
        
        # Получаем все подкатегории текущей категории
        all_category_ids = get_all_subcategories(category.id)
        
        # Базовый запрос для товаров категории и всех подкатегорий
        products_query = Product.query.filter(Product.category_id.in_(all_category_ids))
        
        # Применяем фильтры по опциям
        if filters:
            for option_id, value_ids in filters.items():
                if value_ids:  # Если есть выбранные значения
                    # Получаем товары, у которых есть эта опция с выбранными значениями
                    option_id = int(option_id)
                    value_ids = [int(vid) for vid in value_ids]
                    
                    # Подзапрос для получения product_id через прямую связь товаров с option_value
                    from ..models.productOptions import product_option_value_association
                    
                    subquery = db.session.query(product_option_value_association.c.product_id).filter(
                        product_option_value_association.c.option_value_id.in_(value_ids)
                    )
                    
                    products_query = products_query.filter(Product.id.in_(subquery))
        
        # Применяем сортировку
        if sort == 'new':
            products_query = products_query.order_by(Product.created_at.desc())
        elif sort == 'price_asc':
            products_query = products_query.order_by(Product.price.asc())
        elif sort == 'price_desc':
            products_query = products_query.order_by(Product.price.desc())
        else:  # popular (по умолчанию)
            products_query = products_query.order_by(Product.sort_order, Product.id)
        
        # Получаем отфильтрованные товары
        filtered_products = products_query.all()
        
        print(f"Found {len(filtered_products)} products after filtering")
        
        # Загружаем все изображения для отфильтрованных товаров с правильным порядком
        from app.models.product import product_images
        from app.models.image import Image
        
        product_images_data = {}
        for product in filtered_products:
            # Создаем список изображений
            images_list = []
            
            # Добавляем главное изображение в начало
            if product.main_image:
                product.main_image.order = -1
                images_list.append(product.main_image)
            
            # Получаем все дополнительные изображения товара с порядком
            images_with_order = db.session.query(Image, product_images.c.order) \
                .join(product_images, Image.id == product_images.c.image_id) \
                .filter(product_images.c.product_id == product.id) \
                .order_by(product_images.c.order) \
                .all()
            
            # Добавляем дополнительные изображения
            for img, order in images_with_order:
                # Проверяем, что это не главное изображение
                if img.id != product.main_image_id:
                    img.order = order
                    images_list.append(img)
            
            # Добавляем в словарь
            product_images_data[product.id] = images_list
        
        # Отладочная информация
        if len(filtered_products) == 0 and filters:
            print("=== DEBUG FILTERING ===")
            print(f"Total products in category (including subcategories): {Product.query.filter(Product.category_id.in_(all_category_ids)).count()}")
            print(f"Total variations in category (including subcategories): {ProductVariation.query.join(Product).filter(Product.category_id.in_(all_category_ids)).count()}")
            
            for option_id, value_ids in filters.items():
                print(f"Checking option {option_id} with values {value_ids}")
                
                # Проверяем существование опции
                option = ProductOption.query.get(option_id)
                if option:
                    print(f"Option '{option.name}' exists")
                    
                    # Проверяем существование значений
                    values = ProductOptionValue.query.filter(
                        ProductOptionValue.id.in_(value_ids),
                        ProductOptionValue.option_id == option_id
                    ).all()
                    print(f"Found {len(values)} option values: {[v.value for v in values]}")
                    
                    # Проверяем товары с конкретными значениями через product_option_value_association
                    from ..models.productOptions import product_option_value_association
                    
                    # Сначала проверим все связи в таблице
                    all_associations = db.session.query(product_option_value_association).all()
                    print(f"Total associations in table: {len(all_associations)}")
                    print(f"All associations: {[(a.product_id, a.option_value_id) for a in all_associations]}")
                    
                    # Проверим связи для конкретных option_value_id
                    associations_for_values = db.session.query(product_option_value_association).filter(
                        product_option_value_association.c.option_value_id.in_(value_ids)
                    ).all()
                    print(f"Associations for values {value_ids}: {[(a.product_id, a.option_value_id) for a in associations_for_values]}")
                    
                    # Получим все подкатегории текущей категории
                    all_category_ids = get_all_subcategories(category.id)
                    print(f"All category IDs (including subcategories): {all_category_ids}")
                    
                    # Проверим товары в категории и всех подкатегориях
                    category_products = Product.query.filter(Product.category_id.in_(all_category_ids)).all()
                    print(f"Category products (including subcategories): {[(p.id, p.name, p.category.name if p.category else 'No category') for p in category_products]}")
                    
                    products_with_values = db.session.query(Product).join(
                        product_option_value_association, Product.id == product_option_value_association.c.product_id
                    ).filter(
                        product_option_value_association.c.option_value_id.in_(value_ids),
                        Product.category_id.in_(all_category_ids)
                    ).all()
                    print(f"Found {len(products_with_values)} products with selected values in category")
                    
                    # Показываем какие товары найдены
                    if products_with_values:
                        print(f"Products found: {[p.name for p in products_with_values]}")
                    else:
                        print("No products found with these option values")
                else:
                    print(f"Option {option_id} not found")
        
        # Формируем HTML для товаров
        products_html = []
        for product in filtered_products:
            # Получаем опции для товара
            product_options = ProductOption.get_options_by_product_id(product.id)
            print(f"Product {product.id} ({product.name}) has {len(product_options)} options")
            
            # Отладочная информация для опций
            for option in product_options:
                print(f"  Option: {option['name']} (type: {option['display_type']})")
                if option['display_type'] == 'color':
                    print(f"    Colors: {[color['value'] for color in option['values']]}")
            
            # Генерируем HTML для цветовой палитры отдельно
            color_html = ''
            for option in product_options:
                if option['display_type'] == 'color':
                    colors = []
                    for i, color in enumerate(option['values']):
                        color_class = color['value'].lower().replace(' ', '-')
                        active_class = 'active' if i == 0 else ''
                        
                        # Добавляем inline стили для цветов
                        color_style = ''
                        if color['value'] == 'Красный':
                            color_style = 'background-color: #e31e2b;'
                        elif color['value'] == 'Белый':
                            color_style = 'background-color: #ffffff; border: 1px solid #e0e0e0;'
                        elif color['value'] == 'Черный':
                            color_style = 'background-color: #000000;'
                        elif color['value'] == 'Синий':
                            color_style = 'background-color: #007bff;'
                        elif color['value'] == 'Зеленый':
                            color_style = 'background-color: #28a745;'
                        elif color['value'] == 'Желтый':
                            color_style = 'background-color: #ffc107;'
                        elif color['value'] == 'Оранжевый':
                            color_style = 'background-color: #fd7e14;'
                        elif color['value'] == 'Фиолетовый':
                            color_style = 'background-color: #6f42c1;'
                        elif color['value'] == 'Розовый':
                            color_style = 'background-color: #e83e8c;'
                        elif color['value'] == 'Серый':
                            color_style = 'background-color: #6c757d;'
                        else:
                            # Для других цветов используем CSS класс
                            color_style = ''
                        
                        color_html_part = f'''
                        <div class="pallete-color pallete-color-{color_class} {active_class} cursor-pointer position-relative me-3 transition wh-26 rounded-circle"
                             data-pallet="core"
                             data-color-name="{color['value'].capitalize()}"
                             style="{color_style}">
                        </div>
                        '''
                        colors.append(color_html_part)
                    
                    if colors:
                        color_html += f'<div class="top-palletes d-flex">{"".join(colors)}</div>'
            
            # Получаем изображения для товара
            product_images = product_images_data.get(product.id, [])
            
            # Генерируем HTML для изображений
            if len(product_images) > 1:
                # Слайдер с несколькими изображениями
                images_html = f'''
                <div class="product-image-container">
                    <div class="product-image-slider" data-product-id="{product.id}">
                '''
                for i, image in enumerate(product_images):
                    active_class = 'active' if i == 0 else ''
                    images_html += f'''
                        <div class="product-image-slide {active_class}">
                            <img src="/static/uploads/{image.filename}" alt="{product.name}"
                                 class="img-fluid w-100" data-image-index="{i}">
                        </div>
                    '''
                images_html += '''
                    </div>
                </div>
                '''
            else:
                # Одно изображение
                main_image = product.main_image if product.main_image else None
                if main_image:
                    images_html = f'''
                    <div class="product-image-container">
                        <div class="product-image">
                            <img src="/static/uploads/{main_image.filename}" alt="{product.name}"
                                 class="img-fluid w-100">
                        </div>
                    </div>
                    '''
                else:
                    images_html = '''
                    <div class="product-image-container">
                        <div class="product-image">
                            <img src="/static/uploads/placeholder.jpg" alt="No image"
                                 class="img-fluid w-100">
                        </div>
                    </div>
                    '''
            
            # Формируем HTML карточки товара
            product_html = f'''
            <div class="col-6 col-lg-3 mb-4 product-item">
                <span class="fav-btn" data-product-id="{product.id}">
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor"
                         class="bi bi-heart-fill" viewBox="0 0 16 16">
                        <path fill-rule="evenodd"
                              d="M8 1.314C12.438-3.248 23.534 4.735 8 15-7.534 4.736 3.562-3.248 8 1.314"/>
                    </svg>
                </span>
                <a href="/product/{product.slug}" data-product-id="{product.id}" class="product_item">
                    {images_html}
                </a>
                <div class="row py-2">
                    <div class="col-6">
                        <a href="/product/{product.slug}" data-product-id="{product.id}" class="product_item">
                            <h6>{product.name}</h6>
                        </a>
                    </div>
                    <div class="col-6 d-flex justify-content-end">
                        <p class="fs-6">{product.price} р.</p>
                        <button class="cat-catalog-btn add-to-cart-btn" id="add-to-cart"
                                style="border: none; background: transparent">
                            <img src="/static/icons/add-cart.png">
                        </button>
                    </div>
                    <div class="mt-4 color-options">
                        {color_html}
                    </div>
                </div>
            </div>
            '''
            products_html.append(product_html)
        
        return jsonify({
            'success': True,
            'products_count': len(filtered_products),
            'products_html': ''.join(products_html)
        })
        
    except Exception as e:
        print(f"Error in filter_category_products: {e}")
        return jsonify({'error': str(e)}), 500


@main_bp.route('/custom-auth', methods=['GET', 'POST'])
def custom_auth(action=None):
    # Если пользователь уже авторизован, перенаправляем на главную
    if current_user.is_authenticated and isinstance(current_user, Customer):
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        action = request.form.get('action')  # Определяем, вход или регистрация
        next_page = request.form.get('next', url_for('main.index'))

        if action == 'login':
            email = request.form.get('loginEmail')
            password = request.form.get('loginPassword')

            # Проверка входных данных
            if not email or not password:
                flash('Email и пароль обязательны для входа.', 'danger')
                return redirect(url_for('main.index'))

            # Поиск клиента
            customer = Customer.query.filter_by(email=email).first()

            if customer and customer.check_password(password):
                login_user(customer)
                session['auth_type'] = 'customer'
                flash('Вход выполнен успешно!', 'success')
                # Объединяем корзину сессии с корзиной пользователя
                merge_session_cart_to_db()
                return redirect(next_page if is_safe_url(next_page) else url_for('main.index'))
            else:
                flash('Неверный email или пароль.', 'danger')

        elif action == 'register':
            name = request.form.get('registerName')
            email = request.form.get('registerEmail')
            password = request.form.get('registerPassword')
            confirm_password = request.form.get('registerConfirmPassword')

            # Проверка входных данных
            if not all([name, email, password, confirm_password]):
                flash('Все поля обязательны для регистрации.', 'danger')
                return redirect(url_for('main.index'))

            if password != confirm_password:
                flash('Пароли не совпадают.', 'danger')
                return redirect(url_for('main.index'))

            # Проверяем, не существует ли уже пользователь с таким email
            existing_customer = Customer.query.filter_by(email=email).first()
            if existing_customer:
                flash('Пользователь с таким email уже существует.', 'danger')
                return redirect(url_for('main.index'))

            try:
                # Создание клиента через addCustomer
                new_customer = addCustomer(name, email, password)
                login_user(new_customer)
                session['auth_type'] = 'customer'
                flash('Регистрация успешна! Добро пожаловать!', 'success')
                # Объединяем корзину сессии с корзиной пользователя
                merge_session_cart_to_db()
                return redirect(next_page if is_safe_url(next_page) else url_for('main.index'))

            except ValueError as e:
                flash(str(e), 'danger')
            except Exception as e:
                db.session.rollback()
                flash('Ошибка при регистрации. Попробуйте снова.', 'danger')

    return redirect(url_for('main.index'))


@main_bp.route('/logout')
@login_required
def logout():
    session.pop('auth_type', None)
    logout_user()
    flash('Вы вышли из системы.', 'success')
    return redirect('/')


@main_bp.route('/favorites', methods=['GET'])
def favorite():
    """Страница избранного"""
    seo = SEOSettings(
        page_type='favorite',
        page_id=0,
        meta_title='Избранное',
        meta_description='Закладки',
        meta_keywords='',
        slug='favorite'
    )
    categories = getPcats()
    if not (current_user.is_authenticated and isinstance(current_user, Customer)):
        return redirect(url_for('main.custom_auth'))
    
    customer_id = current_user.id
    favorites = getFavorites(customer_id)
    site_settings = getSiteSettings()
    
    # Загружаем все изображения для товаров в избранном с правильным порядком
    from app.models.product import product_images
    from app.models.image import Image
    
    product_images_data = {}
    for fav in favorites:
        product = fav.product
        # Создаем список изображений
        images_list = []
        
        # Добавляем главное изображение в начало
        if product.main_image:
            product.main_image.order = -1  # Главное изображение будет первым
            images_list.append(product.main_image)
        
        # Получаем все дополнительные изображения товара с порядком
        images_with_order = db.session.query(Image, product_images.c.order) \
            .join(product_images, Image.id == product_images.c.image_id) \
            .filter(product_images.c.product_id == product.id) \
            .order_by(product_images.c.order) \
            .all()
        
        # Добавляем дополнительные изображения
        for img, order in images_with_order:
            # Проверяем, что это не главное изображение
            if img.id != product.main_image_id:
                img.order = order  # Добавляем order как динамический атрибут
                images_list.append(img)
        
        # Добавляем в словарь
        product_images_data[product.id] = images_list
    
    return render_template('front/favorite.html', favorites=favorites, seo=seo, site_settings=site_settings,
                       auth=current_user.is_authenticated, categories=categories, product_images_data=product_images_data)


@main_bp.route('/favorites/toggle', methods=['POST'])
@csrf.exempt
def toggle_favorite():
    """Добавление/удаление из избранного"""
    if not (current_user.is_authenticated and isinstance(current_user, Customer)):
        return jsonify({'error': 'Необходима авторизация'}), 401
    
    product_id = request.form.get('product_id', type=int)
    if not product_id:
        return jsonify({'error': 'Неверный ID товара'}), 400
    
    # Проверяем, существует ли товар
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'error': 'Товар не найден'}), 404
    
    # Проверяем, есть ли уже в избранном
    is_favorite = checkFavorite(current_user.id, product_id)
    
    if is_favorite:
        deleteFavorite(current_user.id, product_id)
        return jsonify({'message': 'Товар удален из избранного', 'is_favorite': False})
    else:
        addFavorite(current_user.id, product_id)
        return jsonify({'message': 'Товар добавлен в избранное', 'is_favorite': True})


@main_bp.route('/favorites/list', methods=['GET'])
def get_favorites_list():
    """Получение списка избранных товаров пользователя"""
    if not (current_user.is_authenticated and isinstance(current_user, Customer)):
        return jsonify({'favorites': []})
    
    favorites = getFavorites(current_user.id)
    favorite_ids = [fav.product_id for fav in favorites]
    return jsonify({'favorites': favorite_ids})


def is_safe_url(target):
    """Проверяет, что URL безопасен для редиректа."""
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


def get_session_id():
    """Возвращает или создаёт уникальный ID сессии."""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return session['session_id']


@main_bp.before_app_request
def enforce_customer_scope_on_front():
    """На фронте считаем пользователя авторизованным, только если это Customer.
    Админ, вошедший в админку, не должен подхватываться как покупатель."""
    # Применяем только к фронтовым блюпринтам main (не к admin и auth)
    if request.blueprint == 'main':
        if current_user.is_authenticated and current_user.__class__.__name__ == 'User':
            # Логически считаем такого пользователя неавторизованным на фронте
            # Ничего не разлогиниваем, просто не даём фронту видеть авторизацию
            request.view_args = request.view_args or {}


def merge_session_cart_to_db():
    """Переносит корзину из сессии в базу данных для авторизованного пользователя."""
    if not current_user.is_authenticated or 'cart' not in session:
        return

    cart = session.get('cart', {})
    for cart_key, cart_data in cart.items():
        if isinstance(cart_data, dict):
            product_id = cart_data.get('product_id')
            quantity = cart_data.get('quantity', 1)
            selected_options = cart_data.get('selected_options', {})
            
        product = Product.query.get(product_id)
        if product and product.stock >= quantity:
                # Ищем существующий товар с такими же опциями
                existing_cart_item = None
                for cart_item in CartItem.query.filter_by(customer_id=current_user.id, product_id=product_id).all():
                    if cart_item.get_selected_options() == selected_options:
                        existing_cart_item = cart_item
                        break
                
                if existing_cart_item:
                    existing_cart_item.quantity += quantity
                else:
                    cart_item = CartItem(
                        customer_id=current_user.id,
                        product_id=product_id,
                        quantity=quantity
                    )
                    cart_item.set_selected_options(selected_options)
                db.session.add(cart_item)
    
    db.session.commit()
    session.pop('cart', None)  # Очищаем корзину в сессии


@main_bp.route('/cart/add', methods=['POST'])
@csrf.exempt
def add_to_cart():
    product_id = request.form.get('product_id', type=int)
    quantity = request.form.get('quantity', type=int, default=1)
    selected_options_json = request.form.get('selected_options', '{}')
    
    print(f"Добавление в корзину: product_id={product_id}, quantity={quantity}, options={selected_options_json}")
    
    if not product_id or quantity < 1:
        flash('Неверный товар или количество.', 'danger')
        return redirect(request.referrer or url_for('main.index'))

    product = Product.query.get(product_id)
    if not product:
        flash('Товар не найден.', 'danger')
        return redirect(request.referrer or url_for('main.index'))

    # Парсим выбранные опции
    print(f"ADD TO CART - Raw selected_options_json: {selected_options_json}")
    print(f"ADD TO CART - selected_options_json type: {type(selected_options_json)}")
    
    try:
        selected_options = json.loads(selected_options_json) if selected_options_json else {}
        print(f"ADD TO CART - Parsed selected_options: {selected_options}")
        print(f"ADD TO CART - selected_options type: {type(selected_options)}")
    except Exception as e:
        print(f"ADD TO CART - Error parsing selected_options: {e}")
        selected_options = {}

    if current_user.is_authenticated and isinstance(current_user, Customer):
        # Для авторизованных пользователей - просто добавляем новый товар
        cart_item = CartItem(
            customer_id=current_user.id, 
            product_id=product_id, 
            quantity=quantity
        )
        cart_item.set_selected_options(selected_options)
        db.session.add(cart_item)
        db.session.commit()
        print(f"ADD TO CART - Added new cart item for authenticated user")
    else:
        # Для неавторизованных пользователей
        cart = session.get('cart', {})
        print(f"ADD TO CART - Current session cart: {cart}")
        
        # Создаем простой уникальный ключ
        cart_key = f"{product_id}_{len(cart)}"
        cart[cart_key] = {
            'product_id': product_id,
            'quantity': quantity,
            'selected_options': selected_options
        }
        session['cart'] = cart
        session.modified = True
        print(f"ADD TO CART - Added new cart item for unauthenticated user with key: {cart_key}")
        print(f"ADD TO CART - Cart item data: {cart[cart_key]}")
        print(f"ADD TO CART - Updated session cart: {session.get('cart', {})}")

    flash('Товар добавлен в корзину!', 'success')
    return 'Товар добавлен в корзину'


@main_bp.route('/cart/remove', methods=['POST'])
@csrf.exempt
def remove_from_cart():
    cart_item_id = request.form.get('cart_item_id', type=int)
    cart_key = request.form.get('cart_key')
    product_id = request.form.get('product_id', type=int)
    selected_options_json = request.form.get('selected_options', '{}')

    print(f"REMOVE FROM CART: cart_item_id={cart_item_id}, cart_key={cart_key}, product_id={product_id}, options_json={selected_options_json}")

    if current_user.is_authenticated and isinstance(current_user, Customer):
        # Для авторизованных пользователей - удаляем по ID товара в корзине
        if cart_item_id:
            cart_item = CartItem.query.get(cart_item_id)
            if cart_item and cart_item.customer_id == current_user.id:
                db.session.delete(cart_item)
                db.session.commit()
                print(f"REMOVE FROM CART - Deleted cart item {cart_item_id}")
            else:
                print("REMOVE FROM CART - Cart item not found or not owned by user")
                flash('Товар не найден в корзине.', 'warning')
                return redirect(request.referrer or url_for('main.index'))
        else:
            flash('Неверный товар.', 'danger')
            return redirect(request.referrer or url_for('main.index'))
    else:
        # Для неавторизованных пользователей
        cart = session.get('cart', {})
        print(f"REMOVE FROM CART - Session cart: {cart}")
        
        # Если передан cart_key, удаляем по нему
        if cart_key and cart_key in cart:
            cart.pop(cart_key, None)
            session['cart'] = cart
            session.modified = True
            print(f"REMOVE FROM CART - Removed by cart_key: {cart_key}")
            flash('Товар удален из корзины!', 'success')
            return redirect(url_for('main.view_cart'))
        
        # Иначе ищем по product_id и selected_options (старый способ)
        if not product_id:
            flash('Неверный товар.', 'danger')
            return redirect(request.referrer or url_for('main.index'))

        # Парсим выбранные опции
        try:
            selected_options = json.loads(selected_options_json) if selected_options_json else {}
        except Exception as e:
            print(f"REMOVE FROM CART - Error parsing selected_options: {e}")
            selected_options = {}

        print(f"REMOVE FROM CART - Looking for product_id: {product_id}, selected_options: {selected_options}")
        print(f"REMOVE FROM CART - selected_options type: {type(selected_options)}")
        
        # Ищем товар с такими же опциями
        item_found = False
        for cart_key, cart_data in cart.items():
            if isinstance(cart_data, dict):
                print(f"REMOVE FROM CART - Checking cart_key: {cart_key}, cart_data: {cart_data}")
                cart_product_id = cart_data.get('product_id')
                cart_selected_options = cart_data.get('selected_options', {})
                
                print(f"REMOVE FROM CART - Comparing: cart_product_id={cart_product_id} vs {product_id}")
                print(f"REMOVE FROM CART - Comparing: cart_selected_options={cart_selected_options} vs {selected_options}")
                print(f"REMOVE FROM CART - cart_selected_options type: {type(cart_selected_options)}")
                
                # Конвертируем ключи в int для сравнения
                normalized_cart_options = {}
                for k, v in cart_selected_options.items():
                    try:
                        normalized_cart_options[int(k)] = int(v)
                    except (ValueError, TypeError):
                        normalized_cart_options[k] = v
                
                normalized_selected_options = {}
                for k, v in selected_options.items():
                    try:
                        normalized_selected_options[int(k)] = int(v)
                    except (ValueError, TypeError):
                        normalized_selected_options[k] = v
                
                print(f"REMOVE FROM CART - Normalized comparison:")
                print(f"  cart: {normalized_cart_options}")
                print(f"  selected: {normalized_selected_options}")
                
                if (cart_product_id == product_id and normalized_cart_options == normalized_selected_options):
                    cart.pop(cart_key, None)
                    session['cart'] = cart
                    session.modified = True
                    item_found = True
                    print(f"REMOVE FROM CART - Removed cart_key: {cart_key}")
                    break
        
        if not item_found:
            print("REMOVE FROM CART - Item not found in session cart!")
            flash('Товар не найден в корзине.', 'warning')
            return redirect(request.referrer or url_for('main.index'))

    flash('Товар удален из корзины!', 'success')
    return redirect(url_for('main.view_cart'))


@main_bp.route('/cart', methods=['GET'])
def view_cart():
    cart_items = []
    total_price = Decimal('0')

    if current_user.is_authenticated and isinstance(current_user, Customer):
        cart_items = CartItem.query.filter_by(customer_id=current_user.id).all()
        processed_cart_items = []
        
        for item in cart_items:
            # Получаем цену с учетом вариаций
            selected_options = item.get_selected_options()
            item_price = item.product.price
            
            if selected_options:
                # Находим подходящую вариацию
                print(f"Looking for variations for product {item.product_id} with options {selected_options}")
                variations = ProductVariation.get_variations_by_product_id(item.product_id)
                print(f"Found variations: {variations}")
                matching_variation = None
                for var_id, variation in variations.items():
                    print(f"Checking variation {var_id}: {variation.get('option_value_ids')} vs {list(selected_options.values())}")
                    # Сравниваем списки значений опций
                    variation_values = variation.get('option_value_ids', [])
                    selected_values = list(selected_options.values())
                    
                    # Проверяем, что все выбранные значения есть в вариации
                    if set(selected_values) == set(variation_values):
                        matching_variation = variation
                        print(f"Found matching variation: {variation}")
                        break
                
                if matching_variation:
                    # Конвертируем float в Decimal
                    item_price = Decimal(str(matching_variation['price']))
                    total_price += item_price * item.quantity
                    print(f"Using variation price: {item_price}")
                else:
                    total_price += item.product.price * item.quantity
                    print(f"Using base product price: {item.product.price}")
            else:
                total_price += item.product.price * item.quantity
                print(f"No options, using base product price: {item.product.price}")
            
            # Создаем словарь для шаблона
            processed_cart_items.append({
                'product': item.product,
                'quantity': item.quantity,
                'selected_options': selected_options,
                'price': item_price,
                'cart_item_id': item.id  # Добавляем ID товара в корзине
            })
        
        cart_items = processed_cart_items
    else:
        cart = session.get('cart', {})
        for cart_key, cart_data in cart.items():
            if isinstance(cart_data, dict):
                product = Product.query.get(cart_data['product_id'])
                quantity = cart_data['quantity']
                selected_options = cart_data.get('selected_options', {})
            else:
                # Старый формат для обратной совместимости
                product = Product.query.get(int(cart_key))
                quantity = cart_data
                selected_options = {}
            
            if product:
                # Получаем цену с учетом вариаций
                item_price = product.price
                if selected_options:
                    variations = ProductVariation.get_variations_by_product_id(product.id)
                    matching_variation = None
                    for var_id, variation in variations.items():
                        # Сравниваем списки значений опций
                        variation_values = variation.get('option_value_ids', [])
                        selected_values = list(selected_options.values())
                        
                        # Проверяем, что все выбранные значения есть в вариации
                        if set(selected_values) == set(variation_values):
                            matching_variation = variation
                            break
                    
                    if matching_variation:
                        # Конвертируем float в Decimal
                        item_price = Decimal(str(matching_variation['price']))
                        total_price += item_price * quantity
                    else:
                        total_price += product.price * quantity
                else:
                    total_price += product.price * quantity
                
                cart_items.append({
                    'product': product, 
                    'quantity': quantity,
                    'selected_options': selected_options,
                    'price': item_price,
                    'cart_key': cart_key  # Добавляем ключ сессии для удаления
                })

    # Создаем карты для быстрого доступа к опциям и их значениям
    options_map = {}
    option_values_map = {}
    
    # Получаем все уникальные option_id и value_id из корзины
    all_option_ids = set()
    all_value_ids = set()
    
    print("=== DEBUG CART ITEMS FOR OPTIONS ===")
    for item in cart_items:
        if isinstance(item, dict):
            selected_options = item.get('selected_options', {})
            print(f"Dict item - selected_options: {selected_options}")
        else:
            selected_options = item.get_selected_options()
            print(f"Object item - selected_options: {selected_options}")
        
        print(f"Item type: {type(item)}")
        print(f"Selected options keys: {list(selected_options.keys())}")
        print(f"Selected options values: {list(selected_options.values())}")
        
        # Конвертируем ключи в int, если они строки
        for key in selected_options.keys():
            try:
                all_option_ids.add(int(key))
            except (ValueError, TypeError):
                all_option_ids.add(key)
        
        for value in selected_options.values():
            try:
                all_value_ids.add(int(value))
            except (ValueError, TypeError):
                all_value_ids.add(value)
    
    print(f"Final all_option_ids: {all_option_ids}")
    print(f"Final all_value_ids: {all_value_ids}")
    
    # Загружаем опции и их значения
    if all_option_ids:
        print(f"Loading options for IDs: {all_option_ids}")
        options = ProductOption.query.filter(ProductOption.id.in_(all_option_ids)).all()
        options_map = {option.id: option for option in options}
        print(f"Loaded options: {[f'{opt.id}:{opt.name}' for opt in options]}")
        print(f"Options map keys: {list(options_map.keys())}")
        
        if all_value_ids:
            print(f"Loading option values for IDs: {all_value_ids}")
            option_values = ProductOptionValue.query.filter(ProductOptionValue.id.in_(all_value_ids)).all()
            option_values_map = {value.id: value for value in option_values}
            print(f"Loaded option values: {[f'{val.id}:{val.value}' for val in option_values]}")
            print(f"Option values map keys: {list(option_values_map.keys())}")
        else:
            print("No value IDs found!")
    else:
        print("No option IDs found!")

    seo = SEOSettings(
        page_type='cart',
        page_id=0,
        meta_title='Корзина',
        meta_description='Корзина покупок',
        meta_keywords='',
        slug='cart'
    )
    categories = getPcats()
    site_settings = getSiteSettings()
    return render_template('front/cart.html', 
                           cart_items=cart_items, 
                           total_price=total_price, 
                           options_map=options_map,
                           option_values_map=option_values_map,
                           seo=seo,
                           site_settings=site_settings,
                           auth=current_user.is_authenticated, 
                           categories=categories)


def _compute_cart_items_for_customer(customer_id):
    """Возвращает (processed_cart_items, total_price) для авторизованного пользователя.

    processed_cart_items: список словарей вида
      { 'product': Product, 'quantity': int, 'selected_options': dict, 'price': Decimal }
    """
    cart_items = CartItem.query.filter_by(customer_id=customer_id).all()
    processed_cart_items = []
    total_price = Decimal('0')

    for item in cart_items:
        selected_options = item.get_selected_options()
        item_price = item.product.price

        if selected_options:
            variations = ProductVariation.get_variations_by_product_id(item.product_id)
            matching_variation = None
            for var_id, variation in variations.items():
                variation_values = variation.get('option_value_ids', [])
                selected_values = list(selected_options.values())
                if set(selected_values) == set(variation_values):
                    matching_variation = variation
                    break
            if matching_variation:
                item_price = Decimal(str(matching_variation['price']))
        total_price += item_price * item.quantity

        processed_cart_items.append({
            'product': item.product,
            'quantity': item.quantity,
            'selected_options': selected_options,
            'price': item_price,
            'cart_item_id': item.id
        })

    return processed_cart_items, total_price


def _compute_cart_items_for_session():
    """Возвращает (processed_cart_items, total_price) для корзины гостя из session."""
    cart = session.get('cart', {})
    processed_cart_items = []
    total_price = Decimal('0')

    for cart_key, cart_data in cart.items():
        if not isinstance(cart_data, dict):
            continue
        product = Product.query.get(cart_data.get('product_id'))
        if not product:
            continue
        quantity = int(cart_data.get('quantity', 1))
        selected_options = cart_data.get('selected_options', {})

        item_price = product.price
        if selected_options:
            variations = ProductVariation.get_variations_by_product_id(product.id)
            matching_variation = None
            for var_id, variation in variations.items():
                variation_values = variation.get('option_value_ids', [])
                selected_values = list(selected_options.values())
                if set(selected_values) == set(variation_values):
                    matching_variation = variation
                    break
            if matching_variation:
                item_price = Decimal(str(matching_variation['price']))

        total_price += item_price * quantity
        processed_cart_items.append({
            'product': product,
            'quantity': quantity,
            'selected_options': selected_options,
            'price': item_price,
            'cart_key': cart_key
        })

    return processed_cart_items, total_price


def _resolve_variation_id(product_id, selected_options_dict):
    """Возвращает ID вариации по выбранным значениям опций или None, если не найдено."""
    if not selected_options_dict:
        return None
    variations = ProductVariation.get_variations_by_product_id(product_id)
    selected_values = list(selected_options_dict.values())
    for var_id, variation in variations.items():
        variation_values = variation.get('option_value_ids', [])
        if set(selected_values) == set(variation_values):
            return var_id
    return None
@main_bp.route('/checkout', methods=['GET', 'POST'])
def checkout():
    """Страница оформления заказа: доступна гостям и авторизованным."""
    # Готовим корзину
    if current_user.is_authenticated and isinstance(current_user, Customer):
        processed_cart_items, subtotal = _compute_cart_items_for_customer(current_user.id)
    else:
        processed_cart_items, subtotal = _compute_cart_items_for_session()
    if not processed_cart_items:
        flash('Корзина пуста.', 'warning')
        return redirect(url_for('main.view_cart'))

    # Доставка (пока опционально, если методы есть)
    shipping_methods = ShippingMethod.query.order_by(ShippingMethod.id.asc()).all()
    selected_shipping_id = None
    shipping_cost = Decimal('0')

    # Налоги: для авторизованных пробуем по региону, для гостей 0
    tax_amount = Decimal('0')
    if current_user.is_authenticated and isinstance(current_user, Customer):
        try:
            if getattr(current_user, 'region', None) and current_user.region.settings and current_user.region.settings.tax_rate:
                rate = Decimal(str(current_user.region.settings.tax_rate.rate))
                tax_amount = (subtotal * rate) / Decimal('100')
        except Exception:
            tax_amount = Decimal('0')

    # Предзаполнение данных доставки/оплаты для авторизованного клиента
    addresses = []
    selected_address = None
    shipping_prefill = {
        'full_name': '',
        'phone': '',
        'address_line1': '',
        'address_line2': '',
        'city': '',
        'postcode': '',
        'country': ''
    }
    default_payment_method = 'cod'
    if current_user.is_authenticated and isinstance(current_user, Customer):
        try:
            addresses = CustomerAddress.query.filter_by(customer_id=current_user.id).order_by(CustomerAddress.is_default_shipping.desc(), CustomerAddress.id.desc()).all()
            selected_address = current_user.default_shipping_address or (addresses[0] if addresses else None)
        except Exception:
            addresses = []
            selected_address = None

        shipping_prefill['full_name'] = current_user.name or ''
        shipping_prefill['phone'] = current_user.phone or ''
        if selected_address is not None:
            shipping_prefill.update({
                'full_name': selected_address.full_name or shipping_prefill['full_name'],
                'phone': selected_address.phone or shipping_prefill['phone'],
                'address_line1': selected_address.address_line1 or '',
                'address_line2': selected_address.address_line2 or '',
                'city': selected_address.city or '',
                'postcode': selected_address.postcode or '',
                'country': selected_address.country or ''
            })
        default_payment_method = current_user.default_payment_method or 'cod'

    if request.method == 'POST':
        # Получаем выбранный метод доставки
        selected_shipping_id = request.form.get('shipping_method_id', type=int)
        if selected_shipping_id:
            method = ShippingMethod.query.get(selected_shipping_id)
            if method:
                shipping_cost = Decimal(str(method.cost))
                # Сохраним в форме имя метода
                request.form = request.form.copy()
                request.form = request.form.to_dict()
                request.form['shipping_method_name'] = method.method_name

        # Пересчитываем на случай выбора доставки
        total_price = subtotal + shipping_cost + tax_amount

        try:
            # Определяем customer_id: авторизованный или гость
            if current_user.is_authenticated and isinstance(current_user, Customer):
                customer_id = current_user.id
                guest_name = None
                # Если выбрали сохраненный адрес — применим его поля как дефолтные
                sel_addr_id = request.form.get('selected_address_id', type=int)
                selected_addr_obj = None
                if sel_addr_id:
                    selected_addr_obj = CustomerAddress.query.filter_by(id=sel_addr_id, customer_id=current_user.id).first()
            else:
                # Для гостя: email не обязателен, генерируем placeholder при необходимости
                guest_name = (request.form.get('shipping_full_name') or request.form.get('guest_name') or 'Гость').strip()
                guest_email = (request.form.get('guest_email') or '').strip()

                if guest_email:
                    existing_customer = Customer.query.filter_by(email=guest_email).first()
                    if existing_customer:
                        customer_id = existing_customer.id
                    else:
                        rnd_password = uuid.uuid4().hex[:12]
                        new_customer = addCustomer(guest_name, guest_email, rnd_password)
                        customer_id = new_customer.id
                else:
                    # Без email: создаем временный email для соблюдения ограничений БД
                    temp_email = f"guest-{uuid.uuid4().hex}@example.local"
                    rnd_password = uuid.uuid4().hex[:12]
                    new_customer = addCustomer(guest_name, temp_email, rnd_password)
                    customer_id = new_customer.id

            # Создаем заказ
            order = Order(
                customer_id=customer_id,
                status='new',
                total_price=total_price,
                tax_amount=tax_amount,
                shipping_cost=shipping_cost,
                shipping_method_id=(method.id if selected_shipping_id and method else None),
                shipping_method_name=(request.form.get('shipping_method_name') or (method.method_name if selected_shipping_id and method else None)),
                shipping_full_name=(
                    request.form.get('shipping_full_name')
                    or (selected_addr_obj.full_name if current_user.is_authenticated and isinstance(current_user, Customer) and 'selected_addr_obj' in locals() and selected_addr_obj else None)
                    or (guest_name if not (current_user.is_authenticated and isinstance(current_user, Customer)) else current_user.name)
                ),
                shipping_phone=(
                    request.form.get('shipping_phone')
                    or (selected_addr_obj.phone if current_user.is_authenticated and isinstance(current_user, Customer) and 'selected_addr_obj' in locals() and selected_addr_obj else (current_user.phone if current_user.is_authenticated and isinstance(current_user, Customer) else None))
                ),
                shipping_address_line1=(
                    request.form.get('shipping_address_line1')
                    or (selected_addr_obj.address_line1 if current_user.is_authenticated and isinstance(current_user, Customer) and 'selected_addr_obj' in locals() and selected_addr_obj else None)
                ),
                shipping_address_line2=(
                    request.form.get('shipping_address_line2')
                    or (selected_addr_obj.address_line2 if current_user.is_authenticated and isinstance(current_user, Customer) and 'selected_addr_obj' in locals() and selected_addr_obj else None)
                ),
                shipping_city=(
                    request.form.get('shipping_city')
                    or (selected_addr_obj.city if current_user.is_authenticated and isinstance(current_user, Customer) and 'selected_addr_obj' in locals() and selected_addr_obj else None)
                ),
                shipping_postcode=(
                    request.form.get('shipping_postcode')
                    or (selected_addr_obj.postcode if current_user.is_authenticated and isinstance(current_user, Customer) and 'selected_addr_obj' in locals() and selected_addr_obj else None)
                ),
                shipping_country=(
                    request.form.get('shipping_country')
                    or (selected_addr_obj.country if current_user.is_authenticated and isinstance(current_user, Customer) and 'selected_addr_obj' in locals() and selected_addr_obj else None)
                ),
                payment_method=(request.form.get('payment_method') or 'cod'),
                payment_status='pending',
                customer_comment=request.form.get('customer_comment')
            )
            db.session.add(order)
            db.session.flush()  # получаем order.id

            # Создаем позиции заказа
            for item in processed_cart_items:
                db.session.add(OrderItem(
                    order_id=order.id,
                    product_id=item['product'].id,
                    quantity=item['quantity'],
                    price=item['price'],
                    variation_id=_resolve_variation_id(item['product'].id, item['selected_options']),
                    selected_options=json.dumps(item['selected_options']) if item['selected_options'] else None
                ))

            # Очищаем корзину
            if current_user.is_authenticated and isinstance(current_user, Customer):
                CartItem.query.filter_by(customer_id=current_user.id).delete()
            else:
                session.pop('cart', None)
                session.modified = True

            db.session.commit()
            session['last_order_id'] = order.id
            return redirect(url_for('main.order_success', order_id=order.id))
        except Exception as e:
            db.session.rollback()
            flash('Ошибка при создании заказа. Попробуйте снова.', 'danger')
            print(f"CHECKOUT ERROR: {e}")

    # GET или неуспешный POST
    seo = SEOSettings(
        page_type='checkout',
        page_id=0,
        meta_title='Оформление заказа',
        meta_description='Оформление заказа',
        meta_keywords='',
        slug='checkout'
    )
    categories = getPcats()
    site_settings = getSiteSettings()

    total_price_preview = subtotal + shipping_cost + tax_amount

    return render_template(
        'front/checkout.html',
        cart_items=processed_cart_items,
        subtotal=subtotal,
        tax_amount=tax_amount,
        shipping_cost=shipping_cost,
        total_price=total_price_preview,
        shipping_methods=shipping_methods,
        selected_shipping_id=selected_shipping_id,
        addresses=addresses,
        selected_address_id=(selected_address.id if selected_address is not None else None),
        shipping_prefill=shipping_prefill,
        default_payment_method=default_payment_method,
        seo=seo,
                           site_settings=site_settings,
        auth=current_user.is_authenticated,
        categories=categories
    )


@main_bp.route('/order/success/<int:order_id>')
def order_success(order_id):
    order = Order.query.get_or_404(order_id)
    # Авторизованный клиент видит только свой заказ; гость — только последний заказ из сессии
    if current_user.is_authenticated and isinstance(current_user, Customer):
        if order.customer_id != current_user.id:
            flash('Доступ запрещен.', 'danger')
            return redirect(url_for('main.index'))
    else:
        if session.get('last_order_id') != order_id:
            flash('Доступ запрещен.', 'danger')
            return redirect(url_for('main.index'))

    categories = getPcats()
    site_settings = getSiteSettings()
    seo = SEOSettings(
        page_type='order_success',
        page_id=order.id,
        meta_title=f'Заказ #{order.id} оформлен',
        meta_description='Подтверждение заказа',
        meta_keywords='',
        slug=f'order-{order.id}-success'
    )
    return render_template('front/order_success.html', order=order, seo=seo, site_settings=site_settings,
                           auth=current_user.is_authenticated, categories=categories)


@main_bp.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    if not isinstance(current_user, Customer):
        return redirect(url_for('main.index'))

    # Обновление профиля
    if request.method == 'POST' and request.form.get('action') == 'update_profile':
        current_user.name = request.form.get('name', current_user.name)
        current_user.phone = request.form.get('phone')
        current_user.default_payment_method = request.form.get('default_payment_method')
        try:
            db.session.commit()
            flash('Профиль обновлён', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка сохранения профиля: {e}', 'danger')
        return redirect(url_for('main.account'))

    # Данные для отображения
    active_section = request.args.get('section', 'overview')
    addresses = CustomerAddress.query.filter_by(customer_id=current_user.id).order_by(CustomerAddress.id.desc()).all()
    orders = Order.query.filter_by(customer_id=current_user.id).order_by(Order.created_at.desc()).all()

    categories = getPcats()
    seo = SEOSettings('page', 0, 'Личный кабинет', '', '')
    site_settings = getSiteSettings()
    return render_template('front/account.html',
                           seo=seo,
                           site_settings=site_settings,
                           categories=categories,
                           auth=True,
                           customer=current_user,
                           addresses=addresses,
                           orders=orders,
                           active_section=active_section)


@main_bp.route('/account/password', methods=['POST'])
@login_required
def account_password():
    if not isinstance(current_user, Customer):
        return redirect(url_for('main.index'))
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    if not all([current_password, new_password, confirm_password]):
        flash('Заполните все поля пароля', 'danger')
        return redirect(url_for('main.account'))
    if not current_user.check_password(current_password):
        flash('Неверный текущий пароль', 'danger')
        return redirect(url_for('main.account'))
    if new_password != confirm_password:
        flash('Пароли не совпадают', 'danger')
        return redirect(url_for('main.account'))
    try:
        current_user.password = hash_password(new_password)
        db.session.commit()
        flash('Пароль обновлён', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка обновления пароля: {e}', 'danger')
    return redirect(url_for('main.account'))


@main_bp.route('/account/address/add', methods=['POST'])
@login_required
def account_address_add():
    if not isinstance(current_user, Customer):
        return redirect(url_for('main.index'))
    addr = CustomerAddress(
        customer_id=current_user.id,
        full_name=request.form.get('full_name') or current_user.name,
        phone=request.form.get('phone') or current_user.phone,
        address_line1=request.form.get('address_line1'),
        address_line2=request.form.get('address_line2'),
        city=request.form.get('city'),
        postcode=request.form.get('postcode'),
        country=request.form.get('country') or 'Россия',
        is_default_shipping=bool(request.form.get('is_default_shipping')),
        is_default_billing=False,
    )
    if addr.is_default_shipping:
        # Сбрасываем предыдущие
        CustomerAddress.query.filter_by(customer_id=current_user.id, is_default_shipping=True).update({CustomerAddress.is_default_shipping: False})
        current_user.default_shipping_address_id = None
    try:
        db.session.add(addr)
        db.session.flush()
        if addr.is_default_shipping:
            current_user.default_shipping_address_id = addr.id
        db.session.commit()
        flash('Адрес добавлен', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка добавления адреса: {e}', 'danger')
    return redirect(url_for('main.account'))


@main_bp.route('/account/address/<int:addr_id>/default', methods=['POST'])
@login_required
def account_address_default(addr_id):
    if not isinstance(current_user, Customer):
        return redirect(url_for('main.index'))
    addr = CustomerAddress.query.get_or_404(addr_id)
    if addr.customer_id != current_user.id:
        flash('Нет доступа', 'danger')
        return redirect(url_for('main.account'))
    try:
        CustomerAddress.query.filter_by(customer_id=current_user.id, is_default_shipping=True).update({CustomerAddress.is_default_shipping: False})
        addr.is_default_shipping = True
        current_user.default_shipping_address_id = addr.id
        db.session.commit()
        flash('Адрес по умолчанию обновлён', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка: {e}', 'danger')
    return redirect(url_for('main.account'))


@main_bp.route('/account/address/<int:addr_id>/delete', methods=['POST'])
@login_required
def account_address_delete(addr_id):
    if not isinstance(current_user, Customer):
        return redirect(url_for('main.index'))
    addr = CustomerAddress.query.get_or_404(addr_id)
    if addr.customer_id != current_user.id:
        flash('Нет доступа', 'danger')
        return redirect(url_for('main.account'))
    try:
        if current_user.default_shipping_address_id == addr.id:
            current_user.default_shipping_address_id = None
        db.session.delete(addr)
        db.session.commit()
        flash('Адрес удалён', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка: {e}', 'danger')
    return redirect(url_for('main.account'))


@main_bp.route('/account/orders/<int:order_id>/details', methods=['GET'])
@login_required
def account_order_details(order_id: int):
    """Возвращает детали заказа текущего пользователя для модального окна в ЛК."""
    if not isinstance(current_user, Customer):
        return jsonify(success=False, message='Not allowed'), 403

    order = Order.query.filter_by(id=order_id, customer_id=current_user.id).first()
    if not order:
        return jsonify(success=False, message='Заказ не найден'), 404

    items = []
    order_items = OrderItem.query.filter_by(order_id=order.id).all()
    for it in order_items:
        selected_options_pretty = []
        try:
            sel = getattr(it, 'selected_options', None)
            if sel:
                if isinstance(sel, dict):
                    for name, value in sel.items():
                        selected_options_pretty.append({'name': str(name), 'value': str(value)})
                elif isinstance(sel, list):
                    for opt in sel:
                        if isinstance(opt, dict) and 'name' in opt and 'value' in opt:
                            selected_options_pretty.append({'name': str(opt['name']), 'value': str(opt['value'])})
        except Exception:
            selected_options_pretty = []

        subtotal = (it.price or 0) * (it.quantity or 1)
        items.append({
            'product_id': it.product_id,
            'product_name': getattr(it, 'product_name', None) or (it.product.name if getattr(it, 'product', None) else None),
            'quantity': it.quantity or 0,
            'price': float(it.price or 0),
            'subtotal': float(subtotal or 0),
            'selected_options': getattr(it, 'selected_options', None),
            'selected_options_pretty': selected_options_pretty,
        })

    shipping = {
        'full_name': order.shipping_full_name,
        'phone': getattr(order, 'shipping_phone', None),
        'address_line1': getattr(order, 'shipping_address_line1', None),
        'address_line2': getattr(order, 'shipping_address_line2', None),
        'city': getattr(order, 'shipping_city', None),
        'postcode': getattr(order, 'shipping_postcode', None),
        'country': getattr(order, 'shipping_country', None),
        'method_name': order.shipping_method_name,
    }

    data = {
        'id': order.id,
        'status': order.status,
        'total_price': float(order.total_price or 0),
        'tax_amount': float(order.tax_amount or 0),
        'shipping_cost': float(order.shipping_cost or 0),
        'created_at': order.created_at.isoformat() if order.created_at else None,
        'payment_method': getattr(order, 'payment_method', None),
        'payment_status': getattr(order, 'payment_status', None),
        'payment_reference': getattr(order, 'payment_reference', None),
        'shipping': shipping,
        'items': items,
    }

    return jsonify(success=True, order=data)
