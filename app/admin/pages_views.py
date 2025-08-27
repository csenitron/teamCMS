import json

from flask import Blueprint, render_template, request, redirect, url_for, flash
from ..extensions import db
from . import admin_bp
from .decorators import admin_required
from ..models.page import *
from ..models.module import *
from datetime import datetime




# ---------------------------
#   СПИСОК СТРАНИЦ
# ---------------------------
@admin_bp.route('page/', methods=['GET'])
@admin_required
def page_list():
    pages = Page.query.order_by(Page.created_at.desc()).all()
    return render_template('admin/page_list.html', pages=pages)


# ---------------------------
#   СОЗДАНИЕ/РЕДАКТИРОВАНИЕ СТРАНИЦ
# ---------------------------
@admin_bp.route('/page/form', defaults={'page_id': None}, methods=['GET', 'POST'])
@admin_bp.route('/page/form/<int:page_id>', methods=['GET', 'POST'])
@admin_required
def page_form(page_id):
    """
    Создание или редактирование страницы
    """
    # 1) Получаем или создаём Page
    if page_id:
        page = Page.query.get_or_404(page_id)
    else:
        page = Page()

    # 2) Если POST -> обрабатываем форму
    if request.method == 'POST':
        # Отладочный вывод
        print("Получены данные формы:", request.form)
        
        page.title = request.form.get('title')
        page.slug = request.form.get('slug') or generate_slug(page.title)
        page.meta_title = request.form.get('meta_title')
        page.meta_keywords = request.form.get('meta_keywords')
        page.meta_description = request.form.get('meta_description')

        # Сохраняем страницу для получения ID
        db.session.add(page)
        db.session.commit()
        
        # Отладочный вывод
        print(f"Сохранена страница с ID: {page.id}")

        # Очищаем layout (только если страница уже существовала)
        if page_id:
            PageLayout.query.filter_by(page_id=page.id).delete()

        # Разбираем JSON с layout
        layout_json = request.form.get('layout_json', '')
        print(f"Полученный layout_json: {layout_json}")
        
        try:
            if layout_json and layout_json.strip():
                layout_data = json.loads(layout_json)
            else:
                layout_data = []
                
            # Отладочный вывод
            print(f"Разобранный layout_data: {layout_data}")
            
            # Сохраняем ячейки PageLayout
            for row in layout_data:
                row_index = row.get('rowIndex')
                columns = row.get('columns', [])
                
                print(f"Обработка строки {row_index} с {len(columns)} столбцами")
                
                for col in columns:
                    col_index = col.get('colIndex', 0)
                    col_width = col.get('colWidth', 3)
                    module_instance_id = col.get('moduleInstanceId')
                    
                    print(f"  Столбец {col_index}, ширина {col_width}, модуль {module_instance_id}")

                    pl = PageLayout(
                        page_id=page.id,
                        row_index=row_index,
                        col_index=col_index,
                        col_width=col_width,
                        module_instance_id=module_instance_id
                    )
                    db.session.add(pl)

            db.session.commit()
            print("Layout успешно сохранен")
            
        except json.JSONDecodeError as e:
            print(f"Ошибка разбора JSON: {e}")
            flash(f"Ошибка разбора данных макета: {e}", "danger")
        except Exception as e:
            print(f"Ошибка при сохранении layout: {e}")
            db.session.rollback()
            flash(f"Ошибка при сохранении макета: {e}", "danger")

        flash("Страница успешно сохранена!", "success")
        return redirect(url_for('admin.page_list'))  # или другой список страниц

    # 3) Если GET -> подгружаем layout для отрисовки
    if page and page.id:
        layout_cells = PageLayout.query.filter_by(page_id=page.id)\
                            .order_by(PageLayout.row_index, PageLayout.col_index).all()
    else:
        layout_cells = []

    # 4) Подтягиваем реальные данные о модулях и экземплярах
    modules = Module.query.all()
    instances = ModuleInstance.query.all()
    # Превратим их в удобную структуру для шаблона
    # Например, module_instances_by_module = { module_id: [ {...}, {...} ] }
    from collections import defaultdict
    module_instances_by_module = defaultdict(list)

    for inst in instances:
        # Если в inst.settings хранится JSON с именем/названием
        settings_json = json.loads(inst.settings or '{}')
        # Название экземпляра возьмём из settings.get('name') или "Instance #ID"
        inst_label = settings_json.get('name') or f"Instance {inst.id}"

        module_instances_by_module[inst.module_id].append({
            'id': inst.id,
            'label': inst_label
        })

    return render_template(
        'admin/page_form.html',
        page=page,
        layout_cells=layout_cells,
        modules=modules,  # список всех модулей
        module_instances_by_module=module_instances_by_module  # экземпляры по каждому модулю
    )



# ---------------------------
#   УДАЛЕНИЕ СТРАНИЦ
# ---------------------------
@admin_bp.route('page/<int:page_id>/delete', methods=['POST'])
@admin_required
def page_delete(page_id):
    page = Page.query.get_or_404(page_id)
    # Удаляем layout
    PageLayout.query.filter_by(page_id=page.id).delete()
    # Удаляем саму страницу
    db.session.delete(page)
    db.session.commit()
    flash("Страница удалена", "success")
    return redirect(url_for('admin.page_list'))


def generate_slug(title):
    """
    Простая функция генерации slug (пример)
    """
    import re
    from unidecode import unidecode

    base = unidecode(title or '').lower()
    base = re.sub(r'[^a-z0-9]+', '-', base).strip('-')

    # Можно добавить логику, которая проверяет занятость slug
    # и при необходимости добавляет -1, -2...
    return base or 'page'
