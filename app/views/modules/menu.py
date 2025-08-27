"""
@file: app/views/modules/menu.py
@description: Логика модуля меню для фронтенда
@dependencies: MenuModuleInstance, MenuItemExtended
@created: 2024-12-21
"""

from ...models.modules.menu import MenuModuleInstance, MenuItemExtended
from ...models.menu import MenuItem
from ...models.category import Category
from ...models.image import Image


class MenuModule:
    """Класс для отображения модуля меню на фронтенде"""

    @staticmethod
    def get_instance_data(module_instance):
        """
        Получает данные экземпляра модуля для отображения на фронтенде
        
        Args:
            module_instance: Экземпляр ModuleInstance
            
        Returns:
            dict: Данные для отображения в шаблоне
        """
        try:
            # Получаем экземпляр модуля меню
            menu_instance = MenuModuleInstance.query.filter_by(
                module_instance_id=module_instance.id
            ).first()

            if not menu_instance:
                return {
                    'error': 'Экземпляр модуля меню не найден',
                    'menu_items': []
                }

            # Получаем пункты меню с их расширенными данными
            extended_items = MenuItemExtended.query.filter_by(
                menu_instance_id=menu_instance.id
            ).join(MenuItem).order_by(MenuItem.position).all()

            # Строим структуру меню
            menu_structure = MenuModule.build_menu_structure(
                extended_items, 
                menu_instance.max_depth,
                menu_instance.enable_auto_catalog
            )

            # Возвращаем данные для шаблона
            return {
                'menu_title': menu_instance.title,
                'menu_style': menu_instance.menu_style,
                'show_icons': menu_instance.show_icons,
                'enable_videos': menu_instance.enable_videos,
                'max_depth': menu_instance.max_depth,
                'menu_items': menu_structure,
                'menu_tree': MenuModule.build_hierarchical_menu(menu_structure)
            }

        except Exception as e:
            print(f"Ошибка получения данных модуля меню: {e}")
            return {
                'error': str(e),
                'menu_items': []
            }

    @staticmethod
    def build_menu_structure(extended_items, max_depth=3, enable_auto_catalog=True):
        """
        Строит структуру меню для отображения
        
        Args:
            extended_items: Список расширенных пунктов меню
            max_depth: Максимальная глубина меню
            enable_auto_catalog: Включить автокаталог
            
        Returns:
            list: Структурированный список пунктов меню
        """
        menu_items = []

        for extended_item in extended_items:
            try:
                # Получаем данные иконки и видео
                icon_data = None
                video_data = None

                if extended_item.icon_id:
                    icon = Image.query.get(extended_item.icon_id)
                    if icon:
                        icon_data = {
                            'id': icon.id,
                            'filename': icon.filename,
                            'url': f'/static/uploads/{icon.filename}'
                        }

                if extended_item.video_id:
                    video = Image.query.get(extended_item.video_id)
                    if video:
                        video_data = {
                            'id': video.id,
                            'filename': video.filename,
                            'url': f'/static/uploads/videos/{video.filename}'
                        }

                # Формируем данные пункта меню
                item_data = {
                    'id': extended_item.menu_item.id,  # Используем ID из MenuItem, а не из MenuItemExtended
                    'title': extended_item.get_target_title(),
                    'url': extended_item.get_dynamic_url(),
                    'type': extended_item.item_type,
                    'description': extended_item.description,
                    'custom_class': extended_item.custom_class,
                    'open_in_new_tab': extended_item.open_in_new_tab,
                    'is_featured': extended_item.is_featured,
                    'parent_id': extended_item.menu_item.parent_id,
                    'position': extended_item.menu_item.position,
                    'icon': icon_data,
                    'video': video_data,
                    'children': []
                }

                # Для каталога добавляем автогенерируемые категории
                # Каталог: всегда подтягиваем дерево категорий, чтобы не зависеть от невыставленных флагов
                url_value = (extended_item.menu_item.url or '').rstrip('/') if getattr(extended_item, 'menu_item', None) else ''
                is_catalog_point = (
                    extended_item.item_type == 'catalog' or
                    (extended_item.item_type in ('custom', 'external') and url_value == '/catalog')
                )
                if is_catalog_point:
                    # Если в целевом id указан корень каталога — используем его
                    parent_root_id = extended_item.target_id if extended_item.target_id else None
                    catalog_items = MenuItemExtended.get_catalog_items(
                        parent_id=parent_root_id,
                        max_depth=max_depth
                    )
                    # Fallback: если ничего не нашли на верхнем уровне, а есть единственный корень — берем его детей
                    if not catalog_items:
                        roots = MenuItemExtended.get_catalog_items(parent_id=None, max_depth=1)
                        if len(roots) == 1:
                            catalog_items = MenuItemExtended.get_catalog_items(
                                parent_id=roots[0]['id'],
                                max_depth=max_depth
                            )
                    item_data['children'] = MenuModule.format_catalog_items(catalog_items)

                menu_items.append(item_data)

            except Exception as e:
                print(f"Ошибка обработки пункта меню {extended_item.id}: {e}")
                continue

        return menu_items

    @staticmethod
    def format_catalog_items(catalog_items):
        """
        Форматирует пункты автокаталога для отображения
        
        Args:
            catalog_items: Список пунктов каталога
            
        Returns:
            list: Отформатированные пункты каталога
        """
        formatted_items = []

        for item in catalog_items:
            try:
                # Получаем данные изображения категории
                image_data = None
                if item.get('image_id'):
                    image = Image.query.get(item['image_id'])
                    if image:
                        image_data = {
                            'id': image.id,
                            'filename': image.filename,
                            'url': f'/static/uploads/{image.filename}'
                        }

                formatted_item = {
                    'id': f"catalog_{item['id']}",
                    'title': item['title'],
                    'url': item['url'],
                    'type': 'category',
                    'description': item.get('description', ''),
                    'custom_class': 'catalog-item',
                    'open_in_new_tab': False,
                    'is_featured': False,
                    'icon': image_data,
                    'video': None,
                    'children': MenuModule.format_catalog_items(item.get('children', []))
                }

                formatted_items.append(formatted_item)

            except Exception as e:
                print(f"Ошибка форматирования пункта каталога: {e}")
                continue

        return formatted_items

    @staticmethod
    def build_hierarchical_menu(menu_items, parent_id=None):
        """
        Строит иерархическое дерево меню
        
        Args:
            menu_items: Плоский список пунктов меню
            parent_id: ID родительского элемента
            
        Returns:
            list: Иерархическое дерево меню
        """
        print(f"=== BUILD HIERARCHICAL MENU ===")
        print(f"parent_id: {parent_id}")
        print(f"menu_items count: {len(menu_items)}")
        
        tree = []

        for item in menu_items:
            print(f"Item: {item.get('title')} (ID: {item.get('id')}, parent_id: {item.get('parent_id')})")
            if item.get('parent_id') == parent_id:
                print(f"  -> Adding to tree (parent_id matches)")
                # Рекурсивно получаем дочерние элементы
                children = MenuModule.build_hierarchical_menu(menu_items, item['id'])
                
                # Добавляем уже существующие дочерние элементы (например, из каталога)
                if item.get('children'):
                    children.extend(item['children'])
                
                if children:
                    item['children'] = children
                    print(f"  -> Added {len(children)} children")

                tree.append(item)

        print(f"Returning tree with {len(tree)} items for parent_id {parent_id}")
        return tree

    @staticmethod
    def get_breadcrumbs(current_url, menu_items):
        """
        Генерирует хлебные крошки на основе структуры меню
        
        Args:
            current_url: Текущий URL страницы
            menu_items: Структура меню
            
        Returns:
            list: Массив хлебных крошек
        """
        breadcrumbs = []

        def find_path(items, target_url, path=[]):
            for item in items:
                current_path = path + [item]
                
                if item['url'] == target_url:
                    return current_path
                
                if item.get('children'):
                    found_path = find_path(item['children'], target_url, current_path)
                    if found_path:
                        return found_path
            
            return None

        path = find_path(menu_items, current_url)
        
        if path:
            breadcrumbs = [
                {
                    'title': item['title'],
                    'url': item['url'],
                    'is_current': item['url'] == current_url
                }
                for item in path
            ]

        return breadcrumbs

    @staticmethod
    def get_menu_by_location(location='main'):
        """
        Получает меню по местоположению (для использования в шаблонах)
        
        Args:
            location: Местоположение меню (main, footer, sidebar)
            
        Returns:
            dict: Данные меню или None
        """
        try:
            # Пока используем первый найденный экземпляр меню
            # В будущем можно добавить поле location в MenuModuleInstance
            menu_instance = MenuModuleInstance.query.first()
            
            if not menu_instance:
                return None

            # Создаем фиктивный module_instance для совместимости
            class FakeModuleInstance:
                def __init__(self, id):
                    self.id = id

            fake_module = FakeModuleInstance(menu_instance.module_instance_id)
            
            return MenuModule.get_instance_data(fake_module)

        except Exception as e:
            print(f"Ошибка получения меню по местоположению: {e}")
            return None 