import json
import os
from flask import request, jsonify, render_template, flash, redirect, url_for
from .forms import ImageUploadForm, DirectoryForm, slugify, PostCategoryForm, PostForm
from . import admin_bp
from .decorators import admin_required
from .utils import save_image_file
from ..models.post_category import PostCategory
from ..extensions import db
from ..models.post import Post, PostLayout
from ..models.module import *
from .forms import PostCategoryForm


@admin_bp.route('/post_categories', methods=['GET', 'POST'])
@admin_required
def admin_post_categories():
    """
    Список категорий постов, включая массовые действия.
    """
    form = PostCategoryForm()  # Создаем пустую форму

    if request.method == 'POST':
        action = request.form.get('action')
        selected_ids = request.form.getlist('selected_ids', type=int)
        if action == 'delete_selected':
            deleted_count = 0
            for cid in selected_ids:
                try:
                    cat = PostCategory.query.get(cid)
                    if cat:
                        print(f"Удаляем категорию постов: {cat.name} (ID: {cat.id})")
                        
                        # Получаем все посты в этой категории (включая подкатегории)
                        def get_all_posts_in_category(cat_id):
                            """Рекурсивно получает все посты в категории и её подкатегориях"""
                            posts = []
                            
                            # Посты в текущей категории
                            category_posts = Post.query.filter_by(category_id=cat_id).all()
                            posts.extend(category_posts)
                            
                            # Подкатегории
                            subcategories = PostCategory.query.filter_by(parent_id=cat_id).all()
                            for subcat in subcategories:
                                posts.extend(get_all_posts_in_category(subcat.id))
                            
                            return posts
                        
                        all_posts = get_all_posts_in_category(cat.id)
                        print(f"Найдено постов для удаления: {len(all_posts)}")
                        
                        # Удаляем все посты в категории
                        for post in all_posts:
                            print(f"Удаляем пост: {post.title} (ID: {post.id})")
                            # Удаляем связанные записи поста
                            PostLayout.query.filter_by(post_id=post.id).delete()
                            db.session.delete(post)
                        
                        # Удаляем саму категорию
                        db.session.delete(cat)
                        deleted_count += 1
                        
                except Exception as e:
                    print(f"Ошибка удаления категории постов {cid}: {e}")
            
            try:
                db.session.commit()
                flash(f"Удалено {deleted_count} категорий постов и все посты в них.", "success")
            except Exception as e:
                db.session.rollback()
                flash(f"Ошибка при массовом удалении категорий постов: {e}", "danger")
        elif action == 'toggle_index_selected':
            for cid in selected_ids:
                cat = PostCategory.query.get(cid)
                if cat:
                    cat.is_indexed = not cat.is_indexed
            db.session.commit()
            flash(f"Флаг 'Индексировать' переключён для {len(selected_ids)} категорий.", "success")

        return redirect(url_for('admin.admin_post_categories'))

    # GET
    cat_list = PostCategory.query.all()  # Получаем все категории постов из базы данных
    return render_template('admin/post_categories_list.html', cat_list=cat_list, form=form)  # Передаем форму в шаблон


from flask import request
from werkzeug.utils import secure_filename
import os


@admin_bp.route('/post_categories/form', defaults={'category_id': None}, methods=['GET', 'POST'])
@admin_bp.route('/post_categories/form/<int:category_id>', methods=['GET', 'POST'])
@admin_required
def admin_post_categories_form(category_id):
    # Если редактируем существующую категорию
    if category_id:
        category = PostCategory.query.get_or_404(category_id)
    else:
        category = None

    form = PostCategoryForm(obj=category)

    # Дополнительные формы (модалки)
    img_form = ImageUploadForm()
    dir_form = DirectoryForm()

    if request.method == 'POST':
        if category_id:
            form.process_slug(category_id)
        else:
            form.process_slug()

        if not category:
            category = PostCategory()

        category.name = form.name.data
        # Автоматически генерируем slug на латинице, если не указан
        if not form.slug.data:
            from .forms import generate_unique_slug
            base_slug = slugify(form.name.data)
            if not base_slug:
                base_slug = 'post-category'
            category.slug = generate_unique_slug(base_slug)
        else:
            category.slug = form.slug.data
        category.sort_order = form.sort_order.data
        category.is_indexed = form.is_indexed.data
        category.description = form.description.data
        category.meta_title = form.meta_title.data
        category.meta_description = form.meta_description.data
        category.meta_keywords = form.meta_keywords.data

        print(2, form.image_id)
        if form.image_id.data:
            print(1, form.image_id.data, form.description.data)
            category.image_id = form.image_id.data  # Сохраняем путь к изображению в поле image
        else:
            category.image = None

        if form.parent.data and hasattr(form.parent.data, 'id'):
            category.parent_id = form.parent.data.id
        else:
            category.parent_id = None

        db.session.add(category)
        db.session.commit()

        flash('Категория успешно сохранена!', 'success')
        return redirect(url_for('admin.admin_post_categories'))

    return render_template(
        'admin/post_category_form.html',
        form=form,
        category=category,
        img_form=img_form,
        dir_form=dir_form,
    )


