# app/admin/views.py
import os
import re
import uuid
import unicodedata
from datetime import datetime
from functools import wraps
from unidecode import unidecode
from flask import Blueprint, current_app, flash, request, redirect, url_for, session, render_template, abort, jsonify
import json
from ..extensions import csrf
from sqlalchemy.dialects.postgresql import array
from sqlalchemy.exc import IntegrityError
from flask_login import current_user, login_required  # Импорт current_user
from ..models.attributeValue import AttributeValue
from ..models.product import Product, product_images
from ..extensions import db
from ..models.category import Category, build_category_list
from ..models.directory import Directory
from ..models.image import Image
from ..models.seo_settings import SEOSettings
from ..models.order import Order  # для главной страницы статистики
from ..models.order import OrderItem, OrderComment
from ..models.productOptions import ProductOption, ProductOptionValue
from ..models.size_chart import SizeChart, ProductSizeChart
from ..models.review import Review
from ..models.customer import Customer
from ..models.productAttribute import ProductAttribute
from ..models.attribute import Attribute
from .forms import CategoryForm, DirectoryForm, ImageUploadForm, ImageEditForm, ProductForm, AttributeForm, \
    ExistingOptionForm, SiteSettingsForm
from .decorators import admin_required
from .utils import save_image_file
from .utils import *
from ..models.productOptions import *
from ..models.site_setings import SiteSettings, SocialLink
from ..models.page import Page
from . import admin_bp
from ..models.size_chart import SizeChart, ProductSizeChart



def slugify(value):
    value = unicodedata.normalize('NFKD', value)
    value = value.encode('ascii', 'ignore').decode('ascii')  # убрать не-ASCII символы
    value = re.sub(r'[^a-zA-Z0-9]+', '-', value.lower())
    value = value.strip('-')
    return value





@admin_bp.route('/')
@admin_required
def admin_index():
    print("вход")
    last_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    traffic_info = {
        'today_visits': 120,
        'yesterday_visits': 100,
        'this_month_visits': 3000
    }
    с_user_id = current_user.id

    return render_template('admin/index.html', last_orders=last_orders, traffic=traffic_info, datetime=datetime)


# ---------------------------
#     ЗАКАЗЫ
# ---------------------------

