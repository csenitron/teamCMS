"""
@file: app/admin/modules/menu.py
@description: Логика модуля меню для админ-панели
@dependencies: MenuModuleInstance, MenuItemExtended, Menu, MenuItem
@created: 2024-12-21
"""

from ...extensions import db
from ...models.modules.menu import MenuModuleInstance, MenuItemExtended
from ...models.menu import Menu, MenuItem
from ...models.page import Page
from ...models.category import Category
from ...models.post import Post
from ...models.post_category import PostCategory
from ...models.module import ModuleInstance


class MenuModule:
    """Класс для управления модулем меню в админ-панели"""

    @staticmethod
    def get_content_options():
        """
        Получает опции контента для селектов в форме
        Returns:
            dict: Словарь с опциями для селектов (JSON serializable)
        """
        def build_hierarchical_categories(parent_id=None, level=0):
            """Рекурсивно строит иерархический список категорий"""
            categories = Category.query.filter_by(parent_id=parent_id).order_by(Category.sort_order, Category.id).all()
            result = []
            for cat in categories:
                prefix = "—" * level if level > 0 else ""
                result.append({
                    'id': cat.id, 
                    'name': f"{prefix} {cat.name}".strip(), 
                    'slug': cat.slug,
                    'level': level,
                    'has_children': bool(cat.subcategories)
                })
                # Рекурсивно добавляем подкатегории
                result.extend(build_hierarchical_categories(cat.id, level + 1))
            return result
        
        def build_hierarchical_post_categories(parent_id=None, level=0):
            """Рекурсивно строит иерархический список категорий постов"""
            post_categories = PostCategory.query.filter_by(parent_id=parent_id).order_by(PostCategory.sort_order, PostCategory.id).all()
            result = []
            for pc in post_categories:
                prefix = "—" * level if level > 0 else ""
                result.append({
                    'id': pc.id, 
                    'title': f"{prefix} {pc.name}".strip(), 
                    'slug': pc.slug,
                    'level': level,
                    'has_children': bool(pc.children)
                })
                # Рекурсивно добавляем подкатегории
                result.extend(build_hierarchical_post_categories(pc.id, level + 1))
            return result
        
        categories = build_hierarchical_categories()
        post_categories = build_hierarchical_post_categories()
        pages = Page.query.all()
        posts = Post.query.filter_by(is_published=True).all()
        
        return {
            'pages': [
                {'id': p.id, 'title': p.title, 'slug': p.slug}
                for p in pages
            ],
            'categories': categories,
            'posts': [
                {'id': p.id, 'title': p.title, 'slug': p.slug}
                for p in posts
            ],
            'post_categories': post_categories
        }

    @staticmethod
    def save_instance(module_id, form_data, instance_id=None):
        """
        Создаёт/обновляет экземпляр ModuleInstance и связанный MenuModuleInstance,
        затем пересобирает пункты меню (MenuItem и MenuItemExtended).
        Ожидается вызов как save_instance(module_id, form_data, instance_id) из админ-роута.
        """
        try:
            print("=== НАЧАЛО СОХРАНЕНИЯ МЕНЮ ===")
            print("Form data keys:", list(form_data.keys()))
            # Находим или создаём ModuleInstance
            module_instance = ModuleInstance.query.get(instance_id) if instance_id else None
            if not module_instance:
                module_instance = ModuleInstance(
                    module_id=module_id,
                    settings=form_data.get('settings') or '{}',
                    selected_template=form_data.get('selected_template') or 'default'
                )
                db.session.add(module_instance)
                db.session.flush()
            print(f"Module instance ID: {module_instance.id}")

            # Получаем или создаём MenuModuleInstance
            menu_instance = MenuModuleInstance.query.filter_by(
                module_instance_id=module_instance.id
            ).first()

            if not menu_instance:
                print(f"MenuModuleInstance не найден для module_instance_id={module_instance.id}, создаем новый")
                menu = Menu.query.first()
                if not menu:
                    menu = Menu(name='Основное меню')
                    db.session.add(menu)
                    db.session.flush()
                menu_instance = MenuModuleInstance(
                    module_instance_id=module_instance.id,
                    menu_id=menu.id
                )
                db.session.add(menu_instance)
                db.session.flush()

            # Сохраняем основные поля
            menu_instance.title = form_data.get('menu_title', '')
            menu_instance.menu_style = form_data.get('menu_style', 'horizontal')
            menu_instance.max_depth = int(form_data.get('max_depth', 3))
            menu_instance.show_icons = bool(form_data.get('show_icons', False))
            menu_instance.enable_videos = bool(form_data.get('enable_videos', False))
            # Флаг главного меню
            is_main_flag = bool(form_data.get('is_main', False))
            if is_main_flag:
                # Снимаем флаг у всех остальных
                MenuModuleInstance.query.update({MenuModuleInstance.is_main: False})
                db.session.flush()
            menu_instance.is_main = is_main_flag
            db.session.flush()

            # Удаляем старые пункты меню
            MenuItemExtended.query.filter_by(menu_instance_id=menu_instance.id).delete()
            # Сбрасываем parent_id, чтобы не нарушать FK (self-referencing)
            MenuItem.query.filter_by(menu_id=menu_instance.menu_id).update({MenuItem.parent_id: None})
            db.session.flush()
            # Теперь можно удалить все пункты меню данного меню
            MenuItem.query.filter_by(menu_id=menu_instance.menu_id).delete()
            db.session.flush()

            # Сохраняем новые пункты меню (сначала MenuItem, потом MenuItemExtended)
            index = 0
            menu_items_map = {}  # index -> MenuItem
            while True:
                item_title = form_data.get(f'menu_item_{index}_title', None)
                if item_title is None:
                    break
                item_type = form_data.get(f'menu_item_{index}_type', 'custom')
                url = form_data.get(f'menu_item_{index}_custom_url', '') if item_type in ['custom', 'external'] else ''
                # Не теряем target_id, если он не передан при изменении вложенности
                target_id_raw = form_data.get(f'menu_item_{index}_target_id', None)
                if target_id_raw and str(target_id_raw).isdigit():
                    target_id = int(target_id_raw)
                else:
                    # Пытаемся восстановить прежний target_id по старому MenuItem (если существует)
                    target_id = None
                
                icon_id = form_data.get(f'menu_item_{index}_icon_id', None)
                if icon_id and str(icon_id).isdigit():
                    icon_id = int(icon_id)
                else:
                    icon_id = None
                video_id = form_data.get(f'menu_item_{index}_video_id', None)
                if video_id and str(video_id).isdigit():
                    video_id = int(video_id)
                else:
                    video_id = None
                description = form_data.get(f'menu_item_{index}_description', '')
                custom_class = form_data.get(f'menu_item_{index}_custom_class', '')
                position = int(form_data.get(f'menu_item_{index}_position', index))
                parent_index = form_data.get(f'menu_item_{index}_parent_id', None)
                print(f"DEBUG: item {index} '{item_title}' - parent_index: {parent_index}")
                parent_id = None
                if parent_index and str(parent_index).isdigit():
                    parent_index_int = int(parent_index)
                    # Проверяем, является ли parent_index индексом в форме или ID пункта меню
                    if parent_index_int < 1000:  # Если это индекс в форме (обычно < 1000)
                        # parent_index - это индекс в форме, ищем id созданного MenuItem
                        parent_menu_item = menu_items_map.get(parent_index_int)
                        print(f"DEBUG: parent_index {parent_index_int} как индекс формы, parent_menu_item: {parent_menu_item.title if parent_menu_item else 'None'}")
                    else:
                        # parent_index - это ID пункта меню из базы данных
                        parent_menu_item = MenuItem.query.get(parent_index_int)
                        print(f"DEBUG: parent_index {parent_index_int} как ID пункта меню, parent_menu_item: {parent_menu_item.title if parent_menu_item else 'None'}")
                    
                    if parent_menu_item:
                        parent_id = parent_menu_item.id
                        print(f"DEBUG: setting parent_id to {parent_id}")
                print(f"DEBUG: final parent_id for '{item_title}': {parent_id}")
                # Сохраняем MenuItem
                menu_item = MenuItem(
                    menu_id=menu_instance.menu_id,
                    title=item_title,
                    url=url,
                    parent_id=parent_id,
                    position=position
                )
                db.session.add(menu_item)
                db.session.flush()  # чтобы получить id
                menu_items_map[index] = menu_item
                # Сохраняем MenuItemExtended
                # Если target_id не пришёл (меняли только вложенность), попробуем взять старый extended по title
                if target_id is None:
                    old_ext = MenuItemExtended.query.filter_by(menu_instance_id=menu_instance.id).join(MenuItem).filter(
                        MenuItem.title == item_title
                    ).first()
                    if old_ext:
                        target_id = old_ext.target_id
                menu_item_ext = MenuItemExtended(
                    menu_instance_id=menu_instance.id,
                    menu_item_id=menu_item.id,
                    item_type=item_type,
                    target_id=target_id,
                    icon_id=icon_id,
                    video_id=video_id,
                    description=description,
                    custom_class=custom_class,
                    sort_order=position
                )
                db.session.add(menu_item_ext)
                print(f"Сохраняем пункт: {item_title}, type={item_type}, target_id={target_id}, url={url}, parent_id={parent_id}, video_id={video_id}")
                index += 1
            db.session.commit()
            print("=== СОХРАНЕНИЕ МЕНЮ ЗАВЕРШЕНО ===")
            from flask import redirect, url_for
            return redirect(url_for('admin.create_or_edit_module_instance', module_id=module_instance.module_id, instance_id=module_instance.id))
        except Exception as e:
            db.session.rollback()
            print(f"Ошибка при сохранении меню: {e}")
            raise

    @staticmethod
    def load_instance_data(instance_id):
        """
        Загружает данные экземпляра модуля меню с подгрузкой имени файла видео для предпросмотра
        """
        print(f"=== ЗАГРУЗКА ДАННЫХ МЕНЮ instance_id: {instance_id} ===")
        from ...models.image import Image
        if not instance_id:
            print("instance_id не передан, возвращаем дефолтные значения")
            return {
                'moduleInstanceData': {
                    'title': 'Новое меню',
                    'menu_style': 'horizontal',
                    'max_depth': 3,
                    'show_icons': False,
                    'enable_videos': False
                },
                'items': [],
                'contentOptions': MenuModule.get_content_options()
            }
        menu_instance = MenuModuleInstance.query.filter_by(module_instance_id=instance_id).first()
        if not menu_instance:
            print("MenuModuleInstance не найден, возвращаем дефолтные значения")
            return {
                'moduleInstanceData': {
                    'title': 'Новое меню',
                    'menu_style': 'horizontal',
                    'max_depth': 3,
                    'show_icons': False,
                    'enable_videos': False
                },
                'items': [],
                'contentOptions': MenuModule.get_content_options()
            }
        print(f"Найден MenuModuleInstance: {menu_instance.id}, menu_id: {menu_instance.menu_id}")
        items = []
        if menu_instance.menu_id:
            base_items = MenuItem.query.filter_by(menu_id=menu_instance.menu_id).order_by(MenuItem.position).all()
            print(f"Найдено базовых пунктов меню: {len(base_items)}")
            for base_item in base_items:
                print(f"Обрабатываем базовый пункт: {base_item.id} - {base_item.title}")
                extended_item = MenuItemExtended.query.filter_by(
                    menu_instance_id=menu_instance.id,
                    menu_item_id=base_item.id
                ).first()
                video_filename = None
                if extended_item and extended_item.video_id:
                    video = Image.query.get(extended_item.video_id)
                    if video:
                        video_filename = video.filename
                item_data = {
                    'id': base_item.id,
                    'title': base_item.title,
                    'url': base_item.url,
                    'position': base_item.position,
                    'parent_id': base_item.parent_id,
                    'item_type': extended_item.item_type if extended_item else 'custom',
                    'target_id': extended_item.target_id if extended_item else None,
                    'icon_id': extended_item.icon_id if extended_item else None,
                    'video_id': extended_item.video_id if extended_item else None,
                    'video_filename': video_filename,
                    'description': extended_item.description if extended_item else '',
                    'custom_class': extended_item.custom_class if extended_item else '',
                    'show_in_catalog': extended_item.show_in_catalog if extended_item else False,
                    'open_in_new_tab': extended_item.open_in_new_tab if extended_item else False,
                    'is_featured': extended_item.is_featured if extended_item else False,
                    'sort_order': extended_item.sort_order if extended_item else base_item.position
                }
                items.append(item_data)
                print(f"Добавлен пункт в items: {item_data['title']}")
        # Получаем ModuleInstance для ID
        from ...models.module import ModuleInstance
        module_instance = ModuleInstance.query.get(instance_id)
        print(f"ModuleInstance найден: {module_instance is not None}")
        if module_instance:
            print(f"ModuleInstance ID: {module_instance.id}")
        
        module_instance_data = {
            'id': module_instance.id if module_instance else None,
            'title': menu_instance.title or 'Меню сайта',
            'menu_style': getattr(menu_instance, 'menu_style', 'horizontal'),
            'max_depth': getattr(menu_instance, 'max_depth', 3),
            'show_icons': getattr(menu_instance, 'show_icons', True),
            'enable_videos': getattr(menu_instance, 'enable_videos', False),
            'is_main': getattr(menu_instance, 'is_main', False),
        }
        print(f"module_instance_data: {module_instance_data}")
        print(f"moduleInstanceData: {module_instance_data}")
        result = {
            'moduleInstanceData': module_instance_data,
            'items': items,
            'contentOptions': MenuModule.get_content_options()
        }
        print(f"=== РЕЗУЛЬТАТ ЗАГРУЗКИ: {len(items)} пунктов ===")
        return result

    @staticmethod
    def build_menu_tree(menu_items, parent_id=None):
        """
        Строит иерархическое дерево меню
        
        Args:
            menu_items: Список пунктов меню
            parent_id: ID родительского элемента
            
        Returns:
            list: Иерархический список пунктов меню
        """
        tree = []
        for item in menu_items:
            if item['parent_id'] == parent_id:
                children = MenuModule.build_menu_tree(menu_items, item['id'])
                if children:
                    item['children'] = children
                tree.append(item)
        return tree

    @staticmethod
    def del_instance(module_id, instance_id):
        """
        Удаляет экземпляр модуля меню и связанные с ним данные.
        """
        from flask import flash, redirect, url_for
        from ...models.module import ModuleInstance
        
        # Проверяем, существует ли экземпляр модуля
        module_instance = ModuleInstance.query.get(instance_id)
        if not module_instance:
            flash("Ошибка: Экземпляр модуля не найден!", "danger")
            return redirect(url_for('admin.modules_list'))

        # Удаляем связанные записи из MenuModuleInstance
        menu_instance = MenuModuleInstance.query.filter_by(module_instance_id=instance_id).first()
        if menu_instance:
            # Удаляем все пункты меню, связанные с этим меню
            MenuItemExtended.query.filter_by(menu_id=menu_instance.menu_id).delete()
            MenuItem.query.filter_by(menu_id=menu_instance.menu_id).delete()
            
            # Удаляем само меню
            Menu.query.filter_by(id=menu_instance.menu_id).delete()
            
            # Удаляем экземпляр меню
            db.session.delete(menu_instance)

        # Удаляем сам экземпляр модуля
        db.session.delete(module_instance)

        # Фиксируем изменения в БД
        db.session.commit()

        flash("Экземпляр меню успешно удалён.", "success")
        return redirect(url_for('admin.modules_list'))

    @staticmethod
    def create_subcategories_menu_items(category_id, menu_instance_id, parent_menu_item_id=None):
        """
        Автоматически создает пункты меню из подкатегорий выбранной категории
        
        Args:
            category_id: ID категории
            menu_instance_id: ID экземпляра меню
            parent_menu_item_id: ID родительского пункта меню (если есть) - НЕ ИСПОЛЬЗУЕТСЯ
            
        Returns:
            list: Список созданных пунктов меню
        """
        try:
            print(f"=== СОЗДАНИЕ ПОДПУНКТОВ МЕНЮ ===")
            print(f"category_id: {category_id}")
            print(f"menu_instance_id: {menu_instance_id}")
            print(f"parent_menu_item_id: {parent_menu_item_id} (не используется)")
            
            # Получаем категорию
            category = Category.query.get(category_id)
            if not category:
                print(f"Категория с ID {category_id} не найдена")
                return []
            
            print(f"Найдена категория: {category.name}")
            
            # Получаем экземпляр меню по module_instance_id
            menu_instance = MenuModuleInstance.query.filter_by(module_instance_id=menu_instance_id).first()
            if not menu_instance:
                print(f"MenuModuleInstance с module_instance_id {menu_instance_id} не найден")
                return []
            
            print(f"Найден MenuModuleInstance: {menu_instance.id}")
            
            created_items = []
            
            # Получаем все подкатегории
            subcategories = Category.query.filter_by(parent_id=category_id).order_by(Category.sort_order, Category.id).all()
            print(f"Найдено подкатегорий: {len(subcategories)}")
            for subcat in subcategories:
                print(f"  - {subcat.name} (ID: {subcat.id})")
            
            # Получаем максимальную позицию для новых пунктов
            max_position = db.session.query(db.func.max(MenuItem.position)).filter_by(menu_id=menu_instance.menu_id).scalar() or 0
            
            # Если передан parent_menu_item_id, ищем соответствующий MenuItem
            parent_menu_item = None
            if category_id:
                # Ищем MenuItem по target_id (ID категории) и item_type='category'
                parent_extended = MenuItemExtended.query.filter_by(
                    menu_instance_id=menu_instance.id,
                    target_id=category_id,
                    item_type='category'
                ).first()
                print(f"Поиск родительского extended пункта для category_id={category_id}, menu_instance_id={menu_instance.id}: {parent_extended is not None}")
                if parent_extended:
                    parent_menu_item = MenuItem.query.get(parent_extended.menu_item_id)
                    print(f"Найден родительский пункт меню: {parent_menu_item.title if parent_menu_item else 'Не найден'} (ID: {parent_menu_item.id if parent_menu_item else 'None'})")
                else:
                    print(f"Родительский extended пункт для category_id={category_id} не найден.")
                    
                    # Попробуем найти по menu_item_id, если он передан
                    if parent_menu_item_id and str(parent_menu_item_id).isdigit():
                        parent_menu_item = MenuItem.query.get(int(parent_menu_item_id))
                        print(f"Поиск по menu_item_id {parent_menu_item_id}: {parent_menu_item.title if parent_menu_item else 'Не найден'}")
            else:
                print("category_id не передан для поиска родительского пункта.")
            
            # Дополнительная отладка: выведем все пункты меню для этого экземпляра
            all_menu_items = MenuItemExtended.query.filter_by(menu_instance_id=menu_instance.id).join(MenuItem).all()
            print(f"Все пункты меню для экземпляра {menu_instance.id}:")
            for item in all_menu_items:
                print(f"  - {item.menu_item.title} (ID: {item.menu_item.id}, parent_id: {item.menu_item.parent_id}, target_id: {item.target_id}, type: {item.item_type})")
            
            for i, subcat in enumerate(subcategories):
                # Создаем пункт меню как дочерний от родительского пункта
                menu_item = MenuItem(
                    menu_id=menu_instance.menu_id,
                    title=subcat.name,
                    url=f"/category/{subcat.slug}",
                    parent_id=parent_menu_item.id if parent_menu_item else None,
                    position=max_position + i + 1
                )
                db.session.add(menu_item)
                db.session.flush()  # Получаем ID
                
                # Создаем расширенную информацию
                menu_item_ext = MenuItemExtended(
                    menu_instance_id=menu_instance.id,  # Используем ID MenuModuleInstance
                    menu_item_id=menu_item.id,
                    item_type='category',
                    target_id=subcat.id,
                    sort_order=max_position + i + 1
                )
                db.session.add(menu_item_ext)
                
                created_items.append({
                    'id': menu_item.id,
                    'title': subcat.name,
                    'url': f"/category/{subcat.slug}",
                    'parent_id': parent_menu_item.id if parent_menu_item else None,
                    'position': max_position + i + 1,
                    'item_type': 'category',
                    'target_id': subcat.id
                })
                
                print(f"Создан пункт меню: {subcat.name} (ID: {menu_item.id})")
            
            db.session.commit()
            print(f"Создано {len(created_items)} пунктов меню")
            return created_items
            
        except Exception as e:
            db.session.rollback()
            print(f"Ошибка при создании подпунктов меню: {e}")
            import traceback
            traceback.print_exc()
            return [] 