@admin_bp.route('/post_categories/<int:category_id>/delete', methods=['POST'])
@admin_required
def admin_post_categories_delete(category_id):
    try:
        print(f"=== НАЧАЛО УДАЛЕНИЯ КАТЕГОРИИ ПОСТОВ {category_id} ===")
        category = PostCategory.query.get_or_404(category_id)
        print(f"Категория постов найдена: {category.name}")
        
        # Получаем все посты в этой категории (включая подкатегории)
        def get_all_posts_in_category(cat_id):
            """Рекурсивно получает все посты в категории и её подкатегориях"""
            posts = []
            
            # Посты в текущей категории
            category_posts = Post.query.filter_by(category_id=cat_id).all()
            posts.extend(category_posts)
            
            # Подкатегории
            subcategories = PostCategory.query.filter_by(parent_id=cat_id).all()
            for subcat in subcategories:
                posts.extend(get_all_posts_in_category(subcat.id))
            
            return posts
        
        all_posts = get_all_posts_in_category(category_id)
        print(f"Найдено постов для удаления: {len(all_posts)}")
        
        # Удаляем все посты в категории
        for post in all_posts:
            print(f"Удаляем пост: {post.title} (ID: {post.id})")
            # Удаляем связанные записи поста
            PostLayout.query.filter_by(post_id=post.id).delete()
            db.session.delete(post)
        
        # Удаляем саму категорию
        db.session.delete(category)
        db.session.commit()
        
        print(f"=== УДАЛЕНИЕ КАТЕГОРИИ ПОСТОВ {category_id} ЗАВЕРШЕНО УСПЕШНО ===")
        flash(f'Категория постов "{category.name}" и все посты в ней успешно удалены', 'success')
        
    except Exception as e:
        print(f"❌ Ошибка при удалении категории постов {category_id}: {e}")
        db.session.rollback()
        flash(f'Ошибка при удалении категории постов: {str(e)}', 'error')
    
    return redirect(url_for('admin.admin_post_categories'))


@admin_bp.route('/posts', methods=['GET', 'POST'])
@admin_required
def admin_posts():
    """
    Список всех постов (статей) с возможностью фильтрации и поиска.
    """
    # Извлекаем параметры поиска и фильтрации
    search_query = request.args.get('search', '')
    category_filter = request.args.get('category', '')

    # Формируем запрос к базе данных
    query = Post.query

    # Применяем фильтрацию по имени (поиск)
    if search_query:
        query = query.filter(Post.title.ilike(f'%{search_query}%'))

    # Применяем фильтрацию по категории (включая подкатегории)
    if category_filter:
        # Получаем все ID категорий в поддереве
        def get_post_category_tree_ids(cat_id):
            """Рекурсивно получает все ID категорий постов в поддереве"""
            ids = [cat_id]
            children = PostCategory.query.filter_by(parent_id=cat_id).all()
            for child in children:
                ids.extend(get_post_category_tree_ids(child.id))
            return ids
        
        category_ids = get_post_category_tree_ids(int(category_filter))
        query = query.filter(Post.category_id.in_(category_ids))

    # Выполняем запрос
    posts = query.all()

    # Получаем список категорий для фильтра (с иерархией)
    def build_post_category_list(parent_id=None, level=0):
        """Возвращает список кортежей (cat, level) для категорий постов"""
        results = []
        query = PostCategory.query.filter_by(parent_id=parent_id).order_by(PostCategory.sort_order, PostCategory.id)
        for cat in query:
            results.append((cat, level))
            results.extend(build_post_category_list(cat.id, level + 1))
        return results
    
    categories_with_levels = build_post_category_list()

    return render_template('admin/posts_list.html', posts=posts, categories_with_levels=categories_with_levels, search_query=search_query,
                           category_filter=category_filter)