@admin_bp.route('/orders', methods=['GET'])
@admin_required
def admin_orders():
    """Список заказов с пагинацией и фильтрацией по статусу."""
    status = request.args.get('status', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 20

    query = Order.query.order_by(Order.created_at.desc())
    if status:
        query = query.filter(Order.status == status)

    orders = query.paginate(page=page, per_page=per_page)
    return render_template('admin/orders_list.html', orders=orders, status=status)


@admin_bp.route('/orders/<int:order_id>', methods=['GET', 'POST'])
@admin_required
def admin_order_view(order_id):
    """Детали заказа. POST меняет статус."""
    order = Order.query.get_or_404(order_id)

    if request.method == 'POST':
        new_status = request.form.get('status', '').strip()
        if new_status:
            try:
                order.status = new_status
                db.session.commit()
                flash('Статус заказа обновлён', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка обновления статуса: {e}', 'danger')
        return redirect(url_for('admin.admin_order_view', order_id=order.id))

    # Готовим карту id->объект для опций и значений, чтобы расшифровать выбранные
    option_ids = set()
    value_ids = set()
    for item in order.items:
        if getattr(item, 'selected_options', None):
            try:
                data = json.loads(item.selected_options)
                for k, v in (data.items() if isinstance(data, dict) else []):
                    try:
                        option_ids.add(int(k))
                    except Exception:
                        pass
                    try:
                        value_ids.add(int(v))
                    except Exception:
                        pass
            except Exception:
                pass

    options_map = {o.id: o for o in (ProductOption.query.filter(ProductOption.id.in_(option_ids)).all() if option_ids else [])}
    values_map = {v.id: v for v in (ProductOptionValue.query.filter(ProductOptionValue.id.in_(value_ids)).all() if value_ids else [])}

    allowed_statuses = ['new', 'processing', 'paid', 'shipped', 'completed', 'canceled']
    return render_template('admin/order_view.html', order=order, options_map=options_map, values_map=values_map, allowed_statuses=allowed_statuses)


@admin_bp.route('/orders/<int:order_id>/comment', methods=['POST'])
@admin_required
def add_order_comment(order_id):
    order = Order.query.get_or_404(order_id)
    text = request.form.get('comment', '').strip()
    if not text:
        return redirect(url_for('admin.admin_order_view', order_id=order.id))
    try:
        comment = OrderComment(order_id=order.id, user_id=current_user.id, comment=text)
        db.session.add(comment)
        db.session.commit()
        flash('Комментарий добавлен', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка добавления комментария: {e}', 'danger')
    return redirect(url_for('admin.admin_order_view', order_id=order.id))


# ---------------------------
#     КАТЕГОРИИ
# ---------------------------

@admin_bp.route('/categories', methods=['GET', 'POST'])
@admin_required
def admin_categories():
    """
    Список категорий (с деревом), + массовые действия (POST).
    """
    if request.method == 'POST':
        action = request.form.get('action')
        selected_ids = request.form.getlist('selected_ids', type=int)
        if action == 'delete_selected':
            deleted_count = 0
            for cid in selected_ids:
                try:
                    cat = Category.query.get(cid)
                    if cat:
                        print(f"Удаляем категорию: {cat.name} (ID: {cat.id})")
                        
                        # Получаем все товары в этой категории (включая подкатегории)
                        def get_all_products_in_category(cat_id):
                            """Рекурсивно получает все товары в категории и её подкатегориях"""
                            products = []
                            
                            # Товары в текущей категории
                            category_products = Product.query.filter_by(category_id=cat_id).all()
                            products.extend(category_products)
                            
                            # Подкатегории
                            subcategories = Category.query.filter_by(parent_id=cat_id).all()
                            for subcat in subcategories:
                                products.extend(get_all_products_in_category(subcat.id))
                            
                            return products
                        
                        all_products = get_all_products_in_category(cat.id)
                        print(f"Найдено товаров для удаления: {len(all_products)}")
                        
                        # Удаляем все товары в категории
                        for product in all_products:
                            print(f"Удаляем товар: {product.name} (ID: {product.id})")
                            # Используем функцию delete_product для корректного удаления
                            delete_product(product.id)
                        
                        # Удаляем SEO настройки категории
                        SEOSettings.query.filter_by(page_type='category', page_id=cat.id).delete()
                        
                        # Удаляем саму категорию
                        db.session.delete(cat)
                        deleted_count += 1
                        
                except Exception as e:
                    print(f"Ошибка удаления категории {cid}: {e}")
            
            try:
                db.session.commit()
                flash(f"Удалено {deleted_count} категорий и все товары в них.", "success")
            except Exception as e:
                db.session.rollback()
                flash(f"Ошибка при массовом удалении категорий: {e}", "danger")
        elif action == 'toggle_index_selected':
            for cid in selected_ids:
                cat = Category.query.get(cid)
                if cat:
                    cat.is_indexed = not cat.is_indexed
            db.session.commit()
            flash(f"Флаг 'Индексировать' переключён для {len(selected_ids)} категорий.", "success")

        return redirect(url_for('admin.admin_categories'))

    # GET
    cat_list = build_category_list(parent_id=None, level=0)
    return render_template('admin/categories_list.html', cat_list=cat_list)


@admin_bp.route('/categories/form', defaults={'category_id': None}, methods=['GET', 'POST'])
@admin_bp.route('/categories/form/<int:category_id>', methods=['GET', 'POST'])
@admin_required
def admin_categories_form(category_id):
    if category_id:
        category = Category.query.get_or_404(category_id)
        existing_seo = SEOSettings.query.filter_by(page_type='category', page_id=category.id).first()
    else:
        category = None
        existing_seo = None

    form = CategoryForm(obj=category)
    # Если SEO уже есть, подставим в форму

    # Дополнительные формы (модалки)
    img_form = ImageUploadForm()
    img_edit_form = ImageEditForm()
    dir_form = DirectoryForm()
    dir_edit_form = DirectoryForm()

    if request.method == 'POST':
        if category_id:
            form.process_slug(category_id)
        else:
            form.process_slug()
        # print("DEBUG: form.data =", form.data)
        # print("DEBUG: form.errors =", form.errors)
        if not category:
            category = Category()

        category.name = form.name.data
        # Автоматически генерируем slug на латинице, если не указан
        if not form.slug.data:
            from .forms import slugify, generate_unique_slug
            base_slug = slugify(form.name.data)
            if not base_slug:
                base_slug = 'category'
            category.slug = generate_unique_slug(base_slug)
        else:
            category.slug = form.slug.data
        category.sort_order = form.sort_order.data
        category.is_indexed = form.is_indexed.data
        category.description = form.description.data
        # Image ID
        if form.image_id.data:
            category.image_id = int(form.image_id.data)
        else:
            category.image_id = None

        if form.parent.data and hasattr(form.parent.data, 'id'):
            category.parent_id = form.parent.data.id
        else:
            category.parent_id = None

        db.session.add(category)
        db.session.commit()

        # --- Обновляем или создаём запись SEO ---
        seo = existing_seo or SEOSettings(page_type='category', page_id=category.id)
        seo.meta_title = form.meta_title.data
        seo.meta_description = form.meta_description.data
        seo.meta_keywords = form.meta_keywords.data
        seo.slug = category.slug

        db.session.add(seo)
        db.session.commit()

        return redirect(url_for('admin.admin_categories'))
    if existing_seo:
        form.meta_title.data = existing_seo.meta_title
        form.meta_description.data = existing_seo.meta_description
        form.meta_keywords.data = existing_seo.meta_keywords

    return render_template(
        'admin/category_form.html',
        form=form,
        category=category,
        img_form=img_form,
        img_edit_form=img_edit_form,
        dir_form=dir_form,
        dir_edit_form=dir_edit_form
    )


@admin_bp.route('/categories/<int:category_id>/delete', methods=['POST'])
@admin_required
def admin_categories_delete(category_id):
    try:
        print(f"=== НАЧАЛО УДАЛЕНИЯ КАТЕГОРИИ {category_id} ===")
        category = Category.query.get_or_404(category_id)
        print(f"Категория найдена: {category.name}")
        
        # Получаем все товары в этой категории (включая подкатегории)
        def get_all_products_in_category(cat_id):
            """Рекурсивно получает все товары в категории и её подкатегориях"""
            products = []
            
            # Товары в текущей категории
            category_products = Product.query.filter_by(category_id=cat_id).all()
            products.extend(category_products)
            
            # Подкатегории
            subcategories = Category.query.filter_by(parent_id=cat_id).all()
            for subcat in subcategories:
                products.extend(get_all_products_in_category(subcat.id))
            
            return products
        
        all_products = get_all_products_in_category(category_id)
        print(f"Найдено товаров для удаления: {len(all_products)}")
        
        # Удаляем все товары в категории
        for product in all_products:
            print(f"Удаляем товар: {product.name} (ID: {product.id})")
            # Используем функцию delete_product для корректного удаления
            delete_product(product.id)
        
        # Удаляем SEO настройки категории
        SEOSettings.query.filter_by(page_type='category', page_id=category.id).delete()
        
        # Удаляем саму категорию
        db.session.delete(category)
        db.session.commit()
        
        print(f"=== УДАЛЕНИЕ КАТЕГОРИИ {category_id} ЗАВЕРШЕНО УСПЕШНО ===")
        flash(f'Категория "{category.name}" и все товары в ней успешно удалены', 'success')
        
    except Exception as e:
        print(f"❌ Ошибка при удалении категории {category_id}: {e}")
        db.session.rollback()
        flash(f'Ошибка при удалении категории: {str(e)}', 'error')
    
    return redirect(url_for('admin.admin_categories'))


# ---------------------------
#     ДИРЕКТОРИИ / ИЗОБРАЖЕНИЯ
# ---------------------------




@admin_bp.route('/directories/view', defaults={'dir_id': None})
@admin_bp.route('/directories/view/<int:dir_id>')
@admin_required
def admin_directories_view(dir_id):
    """
    Показ списка каталогов и изображений (полная страница или partial).
    """

    if dir_id and dir_id != 0:
        current_dir = Directory.query.get_or_404(dir_id)
        subdirs = Directory.query.filter_by(parent_id=dir_id).all()
        images = Image.query.filter_by(directory_id=dir_id).all()
    else:
        current_dir = None
        subdirs = Directory.query.filter_by(parent_id=None).all()
        images = Image.query.filter(Image.directory_id.is_(None)).all()

    dir_form = DirectoryForm()
    if current_dir:
        dir_form.parent_id.data = str(current_dir.id)
    else:
        dir_form.parent_id.data = ""

    img_form = ImageUploadForm()
    if current_dir:
        img_form.directory_id.data = str(current_dir.id)
    else:
        img_form.directory_id.data = ""

    img_edit_form = ImageEditForm()
    dir_edit_form = DirectoryForm()
    
    # Получаем все каталоги для выпадающих списков
    all_directories = Directory.query.all()

    # Если AJAX-запрос -> вернуть partial (но у вас пока не используется?)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('admin/_directories_partial.html', current_dir=current_dir,
                               subdirs=subdirs,
                               images=images,
                               dir_form=dir_form,
                               img_form=img_form,
                               all_directories=all_directories)
    else:
        return render_template(
            'admin/directory_view.html',
            current_dir=current_dir,
            subdirs=subdirs,
            images=images,
            dir_form=dir_form,
            img_form=img_form,
            img_edit_form=img_edit_form,
            dir_edit_form=dir_edit_form,
            all_directories=all_directories
        )


@admin_bp.route('/directories/create', methods=['POST'])
@csrf.exempt
@admin_required
def admin_directories_create():
    try:
        print("=== СОЗДАНИЕ КАТАЛОГА ===")
        print("Request method:", request.method)
        print("Request data:", request.form.to_dict())
        print("Headers:", dict(request.headers))
        
        # Обходим форму и работаем напрямую с request.form
        name = request.form.get('name', '').strip()
        parent_id = request.form.get('parent_id', '')
        
        print(f"Name from request: '{name}'")
        print(f"Parent ID from request: '{parent_id}'")
        
        if not name:
            print("✗ Пустое имя каталога")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify(ok=False, message="Имя каталога не может быть пустым"), 400
            flash('Имя каталога не может быть пустым', 'error')
            return redirect(request.referrer)
        
        # Преобразуем parent_id
        try:
            if parent_id and parent_id != '0':
                parent_id = int(parent_id)
            else:
                parent_id = None
        except ValueError:
            parent_id = None
            
        print(f"✓ Создаем каталог: name='{name}', parent_id={parent_id}")
        
        d = Directory(name=name, parent_id=parent_id)
        db.session.add(d)
        db.session.commit()
        print(f"✓ Каталог создан с ID: {d.id}")
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Вернём JSON с полем ok и dir_id
            return jsonify(ok=True, dir_id=parent_id, message="Каталог успешно создан")
        else:
            flash('Каталог успешно создан', 'success')
            return redirect(url_for('admin.admin_directories_view', dir_id=parent_id))
    except Exception as e:
        print("✗ Исключение:", str(e))
        import traceback
        traceback.print_exc()
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(ok=False, message=str(e)), 500
        flash(f'Ошибка создания каталога: {str(e)}', 'error')
        return redirect(request.referrer)


@admin_bp.route('/directories/<int:dir_id>/delete', methods=['POST'])
@csrf.exempt
@admin_required
def admin_directories_delete(dir_id):
    print("=== УДАЛЕНИЕ КАТАЛОГА ===")
    print(f"Directory ID: {dir_id}")
    print("Request method:", request.method)
    print("Headers:", dict(request.headers))
    
    try:
        d = Directory.query.get_or_404(dir_id)
        print(f"Найден каталог: {d.name} с parent_id={d.parent_id}")
        print(f"Количество изображений в каталоге: {len(d.images)}")
        

        
        # Проверяем подкаталоги
        subdirs = Directory.query.filter_by(parent_id=dir_id).all()
        print(f"Количество подкаталогов: {len(subdirs)}")
        
        if len(subdirs) > 0:
            print("✗ Каталог содержит подкаталоги - удаление запрещено")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify(ok=False, message="Сначала удалите все подкаталоги"), 400
            return "Сначала удалите все подкаталоги", 400
        
        # Если есть изображения - удаляем их каскадно
        if len(d.images) > 0:
            print(f"⚠ Каталог содержит {len(d.images)} изображений - выполняем каскадное удаление")
            upload_path = current_app.config['UPLOAD_FOLDER']
            
            # Удаляем файлы с диска
            for img in d.images:
                file_path = os.path.join(upload_path, img.filename)
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        print(f"✓ Удален файл: {img.filename}")
                    except OSError as e:
                        print(f"✗ Ошибка удаления файла {img.filename}: {e}")
                else:
                    print(f"⚠ Файл не найден на диске: {img.filename}")
                
                # Удаляем запись из БД
                db.session.delete(img)
            
            print(f"✓ Удалено {len(d.images)} изображений из каталога")
        
        parent_id = d.parent_id
        db.session.delete(d)
        db.session.commit()
        print(f"✓ Каталог удален вместе со всем содержимым, parent_id={parent_id}")
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            print("Возвращаем JSON ответ")
            return jsonify(ok=True, parent_id=parent_id)
        else:
            print("Возвращаем redirect")
            return redirect(url_for('admin.admin_directories_view', dir_id=parent_id))
            
    except Exception as e:
        print(f"✗ Ошибка при удалении каталога: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(ok=False, message=f"Ошибка: {str(e)}"), 500
        return f"Ошибка: {str(e)}", 500


@admin_bp.route('/directories/<int:dir_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_directories_edit(dir_id):
    """
    Редактирование каталога, если не через модалку, а отдельным шаблоном (может не использоваться).
    """
    d = Directory.query.get_or_404(dir_id)
    form = DirectoryForm(obj=d)
    if request.method == 'GET':
        form.parent_id.data = str(d.parent_id) if d.parent_id else ""
    if form.validate_on_submit():
        d.name = form.name.data
        parent_id = form.parent_id.data
        d.parent_id = int(parent_id) if parent_id else None
        db.session.commit()
        return redirect(url_for('admin.admin_directories_view', dir_id=d.parent_id))
    return "Stub or temporary page", 501


@admin_bp.route('/directories/<int:dir_id>/update', methods=['POST'])
@csrf.exempt
@admin_required
def admin_directories_update(dir_id):
    """
    Обработка переименования каталога (поддержка AJAX).
    """
    d = Directory.query.get_or_404(dir_id)
    
    # Получаем новое имя из запроса
    new_name = request.form.get('name', '').strip()
    
    if not new_name:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(ok=False, message="Название каталога не может быть пустым"), 400
        return redirect(request.referrer)
    
    # Проверяем уникальность имени в том же родительском каталоге
    existing = Directory.query.filter_by(name=new_name, parent_id=d.parent_id).first()
    if existing and existing.id != d.id:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(ok=False, message="Каталог с таким именем уже существует"), 400
        return redirect(request.referrer)
    
    d.name = new_name
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(ok=True, message="Каталог переименован")
    else:
        return redirect(url_for('admin.admin_directories_view', dir_id=d.parent_id))


@admin_bp.route('/images/upload', methods=['POST'])
@csrf.exempt
@admin_required
def admin_images_upload_post():
    """Обработка загрузки изображений (поддержка множественной загрузки)."""
    
    print("=== ЗАГРУЗКА ИЗОБРАЖЕНИЙ ===")
    print("Request method:", request.method)
    print("Request data:", dict(request.form))
    print("Request files:", list(request.files.keys()))
    print("Headers:", dict(request.headers))
    
    # Получаем directory_id из формы
    directory_id = request.form.get('directory_id')
    print(f"Directory ID raw: '{directory_id}'")

    # В корне (dir_id=0) должен быть NULL в БД, иначе нарушится FK
    if directory_id in (None, '', 'None', '0', 0):
        directory_id = None
    else:
        try:
            directory_id = int(directory_id)
            if directory_id == 0:
                directory_id = None
            else:
                # Валидация существования каталога
                if not Directory.query.get(directory_id):
                    directory_id = None
        except (ValueError, TypeError):
            directory_id = None

    print(f"Directory ID final: {directory_id}")

    # Получаем загруженные файлы
    uploaded_files = request.files.getlist('image')
    
    if not uploaded_files or not uploaded_files[0].filename:
        return "Ошибка: не выбраны файлы для загрузки", 400

    uploaded_count = 0
    errors = []

    for file in uploaded_files:
        if file and file.filename:
            try:
                original_filename = file.filename
                # Преобразуем русские символы в английские
                sanitized_filename = unidecode(original_filename)
                # Генерируем новое имя файла с сохранением расширения
                filename = save_image_file(file, sanitized_filename)
                
                img = Image(filename=filename, alt='', directory_id=directory_id)
                db.session.add(img)
                uploaded_count += 1
            except Exception as e:
                errors.append(f"Ошибка при загрузке {file.filename}: {str(e)}")

    if uploaded_count > 0:
        db.session.commit()
        print(f"✓ Загружено {uploaded_count} файлов в каталог {directory_id}")
    else:
        print("✗ Файлы не загружены")
    
    print(f"Errors: {errors}")

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        print("Возвращаем JSON ответ")
        return jsonify(
            ok=True, 
            dir_id=directory_id, 
            uploaded_count=uploaded_count,
            errors=errors
        )
    else:
        print("Возвращаем redirect")
        return redirect(url_for('admin.admin_directories_view', dir_id=directory_id))


@admin_bp.route('/images/<int:image_id>/update', methods=['POST'])
@csrf.exempt
@admin_required
def admin_images_update(image_id):
    """
    Изменение alt у изображения (поддержка AJAX).
    """
    img = Image.query.get_or_404(image_id)
    
    # Получаем новый alt из запроса
    new_alt = request.form.get('alt', '')
    directory_id = request.form.get('directory_id', img.directory_id)
    
    img.alt = new_alt
    # Пока не меняем directory_id для простоты
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(ok=True, message="Изображение обновлено")
    else:
        return redirect(url_for('admin.admin_directories_view', dir_id=img.directory_id))


@admin_bp.route('/images/<int:image_id>/delete', methods=['POST'])
@csrf.exempt
@admin_required
def admin_images_delete(image_id):
    print("=== УДАЛЕНИЕ ИЗОБРАЖЕНИЯ ===")
    print(f"Image ID: {image_id}")
    print("Request method:", request.method)
    print("Headers:", dict(request.headers))
    
    img = Image.query.get_or_404(image_id)
    print(f"Найдено изображение: {img.filename} в каталоге {img.directory_id}")
    
    # Удаляем файл с диска
    upload_path = current_app.config['UPLOAD_FOLDER']
    file_path = os.path.join(upload_path, img.filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            print(f"✓ Файл удален с диска: {file_path}")
        except OSError as e:
            print(f"✗ Ошибка удаления файла: {e}")
    else:
        print(f"✗ Файл не найден на диске: {file_path}")
    
    directory_id = img.directory_id
    db.session.delete(img)
    db.session.commit()
    print(f"✓ Изображение удалено из базы данных")
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        print("Возвращаем JSON ответ")
        return jsonify(ok=True, directory_id=directory_id)
    else:
        print("Возвращаем redirect")
        return redirect(url_for('admin.admin_directories_view', dir_id=directory_id))


#                   Товары
@admin_bp.route('/products/form', defaults={'product_id': None}, methods=['GET', 'POST'])
@admin_bp.route('/products/form/<int:product_id>', methods=['GET', 'POST'])
@admin_required
def product_form(product_id):
    import re  # Импортируем re в начале функции
    # 1) Если редактируем
    product = Product.query.get_or_404(product_id) if product_id else None

    # Основная форма
    form = ProductForm(obj=product)
    img_form = ImageUploadForm()
    dir_form = DirectoryForm()

    existing_option_form = ExistingOptionForm()  # выбор уже существующей опции
    product_options = ProductOption.get_options_by_product_id(product_id)
    product_variations = ProductVariation.get_variations_by_product_id(product_id)
    options = db.session.query(ProductOption).all()
    # SEO
    existing_seo = None
    if product:
        existing_seo = SEOSettings.query.filter_by(page_type='product', page_id=product.id).first()

    # -------------------------------
    # [GET] Заполняем форму, если редактируем
    # -------------------------------
    if request.method == 'GET' and product:
        # SEO
        if existing_seo:
            form.meta_title.data = existing_seo.meta_title
            form.meta_description.data = existing_seo.meta_description
            form.meta_keywords.data = existing_seo.meta_keywords

        # Доп. изображения
        if product:
            # Загружаем изображения с порядком
            additional_images_with_order = db.session.query(Image, product_images.c.order) \
                .join(product_images, Image.id == product_images.c.image_id) \
                .filter(product_images.c.product_id == product.id) \
                .order_by(product_images.c.order) \
                .all()

            # Извлекаем только объекты Image и добавляем динамический order
            product.additional_images = []
            for img, order in additional_images_with_order:
                img.order = order  # Добавляем order как динамический атрибут
                product.additional_images.append(img)  # Добавляем в список

            # Заполняем скрытое поле формы с ID изображений (учитывая порядок)
            form.additional_image_ids.data = ",".join(str(img.id) for img in product.additional_images)

            # Проверяем порядок в консоли
            print("IDs изображений:", form.additional_image_ids.data)
        else:
            form.additional_image_ids.data = ""

    # -------------------------------
    # [POST] Сохранение
    # -------------------------------
    # Обрабатываем связанные товары независимо от валидации основной формы
    if request.method == 'POST' and product:
        # ---------- Связанные товары ----------
        from ..models.product import RelatedProduct
        
        # Удаляем старые связи
        RelatedProduct.query.filter_by(product_id=product.id).delete()
        
        # Обрабатываем новые связи
        raw_related = {}
        for key, val in request.form.items():
            if key.startswith('related_products['):
                m = re.match(r'related_products\[(\d+)\]\[(\w+)\]', key)
                if m:
                    idx = int(m.group(1))
                    field = m.group(2)
                    if idx not in raw_related:
                        raw_related[idx] = {}
                    raw_related[idx][field] = val

        for idx, data in raw_related.items():
            product_id_related = data.get('product_id')
            link_text = data.get('link_text')
            sort_order = data.get('sort_order', 0)
            
            if product_id_related and link_text:
                try:
                    related_product = RelatedProduct(
                        product_id=product.id,
                        related_product_id=int(product_id_related),
                        link_text=link_text.strip(),
                        sort_order=int(sort_order) if sort_order else 0
                    )
                    db.session.add(related_product)
                except (ValueError, TypeError):
                    continue  # Пропускаем некорректные данные
        
        # Сохраняем связанные товары
        try:
            db.session.commit()
            if raw_related:
                flash("Связанные товары обновлены.", "info")
        except Exception as e:
            db.session.rollback()
            flash(f"Ошибка при сохранении связанных товаров: {e}", "warning")
    
    if form.validate_on_submit():
        # Создаём товар, если его не было
        if not product:
            product = Product()
            db.session.add(product)

        # Заполняем поля товара
        form.populate_obj(product)
        product.process_slug()

        # Главное изображение
        if form.main_image_id.data:
            product.main_image_id = int(form.main_image_id.data)
        else:
            product.main_image_id = None

        # Доп. изображения
        if form.additional_image_ids.data:
            print("Полученные данные о порядке изображений:",
                  form.additional_image_ids.data)  # Проверяем, что передается в Flask
            ids_list = [int(x) for x in form.additional_image_ids.data.split(',') if x.strip().isdigit()]

            # Удаляем старые связи
            db.session.execute(
                product_images.delete().where(product_images.c.product_id == product.id)
            )

            # Добавляем изображения с новым порядком
            for index, image_id in enumerate(ids_list):
                db.session.execute(
                    product_images.insert().values(
                        product_id=product.id,
                        image_id=image_id,
                        order=index
                    )
                )
                print(f"Добавляем изображение {image_id} с порядком {index}")  # Проверяем, какие данные идут в БД
        else:
            db.session.execute(
                product_images.delete().where(product_images.c.product_id == product.id)
            )

        db.session.commit()

        # ---------- Атрибуты ----------
        if product_id:
            db.session.query(ProductAttribute).filter_by(product_id=product.id).delete()

        raw_attrs = {}
        for key, val in request.form.items():
            if key.startswith('attributes['):
                m = re.match(r'attributes\[(\d+)\]\[(\w+)\]', key)
                if m:
                    idx = int(m.group(1))
                    field = m.group(2)
                    if idx not in raw_attrs:
                        raw_attrs[idx] = {}
                    raw_attrs[idx][field] = val

        for idx, dataA in raw_attrs.items():
            a_name = dataA.get('name')
            a_val = dataA.get('value')
            if a_name and a_val:
                # Создаём или ищем Attribute
                attribute = Attribute.query.filter_by(name=a_name).first()
                if not attribute:
                    attribute = Attribute(name=a_name)
                    db.session.add(attribute)
                    db.session.flush()

                # Создаём/ищем AttributeValue
                attr_value = AttributeValue.query.filter_by(attribute_id=attribute.id, value=a_val).first()
                if not attr_value:
                    attr_value = AttributeValue(attribute_id=attribute.id, value=a_val)
                    db.session.add(attr_value)
                    db.session.flush()

                # Привязка к товару
                pa = ProductAttribute(product_id=product.id, attribute_value_id=attr_value.id)
                db.session.add(pa)

        db.session.execute(
            product_option_association.delete().where(
                product_option_association.c.product_id == product.id
            )
        )
        db.session.execute(
            product_option_value_association.delete().where(
                product_option_value_association.c.product_id == product.id
            )
        )

        raw_options = {}  # Словарь вида { idx: {"name": ..., "values_ids": "..."}, ... }
        for key, val in request.form.items():
            # Ищем шаблон "options[<номер>][existing_option_id]" или "options[<номер>][values_ids]"
            match_opt = re.match(r'^options\[(\d+)\]\[(\w+)\]$', key)
            if match_opt:
                opt_idx = int(match_opt.group(1))
                field_name = match_opt.group(2)

                if opt_idx not in raw_options:
                    raw_options[opt_idx] = {}
                raw_options[opt_idx][field_name] = val

        for _, opt_data in raw_options.items():
            option_name = opt_data.get('existing_option_id', '').strip()
            values_str = opt_data.get('values_ids', '').strip()
            display_type = opt_data.get('display_type', 'select').strip()
            has_individual_photos = opt_data.get('has_individual_photos', 'false').strip() == 'true'
            
            if not option_name:
                continue

            option = ProductOption.query.filter_by(name=option_name).first()
            if not option:
                option = ProductOption(
                    name=option_name,
                    display_type=display_type,
                    has_individual_photos=has_individual_photos
                )
                db.session.add(option)
                db.session.flush()
            else:
                # Обновляем существующую опцию
                option.display_type = display_type
                option.has_individual_photos = has_individual_photos

            # Связываем товар с этой опцией (product_option_association)
            # Можно просто выполнить INSERT в association-таблицу:
            db.session.execute(
                product_option_association.insert().values(
                    product_id=product.id,
                    option_id=option.id
                )
            )

            # Теперь значения опции (например, "Красный,Белый")
            if values_str:
                for val_name in values_str.split(','):
                    val_name = val_name.strip()
                    if not val_name:
                        continue

                    # Ищем/создаём значение опции
                    value_obj = ProductOptionValue.query.filter_by(
                        option_id=option.id, value=val_name
                    ).first()
                    if not value_obj:
                        value_obj = ProductOptionValue(
                            option_id=option.id,
                            value=val_name
                        )
                        db.session.add(value_obj)
                        db.session.flush()

                    # Связываем товар с этим значением (product_option_value_association)
                    db.session.execute(
                        product_option_value_association.insert().values(
                            product_id=product.id,
                            option_value_id=value_obj.id
                        )
                    )
        # Вариации: удаляем/пересоздаём ТОЛЬКО если явно пришли данные для генерации (combo/combo_ids)
        has_variation_fields = any(k.startswith('variations[') for k in request.form.keys())
        has_combo_data = any(re.match(r'^variations\[\d+\]\[(combo|combo_ids)\]\[', k) for k in request.form.keys())
        regenerate_flag = request.form.get('regenerate_variations', '').lower() in ('1', 'true', 'yes')
        # Если пришли id существующих вариаций без combo/combo_ids, значит просто обновляем, не регенерируем
        has_existing_ids = any(re.match(r'^variations\[(\d+)\]\[id\]$', k) for k in request.form.keys())
        should_regenerate = regenerate_flag or (has_variation_fields and has_combo_data and not has_existing_ids)
        current_app.logger.info('[Product Save] regenerate_flag=%s, has_variation_fields=%s, has_combo_data=%s, has_existing_ids=%s => should_regenerate=%s',
                                regenerate_flag, has_variation_fields, has_combo_data, has_existing_ids, should_regenerate)
        if should_regenerate:
            # Перед удалением вариаций отвяжем их от позиций заказов, чтобы не нарушать FK
            from ..models.order import OrderItem
            variation_ids_subq = db.session.query(ProductVariation.id).filter_by(product_id=product.id).subquery()
            # Обнуляем ссылки в order_items
            db.session.query(OrderItem).filter(
                OrderItem.variation_id.in_(db.session.query(ProductVariation.id).filter_by(product_id=product.id))
            ).update({OrderItem.variation_id: None}, synchronize_session=False)

            # Удаляем значения-линки вариаций
            db.session.query(ProductVariationOptionValue).filter(
                ProductVariationOptionValue.variation_id.in_(variation_ids_subq)
            ).delete(synchronize_session=False)

            # Удаляем сами вариации товара
            db.session.query(ProductVariation).filter_by(product_id=product.id).delete(synchronize_session=False)

        raw_variations = {}
        if should_regenerate:
            # { var_idx: { 'sku': ..., 'price': ..., 'combo': {combo_idx: {'name':..., 'value':...}} }, ... }
            for key, val in request.form.items():
                m = re.match(r'^variations\[(\d+)\]\[(\w+)\]$', key)  # основные поля вариации
                if m:
                    var_idx = int(m.group(1))
                    field = m.group(2)
                    if var_idx not in raw_variations:
                        raw_variations[var_idx] = {"combo": {}}
                    raw_variations[var_idx][field] = val

                # combo: variations[x][combo][y][name], variations[x][combo][y][value]
                c = re.match(r'^variations\[(\d+)\]\[combo\]\[(\d+)\]\[(\w+)\]$', key)
                if c:

                    var_idx = int(c.group(1))
                    combo_idx = int(c.group(2))
                    combo_field = c.group(3)
                    if var_idx not in raw_variations:
                        raw_variations[var_idx] = {"combo": {}}
                    if "combo" not in raw_variations[var_idx]:
                        raw_variations[var_idx]["combo"] = {}
                    if combo_idx not in raw_variations[var_idx]["combo"]:
                        raw_variations[var_idx]["combo"][combo_idx] = {}

                    raw_variations[var_idx]["combo"][combo_idx][combo_field] = val

                # Альтернативный формат: variations[x][combo_ids][y][option_id|value_id]
                cids = re.match(r'^variations\[(\d+)\]\[combo_ids\]\[(\d+)\]\[(\w+)\]$', key)
                if cids:
                    var_idx = int(cids.group(1))
                    combo_idx = int(cids.group(2))
                    combo_field = cids.group(3)
                    if var_idx not in raw_variations:
                        raw_variations[var_idx] = {"combo": {}, "combo_ids": {}}
                    if "combo_ids" not in raw_variations[var_idx]:
                        raw_variations[var_idx]["combo_ids"] = {}
                    if combo_idx not in raw_variations[var_idx]["combo_ids"]:
                        raw_variations[var_idx]["combo_ids"][combo_idx] = {}
                    raw_variations[var_idx]["combo_ids"][combo_idx][combo_field] = val

            # Лог входящих данных по вариациям
            print("DEBUG raw_variations:", raw_variations)

        # Теперь создаём/сохраняем вариации, если они были присланы
        for _, data_v in (raw_variations.items() if should_regenerate else []):
            sku = data_v.get('sku', '').strip()
            price = data_v.get('price', '0').strip()
            stock = data_v.get('stock', '0').strip()
            slug = data_v.get('slug', '').strip()
            is_photo_variation = data_v.get('is_photo_variation', 'false').strip() == 'true'

            # SEO
            seo_title = data_v.get('seo_title', '').strip()
            seo_desc = data_v.get('seo_description', '').strip()
            seo_keys = data_v.get('seo_keywords', '').strip()
            image_id = data_v.get('image_id')
            image_id = int(image_id) if image_id and image_id.isdigit() else None

            # Проверяем уникальность SKU и генерируем новый если нужно
            if not sku or ProductVariation.query.filter_by(sku=sku).filter(ProductVariation.product_id != product.id).first():
                import time
                if is_photo_variation:
                    sku = f"photo-var-{product.id}-{int(time.time())}"
                else:
                    sku = f"var-{product.id}-{int(time.time())}"

            variation = ProductVariation(
                product_id=product.id,
                sku=sku,
                price=price,
                stock=stock,
                slug=slug or None,
                seo_keys=seo_keys,
                seo_title=seo_title or None,
                seo_description=seo_desc or None,
                image_id=image_id
            )
            variation.generate_slug()
            db.session.add(variation)
            db.session.flush()

            # Обрабатываем combo (по именам)
            #  Например: data_v["combo"] = {0: {'name': 'Цвет', 'value': 'Красный'}, 1: ...}
            combo_dict = data_v.get('combo', {})

            for _, combo_item in combo_dict.items():
                combo_name = combo_item.get('name', '').strip()
                combo_value = combo_item.get('value', '').strip()
                if not combo_name or not combo_value:
                    continue

                # Ищем нужный option ТОЛЬКО среди опций, связанных с текущим товаром
                option = db.session.query(ProductOption).join(
                    product_option_association,
                    product_option_association.c.option_id == ProductOption.id
                ).filter(
                    product_option_association.c.product_id == product.id,
                    ProductOption.name == combo_name
                ).first()
                if not option:
                    # Если опция не найдена среди связанных с товаром — пробуем найти глобально по имени
                    option = ProductOption.query.filter_by(name=combo_name).first()
                    if not option:
                        # Создаём новую опцию и сразу привязываем к товару
                        option = ProductOption(name=combo_name, display_type='select')
                        db.session.add(option)
                        db.session.flush()
                    # Обеспечиваем связь опции с текущим товаром
                    db.session.execute(
                        product_option_association.insert().values(
                            product_id=product.id,
                            option_id=option.id
                        )
                    )

                # Ищем нужный option_value в рамках найденной опции
                option_value = ProductOptionValue.query.filter_by(option_id=option.id, value=combo_value).first()
                if not option_value:
                    option_value = ProductOptionValue(
                        option_id=option.id,
                        value=combo_value
                    )
                    db.session.add(option_value)
                    db.session.flush()

                # Связь Variation – OptionValue
                pov = ProductVariationOptionValue(
                    variation_id=variation.id,
                    option_value_id=option_value.id
                )
                db.session.add(pov)

            # Обрабатываем combo_ids (по ID опции и ID значения)
            combo_ids = data_v.get('combo_ids', {})
            for _, combo_item in combo_ids.items():
                opt_id_raw = combo_item.get('option_id')
                val_id_raw = combo_item.get('value_id')
                try:
                    opt_id = int(opt_id_raw) if opt_id_raw is not None else None
                    val_id = int(val_id_raw) if val_id_raw is not None else None
                except ValueError:
                    opt_id = None
                    val_id = None
                if not opt_id or not val_id:
                    continue

                option = ProductOption.query.get(opt_id)
                value_obj = ProductOptionValue.query.get(val_id)
                if not option or not value_obj:
                    continue

                # Гарантируем, что опция привязана к товару
                exists_link = db.session.execute(
                    product_option_association.select().where(
                        (product_option_association.c.product_id == product.id) &
                        (product_option_association.c.option_id == option.id)
                    )
                ).first()
                if not exists_link:
                    db.session.execute(
                        product_option_association.insert().values(product_id=product.id, option_id=option.id)
                    )

                pov = ProductVariationOptionValue(
                    variation_id=variation.id,
                    option_value_id=value_obj.id
                )
                db.session.add(pov)
        # Обновление существующих вариаций (без регенерации): по hidden id
        if not should_regenerate:
            # проходим пришедшие поля вариаций с id и обновляем только их основные поля
            update_map = {}
            for key, val in request.form.items():
                m = re.match(r'^variations\[(\d+)\]\[(\w+)\]$', key)
                if not m:
                    continue
                idx = int(m.group(1))
                field = m.group(2)
                if field == 'id':
                    try:
                        update_map[idx] = {'id': int(val)}
                    except ValueError:
                        continue
                else:
                    if idx not in update_map:
                        update_map[idx] = {}
                    update_map[idx][field] = val
            current_app.logger.info('[Product Save] update_map indices=%s', list(update_map.keys()))
            for idx_key, payload in update_map.items():
                var_id = payload.get('id')
                if not var_id:
                    continue
                variation = ProductVariation.query.filter_by(id=var_id, product_id=product.id).first()
                if not variation:
                    continue
                # обновляем простые поля
                before = {
                    'sku': variation.sku,
                    'price': str(variation.price),
                    'stock': variation.stock,
                    'slug': variation.slug,
                    'seo_title': variation.seo_title,
                    'seo_description': variation.seo_description,
                    'seo_keys': variation.seo_keys,
                    'image_id': variation.image_id,
                }
                variation.sku = payload.get('sku', variation.sku)
                variation.price = payload.get('price', variation.price)
                variation.stock = payload.get('stock', variation.stock)
                variation.slug = (payload.get('slug') or variation.slug)
                variation.seo_title = payload.get('seo_title') or variation.seo_title
                variation.seo_description = payload.get('seo_description') or variation.seo_description
                variation.seo_keys = payload.get('seo_keywords') or variation.seo_keys
                img_raw = payload.get('image_id')
                if img_raw and img_raw.isdigit():
                    variation.image_id = int(img_raw)
                current_app.logger.info('[Product Save] Updated variation id=%s fields: before=%s after={"sku":%s,"price":%s,"stock":%s,"slug":%s,"seo_title":%s,"seo_description":%s,"seo_keys":%s,"image_id":%s}',
                                        var_id, before, variation.sku, variation.price, variation.stock, variation.slug, variation.seo_title, variation.seo_description, variation.seo_keys, variation.image_id)
                # Обновляем связи вариации с выбранными значениями опций, если пришли combo_ids
                # Считываем все combo_ids для данного индекса вариации
                combo_items = []
                for key2, val2 in request.form.items():
                    c = re.match(rf'^variations\[{idx_key}\]\[combo_ids\]\[(\d+)\]\[(option_id|value_id)\]$', key2)
                    if c:
                        combo_idx = int(c.group(1))
                        field_name = c.group(2)
                        while len(combo_items) <= combo_idx:
                            combo_items.append({'option_id': None, 'value_id': None})
                        combo_items[combo_idx][field_name] = val2
                # Фильтруем валидные value_id
                value_ids = []
                for item in combo_items:
                    try:
                        vid = int(item.get('value_id') or 0)
                    except Exception:
                        vid = 0
                    if vid:
                        value_ids.append(vid)
                current_app.logger.info('[Product Save] variation idx=%s id=%s parsed combo_items=%s => value_ids=%s', idx_key, var_id, combo_items, value_ids)
                if value_ids:
                    # Удаляем старые и создаем новые связи PVOV
                    deleted = db.session.query(ProductVariationOptionValue).filter_by(variation_id=variation.id).delete()
                    current_app.logger.info('[Product Save] variation id=%s removed %s old PVOV links', var_id, deleted)
                    for vid in value_ids:
                        db.session.add(ProductVariationOptionValue(variation_id=variation.id, option_value_id=vid))
                    current_app.logger.info('[Product Save] variation id=%s added PVOV value_ids=%s', var_id, value_ids)
                else:
                    current_app.logger.info('[Product Save] variation id=%s received no combo_ids; PVOV unchanged', var_id)

        # ---------- SEO ----------
        seo = existing_seo or SEOSettings(page_type='product', page_id=product.id)
        seo.meta_title = form.meta_title.data
        seo.meta_description = form.meta_description.data
        seo.meta_keywords = form.meta_keywords.data
        seo.slug = product.slug
        db.session.add(seo)

        # ---------- Фотографии значений опций ----------
        from ..models.productOptions import ProductOptionValueImage
        
        # Сначала удаляем старые фотографии опций для этого товара
        if product_id:
            # Получаем все значения опций для данного товара
            option_values = db.session.query(ProductOptionValue).join(
                product_option_value_association,
                (product_option_value_association.c.option_value_id == ProductOptionValue.id)
            ).filter(
                product_option_value_association.c.product_id == product.id
            ).all()
            
            for option_value in option_values:
                ProductOptionValueImage.query.filter_by(option_value_id=option_value.id).delete()

        # Обрабатываем новые фотографии опций
        option_photos = {}
        for key, val in request.form.items():
            if key.startswith('option_photos['):
                # Парсим option_photos[OptionName][Value] = "id1,id2,id3"
                match = re.match(r'option_photos\[([^\]]+)\]\[([^\]]+)\]', key)
                if match:
                    option_name = match.group(1)
                    option_value = match.group(2)
                    image_ids = [x.strip() for x in val.split(',') if x.strip()]
                    
                    if option_name not in option_photos:
                        option_photos[option_name] = {}
                    option_photos[option_name][option_value] = image_ids

        # Сохраняем фотографии опций
        for option_name, values_dict in option_photos.items():
            for option_value, image_ids in values_dict.items():
                # Находим ProductOptionValue
                option = ProductOption.query.filter_by(name=option_name).first()
                if option:
                    option_value_obj = ProductOptionValue.query.filter_by(
                        option_id=option.id, value=option_value
                    ).first()
                    
                    if option_value_obj:
                        # Сохраняем каждое изображение
                        for order, image_id in enumerate(image_ids):
                            if image_id.isdigit():
                                photo = ProductOptionValueImage(
                                    option_value_id=option_value_obj.id,
                                    image_id=int(image_id),
                                    order=order,
                                    is_main=(order == 0)  # Первое фото - главное
                                )
                                db.session.add(photo)

        # Связь товара с выбранной размерной сеткой
        size_chart_id = request.form.get('size_chart_id', type=int)
        ProductSizeChart.query.filter_by(product_id=product.id).delete()
        if size_chart_id:
            db.session.add(ProductSizeChart(product_id=product.id, size_chart_id=size_chart_id))

        # Сохраняем
        try:
            db.session.commit()
            flash("Товар успешно сохранён.", "success")
        except IntegrityError as e:
            db.session.rollback()
            flash(f"Ошибка БД: {e}", "danger")
            return redirect(url_for('admin.product_form', product_id=product.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Ошибка сохранения: {e}", "danger")
            return redirect(url_for('admin.product_form', product_id=product.id))

        return redirect(url_for('admin.list_products'))

    # GET или не прошла валидацию
    # Подготавливаем данные о фотографиях опций для JavaScript
    import json
    existing_option_photos = {}
    print(f"DEBUG: product_options = {product_options}")
    for option in product_options:
        print(f"DEBUG: Проверяем опцию: {option.get('name', 'N/A')}, has_individual_photos = {option.get('has_individual_photos', False)}")
        if option.get('has_individual_photos', False):
            option_photos = {}
            for value in option['values']:
                print(f"DEBUG: Значение опции: {value.get('value', 'N/A')}, фото: {value.get('photos', [])}")
                option_photos[value['value']] = value.get('photos', [])
            existing_option_photos[option['name']] = option_photos
    
    print(f"DEBUG: existing_option_photos = {existing_option_photos}")
    # Простой JSON без дополнительного экранирования
    existing_option_photos_json = json.dumps(existing_option_photos, ensure_ascii=False)
    print(f"DEBUG: existing_option_photos_json = {existing_option_photos_json}")
    
    try:
        current_app.logger.info('[Product GET] product_id=%s variations=%s', product.id, list(product_variations.keys()) if isinstance(product_variations, dict) else 'n/a')
        if isinstance(product_variations, dict):
            for v in product_variations.values():
                current_app.logger.info('[Product GET] var id=%s option_value_ids=%s combo_ids=%s', v.get('id'), v.get('option_value_ids'), v.get('combo_ids'))
    except Exception:
        pass

    # Загружаем связанные товары для отображения в форме
    related_products = []
    if product:
        from ..models.product import RelatedProduct
        related_products_raw = RelatedProduct.query.filter_by(product_id=product.id).order_by(RelatedProduct.sort_order).all()
        # Преобразуем в словари для JSON сериализации
        related_products = []
        for related in related_products_raw:
            related_products.append({
                'id': related.id,
                'product_id': related.product_id,
                'related_product_id': related.related_product_id,
                'link_text': related.link_text,
                'sort_order': related.sort_order
            })

    # Загружаем все товары для выпадающего списка
    all_products = Product.query.order_by(Product.name).all()
    print(f"DEBUG: Загружено товаров для выпадающего списка: {len(all_products)}")
    for p in all_products:
        print(f"DEBUG: Товар ID={p.id}, название='{p.name}'")
    
    return render_template(
        'admin/product_form.html',
        form=form,
        product=product,
        options=options,
        product_options=product_options,
        product_variations=product_variations,
        existing_option_form=existing_option_form,
        img_form=img_form,
        dir_form=dir_form,
        existing_option_photos_json=existing_option_photos_json,
        size_charts=SizeChart.query.order_by(SizeChart.id.desc()).all(),
        all_products=all_products,
        related_products=related_products
    )


@admin_bp.route('/products', methods=['GET', 'POST'])
@admin_required
def list_products():
    # Обработка массовых операций
    if request.method == 'POST':
        action = request.form.get('action')
        selected_ids = request.form.getlist('selected_ids', type=int)
        
        if action == 'delete_selected' and selected_ids:
            deleted_count = 0
            for product_id in selected_ids:
                try:
                    product = Product.query.get(product_id)
                    if product:
                        # Удаляем товар напрямую, используя логику из delete_product
                        from ..models.productAttribute import ProductAttribute
                        from ..models.productOptions import ProductVariation, ProductVariationOptionValue, product_option_association, product_option_value_association
                        from ..models.cart import CartItem
                        from ..models.review import Review
                        from ..models.favorite import Favorite
                        from ..models.order import OrderItem
                        from ..models.comparison import ComparisonItem
                        from ..models.wishlist import WishlistItem
                        from ..models.size_chart import ProductSizeChart
                        
                        # Удаляем связанные записи в правильном порядке
                        ProductAttribute.query.filter_by(product_id=product_id).delete()
                        
                        variation_ids = [v.id for v in ProductVariation.query.filter_by(product_id=product_id).all()]
                        if variation_ids:
                            ProductVariationOptionValue.query.filter(ProductVariationOptionValue.variation_id.in_(variation_ids)).delete(synchronize_session=False)
                        
                        ProductVariation.query.filter_by(product_id=product_id).delete()
                        
                        db.session.execute(product_option_association.delete().where(product_option_association.c.product_id == product_id))
                        db.session.execute(product_option_value_association.delete().where(product_option_value_association.c.product_id == product_id))
                        db.session.execute(product_images.delete().where(product_images.c.product_id == product_id))
                        
                        CartItem.query.filter_by(product_id=product_id).delete()
                        Review.query.filter_by(product_id=product_id).delete()
                        Favorite.query.filter_by(product_id=product_id).delete()
                        OrderItem.query.filter_by(product_id=product_id).delete()
                        ComparisonItem.query.filter_by(product_id=product_id).delete()
                        WishlistItem.query.filter_by(product_id=product_id).delete()
                        ProductSizeChart.query.filter_by(product_id=product_id).delete()
                        
                        # Удаляем связанные товары
                        from ..models.product import RelatedProduct
                        RelatedProduct.query.filter(
                            (RelatedProduct.product_id == product_id) | 
                            (RelatedProduct.related_product_id == product_id)
                        ).delete()
                        
                        db.session.delete(product)
                        deleted_count += 1
                        
                except Exception as e:
                    print(f"Ошибка удаления товара {product_id}: {e}")
            
            try:
                db.session.commit()
                flash(f"Удалено {deleted_count} товаров из {len(selected_ids)} выбранных.", "success")
            except Exception as e:
                db.session.rollback()
                flash(f"Ошибка при массовом удалении: {e}", "danger")
            
        elif action == 'toggle_index_selected' and selected_ids:
            updated_count = 0
            for product_id in selected_ids:
                try:
                    product = Product.query.get(product_id)
                    if product:
                        product.is_indexed = not product.is_indexed
                        updated_count += 1
                except Exception as e:
                    print(f"Ошибка обновления товара {product_id}: {e}")
            
            try:
                db.session.commit()
                flash(f"Флаг 'Индексировать' переключён для {updated_count} товаров.", "success")
            except Exception as e:
                db.session.rollback()
                flash(f"Ошибка сохранения изменений: {e}", "danger")
        
        return redirect(url_for('admin.list_products'))

    # GET запрос - отображение списка
    query = Product.query

    # Поиск по названию
    search = request.args.get('search', '').strip()
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))

    # Фильтр по категории (включая подкатегории)
    category_id = request.args.get('category', type=int)
    if category_id:
        # Получаем все ID категорий в поддереве
        def get_category_tree_ids(cat_id):
            """Рекурсивно получает все ID категорий в поддереве"""
            ids = [cat_id]
            children = Category.query.filter_by(parent_id=cat_id).all()
            for child in children:
                ids.extend(get_category_tree_ids(child.id))
            return ids
        
        category_ids = get_category_tree_ids(category_id)
        query = query.filter(Product.category_id.in_(category_ids))

    # Сортировка
    sort = request.args.get('sort', 'name')
    if sort == 'name':
        query = query.order_by(Product.name.asc())
    elif sort == 'price':
        query = query.order_by(Product.price.asc())
    elif sort == 'stock':
        query = query.order_by(Product.stock.asc())

    # Пагинация
    page = request.args.get('page', 1, type=int)
    per_page = 10
    products = query.paginate(page=page, per_page=per_page)

    # Список категорий для фильтрации (с иерархией)
    from ..models.category import build_category_list
    categories_with_levels = build_category_list()

    return render_template(
        'admin/products_list.html',
        products=products,
        categories_with_levels=categories_with_levels,
        search=search,
        category_id=category_id,
        sort=sort
    )


# -------------------- Size Charts CRUD --------------------
@admin_bp.route('/size-charts')
@admin_required
def size_charts_list():
    page = request.args.get('page', 1, type=int)
    charts = SizeChart.query.order_by(SizeChart.id.desc()).paginate(page=page, per_page=20)
    return render_template('admin/size_charts/list.html', charts=charts)


@admin_bp.route('/size-charts/create', methods=['GET', 'POST'])
@admin_bp.route('/size-charts/<int:chart_id>/edit', methods=['GET', 'POST'])
@admin_required
def size_charts_form(chart_id=None):
    chart = SizeChart.query.get(chart_id) if chart_id else None
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        image_id = request.form.get('image_id', type=int)
        table_json_raw = request.form.get('table_json', '').strip()
        current_app.logger.info('[SizeCharts] POST received: title="%s", image_id=%s, desc_len=%s, table_json_len=%s',
                                title, image_id, len(description) if description else 0, len(table_json_raw) if table_json_raw else 0)
        try:
            table_json = json.loads(table_json_raw) if table_json_raw else None
        except Exception:
            table_json = None
        current_app.logger.info('[SizeCharts] Parsed table_json: %s', 'ok' if table_json is not None else 'None')

        if not title:
            flash('Введите заголовок', 'warning')
            return render_template('admin/size_charts/form.html', chart=chart)

        if chart is None:
            chart = SizeChart(title=title, description=description, image_id=image_id, table_json=table_json)
            db.session.add(chart)
        else:
            chart.title = title
            chart.description = description
            chart.image_id = image_id
            chart.table_json = table_json

        try:
            db.session.commit()
            current_app.logger.info('[SizeCharts] Saved chart id=%s', chart.id)
            flash('Размерная сетка сохранена', 'success')
            return redirect(url_for('admin.size_charts_list'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception('Ошибка сохранения размерной сетки')
            flash(f'Ошибка сохранения: {e}', 'danger')

    return render_template('admin/size_charts/form.html', chart=chart)


@admin_bp.route('/size-charts/<int:chart_id>/delete', methods=['POST'])
@admin_required
def size_charts_delete(chart_id):
    chart = SizeChart.query.get_or_404(chart_id)
    try:
        ProductSizeChart.query.filter_by(size_chart_id=chart.id).delete()
        db.session.delete(chart)
        db.session.commit()
        flash('Размерная сетка удалена', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка удаления: {e}', 'danger')
    return redirect(url_for('admin.size_charts_list'))


@admin_bp.route('/reviews')
@admin_required
def reviews_list():
    page = request.args.get('page', 1, type=int)
    reviews = Review.query.order_by(Review.created_at.desc()).paginate(page=page, per_page=20)
    return render_template('admin/reviews_list.html', reviews=reviews)


@admin_bp.route('/reviews/create', methods=['GET', 'POST'])
@admin_bp.route('/reviews/<int:review_id>/edit', methods=['GET', 'POST'])
@admin_required
def review_form(review_id=None):
    review = Review.query.get(review_id) if review_id else None
    if request.method == 'POST':
        product_id = request.form.get('product_id', type=int)
        customer_id = request.form.get('customer_id', type=int)
        rating = request.form.get('rating', type=int)
        sizing_score = request.form.get('sizing_score', type=int)
        quality_score = request.form.get('quality_score', type=int)
        comfort_score = request.form.get('comfort_score', type=int)
        comment = request.form.get('comment', '').strip()
        approved = True if request.form.get('approved') == 'on' else False
        guest_name = request.form.get('guest_name', '').strip()
        guest_email = request.form.get('guest_email', '').strip()

        if review is None:
            review = Review(
                product_id=product_id,
                customer_id=customer_id,
                rating=rating or 0,
                sizing_score=sizing_score,
                quality_score=quality_score,
                comfort_score=comfort_score,
                comment=comment,
                approved=approved,
                guest_name=guest_name or None,
                guest_email=guest_email or None,
            )
            db.session.add(review)
        else:
            review.product_id = product_id
            review.customer_id = customer_id
            review.rating = rating or 0
            review.sizing_score = sizing_score
            review.quality_score = quality_score
            review.comfort_score = comfort_score
            review.comment = comment
            review.approved = approved
            review.guest_name = guest_name or None
            review.guest_email = guest_email or None

        try:
            db.session.commit()
            flash('Отзыв сохранён', 'success')
            return redirect(url_for('admin.reviews_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка сохранения: {e}', 'danger')

    products = Product.query.order_by(Product.name.asc()).all()
    customers = Customer.query.order_by(Customer.id.desc()).all()
    return render_template('admin/review_form.html', review=review, products=products, customers=customers)


@admin_bp.route('/reviews/<int:review_id>/approve', methods=['POST'])
@admin_required
def review_approve(review_id):
    review = Review.query.get_or_404(review_id)
    review.approved = True
    db.session.commit()
    flash('Отзыв одобрен', 'success')
    return redirect(url_for('admin.reviews_list'))


@admin_bp.route('/reviews/<int:review_id>/delete', methods=['POST'])
@admin_required
def review_delete(review_id):
    review = Review.query.get_or_404(review_id)
    db.session.delete(review)
    db.session.commit()
    flash('Отзыв удалён', 'success')
    return redirect(url_for('admin.reviews_list'))

@admin_bp.route('/products/delete/<int:product_id>', methods=['POST'])
@admin_required
def delete_product(product_id):
    try:
        print(f"=== НАЧАЛО УДАЛЕНИЯ ТОВАРА {product_id} ===")
        product = Product.query.get_or_404(product_id)
        print(f"Товар найден: {product.name}")
        
        # Импортируем все необходимые модели
        from ..models.productAttribute import ProductAttribute
        from ..models.productOptions import ProductVariation, ProductVariationOptionValue, product_option_association, product_option_value_association
        from ..models.cart import CartItem
        from ..models.review import Review
        from ..models.favorite import Favorite
        from ..models.order import OrderItem
        from ..models.comparison import ComparisonItem
        from ..models.wishlist import WishlistItem
        from ..models.size_chart import ProductSizeChart
        
        # Удаляем связанные записи в правильном порядке
        
        # 1. Удаляем записи из product_attributes
        print("1. Удаляем product_attributes...")
        deleted_attrs = ProductAttribute.query.filter_by(product_id=product_id).delete()
        print(f"   Удалено записей из product_attributes: {deleted_attrs}")
        
        # 2. Удаляем связи вариаций с опциями
        print("2. Удаляем product_variation_option_values...")
        # Сначала получаем ID вариаций для этого товара
        variation_ids = [v.id for v in ProductVariation.query.filter_by(product_id=product_id).all()]
        print(f"   Найдено вариаций: {len(variation_ids)}")
        
        if variation_ids:
            deleted_pvov = ProductVariationOptionValue.query.filter(ProductVariationOptionValue.variation_id.in_(variation_ids)).delete(synchronize_session=False)
            print(f"   Удалено записей из product_variation_option_values: {deleted_pvov}")
        else:
            print("   Нет вариаций для удаления")
        
        # 3. Удаляем вариации товара
        print("3. Удаляем product_variations...")
        deleted_vars = ProductVariation.query.filter_by(product_id=product_id).delete()
        print(f"   Удалено записей из product_variations: {deleted_vars}")
        
        # 4. Удаляем связи с опциями товара
        print("4. Удаляем связи с опциями товара...")
        result1 = db.session.execute(product_option_association.delete().where(product_option_association.c.product_id == product_id))
        result2 = db.session.execute(product_option_value_association.delete().where(product_option_value_association.c.product_id == product_id))
        print(f"   Удалено записей из product_option_association: {result1.rowcount}")
        print(f"   Удалено записей из product_option_value_association: {result2.rowcount}")
        
        # 5. Удаляем связи с изображениями
        print("5. Удаляем связи с изображениями...")
        result3 = db.session.execute(product_images.delete().where(product_images.c.product_id == product_id))
        print(f"   Удалено записей из product_images: {result3.rowcount}")
        
        # 6. Удаляем товар из корзины
        print("6. Удаляем товар из корзины...")
        deleted_cart = CartItem.query.filter_by(product_id=product_id).delete()
        print(f"   Удалено записей из cart_items: {deleted_cart}")
        
        # 7. Удаляем отзывы товара
        print("7. Удаляем отзывы товара...")
        deleted_reviews = Review.query.filter_by(product_id=product_id).delete()
        print(f"   Удалено записей из reviews: {deleted_reviews}")
        
        # 8. Удаляем товар из избранного
        print("8. Удаляем товар из избранного...")
        deleted_favs = Favorite.query.filter_by(product_id=product_id).delete()
        print(f"   Удалено записей из favorites: {deleted_favs}")
        
        # 9. Удаляем товар из заказов (OrderItem)
        print("9. Удаляем товар из заказов...")
        deleted_orders = OrderItem.query.filter_by(product_id=product_id).delete()
        print(f"   Удалено записей из order_items: {deleted_orders}")
        
        # 10. Удаляем товар из сравнения
        print("10. Удаляем товар из сравнения...")
        deleted_comp = ComparisonItem.query.filter_by(product_id=product_id).delete()
        print(f"   Удалено записей из comparison_items: {deleted_comp}")
        
        # 11. Удаляем товар из wishlist
        print("11. Удаляем товар из wishlist...")
        deleted_wish = WishlistItem.query.filter_by(product_id=product_id).delete()
        print(f"   Удалено записей из wishlist_items: {deleted_wish}")
        
        # 12. Удаляем связи с таблицами размеров
        print("12. Удаляем связи с таблицами размеров...")
        deleted_size_chart = ProductSizeChart.query.filter_by(product_id=product_id).delete()
        print(f"   Удалено записей из product_size_chart: {deleted_size_chart}")
        
        # 13. Удаляем связанные товары
        print("13. Удаляем связанные товары...")
        from ..models.product import RelatedProduct
        deleted_related = RelatedProduct.query.filter(
            (RelatedProduct.product_id == product_id) | 
            (RelatedProduct.related_product_id == product_id)
        ).delete()
        print(f"   Удалено записей из related_products: {deleted_related}")
        
        # 14. Наконец удаляем сам товар
        print("14. Удаляем сам товар...")
        db.session.delete(product)
        
        print("15. Коммитим изменения...")
        db.session.commit()
        print("=== УДАЛЕНИЕ ТОВАРА {product_id} ЗАВЕРШЕНО УСПЕШНО ===")
        flash("Товар удалён", "success")
        
    except IntegrityError as e:
        db.session.rollback()
        print(f"❌ IntegrityError при удалении товара {product_id}: {e}")
        print(f"❌ Детали ошибки: {type(e).__name__}: {str(e)}")
        flash(f"Ошибка целостности данных при удалении товара: {str(e)}", "danger")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Неожиданная ошибка при удалении товара {product_id}: {e}")
        print(f"❌ Тип ошибки: {type(e).__name__}")
        print(f"❌ Детали ошибки: {str(e)}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        flash(f"Неожиданная ошибка при удалении товара: {str(e)}", "danger")
    
    return redirect(url_for('admin.list_products'))


@admin_bp.route('/products/copy', methods=['POST'])
@admin_required
def copy_product():
    """Копирование товара с добавлением числа к имени"""
    try:
        data = request.get_json()
        product_id = data.get('product_id')
        
        if not product_id:
            return jsonify({'success': False, 'error': 'ID товара не указан'})
        
        # Получаем оригинальный товар
        original_product = Product.query.get_or_404(product_id)
        
        # Генерируем уникальное имя для копии
        base_name = original_product.name
        counter = 1
        new_name = f"{base_name} (копия {counter})"
        
        # Проверяем, не существует ли уже товар с таким именем
        while Product.query.filter_by(name=new_name).first():
            counter += 1
            new_name = f"{base_name} (копия {counter})"
        
        # Создаем копию товара
        copied_product = Product(
            name=new_name,
            description=original_product.description,
            price=original_product.price,
            stock=original_product.stock,
            bonus_points=original_product.bonus_points,
            category_id=original_product.category_id,
            main_image_id=original_product.main_image_id,
            qr_code_path=original_product.qr_code_path,
            barcode=original_product.barcode,
            is_indexed=original_product.is_indexed,
            sort_order=original_product.sort_order,
            slug=original_product.slug + f"-copy-{counter}" if original_product.slug else f"copy-{counter}",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.session.add(copied_product)
        db.session.flush()  # Получаем ID нового товара
        
        # Копируем атрибуты товара
        from ..models.productAttribute import ProductAttribute
        original_attributes = ProductAttribute.query.filter_by(product_id=product_id).all()
        for attr in original_attributes:
            copied_attr = ProductAttribute(
                product_id=copied_product.id,
                attribute_value_id=attr.attribute_value_id
            )
            db.session.add(copied_attr)
        
        # Копируем связи с опциями товара через промежуточную таблицу
        from ..models.productOptions import product_option_association, product_option_value_association
        
        # Получаем все опции, связанные с оригинальным товаром
        original_option_links = db.session.execute(
            product_option_association.select().where(product_option_association.c.product_id == product_id)
        ).fetchall()
        
        # Копируем связи с опциями
        for option_link in original_option_links:
            db.session.execute(
                product_option_association.insert().values(
                    product_id=copied_product.id,
                    option_id=option_link.option_id
                )
            )
        
        # Получаем все значения опций, связанные с оригинальным товаром
        original_option_value_links = db.session.execute(
            product_option_value_association.select().where(product_option_value_association.c.product_id == product_id)
        ).fetchall()
        
        # Копируем связи со значениями опций
        for option_value_link in original_option_value_links:
            db.session.execute(
                product_option_value_association.insert().values(
                    product_id=copied_product.id,
                    option_value_id=option_value_link.option_value_id
                )
            )
        
        # Копируем связи с изображениями
        original_images = db.session.execute(
            product_images.select().where(product_images.c.product_id == product_id)
        ).fetchall()
        
        for img in original_images:
            db.session.execute(
                product_images.insert().values(
                    product_id=copied_product.id,
                    image_id=img.image_id,
                    order=img.order
                )
            )
        
        # Копируем связи с таблицами размеров
        from ..models.size_chart import ProductSizeChart
        original_size_charts = ProductSizeChart.query.filter_by(product_id=product_id).all()
        for size_chart in original_size_charts:
            copied_size_chart = ProductSizeChart(
                product_id=copied_product.id,
                size_chart_id=size_chart.size_chart_id
            )
            db.session.add(copied_size_chart)
        
        # Копируем связанные товары
        from ..models.product import RelatedProduct
        original_related = RelatedProduct.query.filter_by(product_id=product_id).all()
        for related in original_related:
            copied_related = RelatedProduct(
                product_id=copied_product.id,
                related_product_id=related.related_product_id,
                link_text=related.link_text,
                sort_order=related.sort_order
            )
            db.session.add(copied_related)
        
        # Копируем SEO настройки
        from ..models.seo_settings import SEOSettings
        original_seo = SEOSettings.query.filter_by(page_type='product', page_id=product_id).first()
        if original_seo:
            # Генерируем уникальный slug для SEO
            base_seo_slug = copied_product.slug
            seo_slug = base_seo_slug
            counter = 1
            while SEOSettings.query.filter_by(slug=seo_slug).first():
                seo_slug = f"{base_seo_slug}-seo-{counter}"
                counter += 1
            
            copied_seo = SEOSettings(
                page_type='product',
                page_id=copied_product.id,
                meta_title=original_seo.meta_title,
                meta_description=original_seo.meta_description,
                meta_keywords=original_seo.meta_keywords,
                slug=seo_slug
            )
            db.session.add(copied_seo)
        
        # Копируем вариации товара
        from ..models.productOptions import ProductVariation, ProductVariationOptionValue
        original_variations = ProductVariation.query.filter_by(product_id=product_id).all()
        
        for original_var in original_variations:
            # Генерируем уникальный slug для вариации
            base_var_slug = original_var.slug
            var_slug = base_var_slug
            counter = 1
            while ProductVariation.query.filter_by(slug=var_slug).first():
                var_slug = f"{base_var_slug}-copy-{counter}"
                counter += 1
            
            # Создаем новую вариацию
            copied_variation = ProductVariation(
                product_id=copied_product.id,
                sku=original_var.sku,
                price=original_var.price,
                stock=original_var.stock,
                slug=var_slug,
                seo_title=original_var.seo_title,
                seo_keys=original_var.seo_keys,
                seo_description=original_var.seo_description,
                image_id=original_var.image_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.session.add(copied_variation)
            db.session.flush()  # Получаем ID новой вариации
            
            # Копируем связи с значениями опций
            original_option_values = ProductVariationOptionValue.query.filter_by(variation_id=original_var.id).all()
            for option_value in original_option_values:
                copied_option_value = ProductVariationOptionValue(
                    variation_id=copied_variation.id,
                    option_value_id=option_value.option_value_id,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.session.add(copied_option_value)
        
        db.session.commit()
        
        print(f"Товар {original_product.name} успешно скопирован как {new_name}")
        
        return jsonify({
            'success': True,
            'copied_name': new_name,
            'message': f'Товар успешно скопирован как "{new_name}"'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Ошибка при копировании товара: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })


@admin_bp.route('/get_option_values', methods=['POST'])
@admin_required
def get_option_values():
    option_id = request.form.get('option_id')
    print("Selected Option ID:", option_id)

    if not option_id:
        return jsonify([]), 400  # Если option_id не передан, возвращаем пустой список с кодом ошибки

    try:
        option_id = int(option_id)  # Преобразуем option_id к типу int
    except ValueError:
        return jsonify([]), 400  # Если option_id не является числом, возвращаем пустой список с кодом ошибки

    option_values = ProductOptionValue.query.filter_by(option_id=option_id).all()
    values = [{'id': value.id, 'value': value.value} for value in option_values]
    return jsonify(values)


@admin_bp.route('/site-settings', methods=['GET', 'POST'])
@admin_required
def site_settings():
    settings = SiteSettings.query.first()
    if not settings:
        settings = SiteSettings()  # еще не добавляем в db.session — только в POST

    pages = Page.query.all()
    form = SiteSettingsForm()

    img_form = ImageUploadForm()
    dir_form = DirectoryForm()

    if request.method == 'GET':
        form.title.data = settings.title
        form.address.data = settings.address
        form.email.data = settings.email
        form.phone.data = settings.phone
        form.owner.data = settings.owner
        form.working_hours.data = settings.working_hours
        form.additional_info.data = settings.additional_info
        form.map_locations.data = settings.map_locations

        if settings.home_page_id:
            form.home_page_id.data = Page.query.filter_by(id=settings.home_page_id).first()

        if settings.logo_id:
            form.image_id.data = str(settings.logo_id)
        else:
            form.image_id.data = ''

        while len(form.social_links.entries) > 0:
            form.social_links.pop_entry()

        existing_links = SocialLink.query.filter_by(site_settings_id=settings.id).all() if settings.id else []
        for link_obj in existing_links:
            entry = form.social_links.append_entry()
            entry.platform.data = link_obj.platform
            entry.url.data = link_obj.url
            if link_obj.icon_id:
                entry.icon_id.data = str(link_obj.icon_id)
                entry.icon.data = link_obj.icon.filename
            else:
                entry.icon_id.data = ''
        
        # Добавляем пустую ссылку если нет ни одной (min_entries=1)
        if len(form.social_links.entries) == 0:
            form.social_links.append_entry()

    if request.method == 'POST' and form.validate_on_submit():
        settings.title = form.title.data
        settings.address = form.address.data
        settings.email = form.email.data
        settings.phone = form.phone.data
        settings.owner = form.owner.data
        settings.working_hours = form.working_hours.data
        settings.additional_info = form.additional_info.data
        settings.map_locations = form.map_locations.data

        home_pid = form.home_page_id.data
        settings.home_page_id = int(home_pid.id) if home_pid else None

        logo_id_str = form.image_id.data
        if logo_id_str and logo_id_str.isdigit():
            settings.logo_id = int(logo_id_str)
        else:
            settings.logo_id = None

        if not settings.id:
            db.session.add(settings)
            db.session.flush()

        # Удаляем старые социальные ссылки
        SocialLink.query.filter_by(site_settings_id=settings.id).delete()
        
        # Обрабатываем социальные ссылки из формы
        for subform in form.social_links.entries:
            if subform.platform.data and subform.url.data:
                new_link = SocialLink(
                    site_settings_id=settings.id,
                    platform=subform.platform.data,
                    url=subform.url.data
                )
                if subform.icon_id.data and subform.icon_id.data.isdigit():
                    new_link.icon_id = int(subform.icon_id.data)
                db.session.add(new_link)
        
        # Обрабатываем дополнительные социальные ссылки, добавленные через JavaScript
        import re
        social_data = {}
        
        for key, value in request.form.items():
            if key.startswith('social_links[') and '].platform' in key:
                # Извлекаем индекс: social_links[0].platform -> 0
                match = re.search(r'social_links\[(\d+)\]\.platform', key)
                if match:
                    index = match.group(1)
                    if index not in social_data:
                        social_data[index] = {}
                    social_data[index]['platform'] = value
            elif key.startswith('social_links[') and '].url' in key:
                # social_links[0].url -> 0
                match = re.search(r'social_links\[(\d+)\]\.url', key)
                if match:
                    index = match.group(1)
                    if index not in social_data:
                        social_data[index] = {}
                    social_data[index]['url'] = value
            elif key.startswith('social_links[') and '].icon_id' in key:
                # social_links[0].icon_id -> 0
                match = re.search(r'social_links\[(\d+)\]\.icon_id', key)
                if match:
                    index = match.group(1)
                    if index not in social_data:
                        social_data[index] = {}
                    social_data[index]['icon_id'] = value
        
        # Создаем социальные ссылки из JavaScript данных
        for index, data in social_data.items():
            if data.get('platform') and data.get('url'):
                new_link = SocialLink(
                    site_settings_id=settings.id,
                    platform=data['platform'],
                    url=data['url']
                )
                if data.get('icon_id') and data['icon_id'].isdigit():
                    new_link.icon_id = int(data['icon_id'])
                db.session.add(new_link)

        db.session.commit()
        flash("Настройки сайта сохранены!", "success")
        return redirect(url_for('admin.site_settings'))
    
    elif request.method == 'POST':
        # Если валидация не прошла, показываем ошибки
        flash("Ошибка валидации формы. Проверьте введенные данные.", "error")

    return render_template(
        'admin/site_settings.html',
        form=form,
        settings=settings,
        pages=pages,
        img_form=img_form,
        dir_form=dir_form
    )


@admin_bp.route('/media/upload', methods=['POST'])
@admin_required
def upload_media():
    """Загрузка изображений для TinyMCE"""
    try:
        from werkzeug.utils import secure_filename
        import os
        from flask import current_app
        
        if 'file' not in request.files:
            return jsonify({'error': 'Файл не выбран'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Файл не выбран'}), 400
            
        # Проверяем расширение
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}
        if '.' not in file.filename or \
           file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
            return jsonify({'error': 'Недопустимый формат изображения'}), 400
            
        # Создаем директорию если её нет
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'app/static/uploads')
        os.makedirs(upload_folder, exist_ok=True)
        
        # Генерируем безопасное имя файла
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{timestamp}{ext}"
        
        # Сохраняем файл
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)
        
        # Создаем запись в БД
        from ..models.image import Image
        
        image = Image(
            filename=filename,
            alt=name
        )
        db.session.add(image)
        db.session.commit()
        
        return jsonify({
            'location': f'/static/uploads/{filename}'
        })
    except Exception as e:
        print(f"Ошибка загрузки изображения: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/media/list', methods=['GET'])
@admin_required
def list_media():
    """Получение списка изображений для TinyMCE"""
    try:
        from ..models.image import Image
        from ..models.directory import Directory
        import os
        
        # Получаем текущий каталог
        current_directory_id = request.args.get('directory_id', type=int)
        
        # Получаем все каталоги для навигации
        directories = Directory.query.all()
        
        # Получаем изображения с фильтрацией по каталогу
        if current_directory_id:
            images = Image.query.filter_by(directory_id=current_directory_id).all()
        else:
            images = Image.query.filter_by(directory_id=None).all()
        
        # Фильтруем только изображения
        image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg']
        image_files = []
        
        for image in images:
            if any(image.filename.lower().endswith(ext) for ext in image_extensions):
                file_path = os.path.join('app/static/uploads', image.filename)
                if os.path.exists(file_path):
                    image_files.append({
                        'id': image.id,
                        'filename': image.filename,
                        'url': f'/static/uploads/{image.filename}',
                        'alt': image.alt or image.filename,
                        'directory_id': image.directory_id
                    })
        
        if request.args.get('format') == 'json':
            return jsonify({
                'images': image_files,
                'directories': [{'id': d.id, 'name': d.name, 'parent_id': d.parent_id} for d in directories],
                'current_directory_id': current_directory_id
            })
        
        return render_template('admin/media_list.html', 
                             images=image_files, 
                             directories=directories,
                             current_directory_id=current_directory_id)
        
    except Exception as e:
        print(f"Ошибка получения списка изображений: {str(e)}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/media/upload/video', methods=['POST'])
@login_required
def upload_video():
    """Загрузка видео файлов"""
    try:
        from werkzeug.utils import secure_filename
        import os
        from flask import current_app
        
        print("Загрузка видео - начало")
        print("Files:", request.files)
        
        if 'video' not in request.files:
            return jsonify({'success': False, 'message': 'Видео не выбрано'}), 400
            
        video_file = request.files['video']
        if video_file.filename == '':
            return jsonify({'success': False, 'message': 'Видео не выбрано'}), 400
            
        # Проверяем расширение
        allowed_extensions = {'mp4', 'webm', 'ogg', 'avi', 'mov'}
        if '.' not in video_file.filename or \
           video_file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
            return jsonify({'success': False, 'message': 'Недопустимый формат видео'}), 400
            
        # Создаем директорию для видео если её нет
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'app/static/uploads')
        video_dir = os.path.join(upload_folder, 'videos')
        os.makedirs(video_dir, exist_ok=True)
        
        print(f"Video dir: {video_dir}")
        
        # Генерируем безопасное имя файла
        filename = secure_filename(video_file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{timestamp}{ext}"
        
        # Сохраняем файл
        filepath = os.path.join(video_dir, filename)
        print(f"Saving to: {filepath}")
        video_file.save(filepath)
        
        # Создаем запись в БД
        from ..models.image import Image
        from ..extensions import db
        
        # Получаем directory_id из формы, если не указан - используем None
        directory_id = request.form.get('directory_id')
        if directory_id:
            directory_id = int(directory_id)
        else:
            directory_id = None
        
        video = Image(
            filename=filename,
            alt='Видео',
            directory_id=directory_id
        )
        db.session.add(video)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'video': {
                'id': video.id,
                'url': f'/static/uploads/videos/{filename}',
                'filename': filename
            }
        })
    except Exception as e:
        print(f"Ошибка загрузки видео: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/media/list/videos', methods=['GET'])
@login_required  
def list_videos():
    """Получение списка видео"""
    from ..models.image import Image
    import os

    video_extensions = ['.mp4', '.webm', '.ogg', '.avi', '.mov']
    videos = []

    all_files = Image.query.all()
    for file in all_files:
        if any(file.filename.lower().endswith(ext) for ext in video_extensions):
            video_path = os.path.join('app/static/uploads/videos', file.filename)
            if os.path.exists(video_path):
                videos.append({
                    'id': file.id,
                    'filename': file.filename,
                    'url': f'/static/uploads/videos/{file.filename}',
                    'alt': file.alt or 'Видео'
                })

    return jsonify({'success': True, 'videos': videos})


@admin_bp.route('/create_subcategories_menu_items', methods=['POST'])
@login_required
def create_subcategories_menu_items():
    """Создание подпунктов меню из подкатегорий"""
    try:
        from ..admin.modules.menu import MenuModule
        from flask import jsonify
        
        print("=== СОЗДАНИЕ ПОДПУНКТОВ МЕНЮ ===")
        print("Form data:", request.form)
        
        category_id = request.form.get('category_id')
        menu_instance_id = request.form.get('menu_instance_id')
        parent_menu_item_id = request.form.get('parent_menu_item_id')
        
        print(f"category_id: {category_id}")
        print(f"menu_instance_id: {menu_instance_id}")
        print(f"parent_menu_item_id: {parent_menu_item_id}")
        
        if not category_id or not menu_instance_id:
            error_msg = f'Не указаны обязательные параметры. category_id: {category_id}, menu_instance_id: {menu_instance_id}'
            print(f"Ошибка: {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 400
        
        # Создаем подпункты меню
        created_items = MenuModule.create_subcategories_menu_items(
            int(category_id),
            int(menu_instance_id),
            int(parent_menu_item_id) if parent_menu_item_id else None
        )
        
        print(f"Создано {len(created_items)} подпунктов")
        
        return jsonify({
            'success': True,
            'created_items': created_items,
            'message': f'Создано {len(created_items)} подпунктов меню'
        })
        
    except Exception as e:
        print(f"Ошибка при создании подпунктов меню: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