@admin_bp.route('/posts/form', defaults={'post_id': None}, methods=['GET', 'POST'])
@admin_bp.route('/posts/form/<int:post_id>', methods=['GET', 'POST'])
@admin_required
def admin_post_form(post_id):
    img_form = ImageUploadForm()
    dir_form = DirectoryForm()

    # Загружаем пост из базы данных, если post_id предоставлен
    if post_id:
        post = Post.query.get_or_404(post_id)
    else:
        post = None

    form = PostForm(obj=post)

    # Если форма отправлена
    if request.method == 'POST':
        if not post:
            post = Post()

        post.title = form.title.data
        post.content = form.content.data
        post.meta_title = form.meta_title.data
        post.meta_description = form.meta_description.data
        post.meta_keywords = form.meta_keywords.data
        post.is_published = form.is_published.data
        post.published_at = form.published_at.data if form.published_at.data else None
        post.slug = form.slug.data if form.slug.data else post.generate_slug()

        # Сохраняем категорию
        if form.category.data and hasattr(form.category.data, 'id'):
            post.category_id = form.category.data.id  # Передаем только ID категории
        else:
            post.category_id = None  # Если категория не выбрана

        # Сохраняем изображение
        if form.image_id.data:
            post.image_id = form.image_id.data

        db.session.add(post)
        db.session.commit()

        # Очищаем старое layout (только если пост уже существовал)
        if post_id:
            PostLayout.query.filter_by(post_id=post.id).delete()

        # Разбираем JSON с layout
        layout_json = request.form.get('layout_json', '')
        if layout_json:
            layout_data = json.loads(layout_json)
        else:
            layout_data = []

        # Сохраняем ячейки PostLayout
        for row_obj in layout_data:
            r_idx = row_obj.get('rowIndex')
            columns = row_obj.get('columns', [])
            for col_obj in columns:
                c_idx = col_obj.get('colIndex', 0)
                c_width = col_obj.get('colWidth', 3)
                mod_inst_id = col_obj.get('moduleInstanceId')

                pl = PostLayout(
                    post_id=post.id,
                    row_index=r_idx,
                    col_index=c_idx,
                    col_width=c_width,
                    module_instance_id=mod_inst_id
                )
                db.session.add(pl)

        db.session.commit()

        flash("Пост успешно сохранён!", "success")
        return redirect(url_for('admin.admin_posts'))

    # 3) Если GET -> загружаем layout для отрисовки
    if post and post.id:
        layout_cells = PostLayout.query.filter_by(post_id=post.id).order_by(PostLayout.row_index, PostLayout.col_index).all()
    else:
        layout_cells = []

    # 4) Подтягиваем модули и экземпляры
    modules = Module.query.all()
    instances = ModuleInstance.query.all()
    from collections import defaultdict
    module_instances_by_module = defaultdict(list)

    for inst in instances:
        settings_json = json.loads(inst.settings or '{}')
        inst_label = settings_json.get('name') or f"Instance #{inst.id}"
        module_instances_by_module[inst.module_id].append({
            'id': inst.id,
            'label': inst_label
        })
    dir_form = DirectoryForm()
    img_form = ImageUploadForm()
    return render_template(
        'admin/post_form.html',
        form=form,
        post=post,
        img_form=img_form,
        dir_form=dir_form,
        layout_cells=layout_cells,
        modules=modules,
        module_instances_by_module=module_instances_by_module
    )





@admin_bp.route('/posts/<int:post_id>/delete', methods=['POST'])
@admin_required
def admin_post_delete(post_id):
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    flash("Пост удалён.", "success")
    return redirect(url_for('admin.admin_posts'))
