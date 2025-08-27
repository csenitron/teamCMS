# app/admin/modules/tabs_module.py
import json
from flask import flash, redirect, url_for
from ...extensions import db
from ...models.module import ModuleInstance
from ...models.modules.product_tab import TabsModuleInstance, TabItem
from ...models.product import Product
from ...models.category import Category
from ...models.productOptions import ProductOption


class TabsModule:

    @staticmethod
    def save_instance(module_id, form_data, instance_id=None):
        from flask import request

        if not module_id:
            flash("Ошибка: module_id не передан!", "danger")
            return redirect(url_for('admin.modules_list'))

        # 1) Получаем/создаём ModuleInstance
        module_instance = ModuleInstance.query.get(instance_id) if instance_id else None
        if not module_instance:
            # создаём
            module_instance = ModuleInstance(
                module_id=module_id,
                settings=json.dumps({'name': form_data.get("module_title")}),
                selected_template="default"
            )
            db.session.add(module_instance)
            db.session.flush()
        else:
            # обновляем
            module_instance.settings = json.dumps({'title': form_data.get("module_title")})

        # 2) Получаем/создаём TabsModuleInstance
        tabs_instance = TabsModuleInstance.query.filter_by(module_instance_id=module_instance.id).first()
        if not tabs_instance:
            tabs_instance = TabsModuleInstance(module_instance_id=module_instance.id)
            db.session.add(tabs_instance)
        else:
            # Удаляем старые вкладки (TabItem)
            TabItem.query.filter_by(tabs_id=tabs_instance.id).delete()

        # Сохраняем title
        tabs_instance.title = form_data.get("module_title") or "Табы"
        db.session.commit()

        # 3) Парсим вкладки из form_data
        # Ожидаем структуру: tabs[XXX][tab_title], tabs[XXX][mode], tabs[XXX][category_id]...
        # Где XXX = id вкладки или new-index
        tabs_data = {}
        for key, value in form_data.items():
            if key.startswith("tabs["):
                # Пример: tabs[12][tab_title], tabs[new-0][mode], ...
                parts = key.split("[")
                tab_index = parts[1].split("]")[0]  # "12" или "new-0"
                field_name = parts[2].split("]")[0]  # "tab_title", "mode", ...

                if tab_index not in tabs_data:
                    tabs_data[tab_index] = {}
                tabs_data[tab_index][field_name] = value

        # 4) Создаём вкладки
        for tab_index, fields in tabs_data.items():
            item = TabItem(
                tabs_id=tabs_instance.id,
                tab_title=fields.get("tab_title", "Вкладка"),
                mode=fields.get("mode", "category"),
                button_text=fields.get("button_text") or ""
            )

            if item.mode == "category":
                item.category_id = int(fields.get("category_id") or 0) if fields.get("category_id") else None
                item.limit_count = int(fields.get("limit_count") or 8)

            elif item.mode == "custom":
                # Для Select2 multiple -> name="tabs[NN][product_ids][]"
                # Собираем все выбранные товары:
                product_ids_list = request.form.getlist(f"tabs[{tab_index}][product_ids][]")
                if product_ids_list:
                    # Превращаем список в строку "1,2,3"
                    item.product_ids = ",".join(product_ids_list)
                else:
                    item.product_ids = ""

            elif item.mode == "all":
                # для "все товары" можно не хранить category_id, product_ids
                pass

            db.session.add(item)

        db.session.commit()

        flash("Модуль «Табы» сохранён!", "success")
        return redirect(url_for('admin.create_or_edit_module_instance',
                                module_id=module_instance.module_id,
                                instance_id=module_instance.id))

    @staticmethod
    def load_instance_data(instance_id):
        """
        Загрузка данных для формы редактирования TabsModule.
        """
        if instance_id:
            module_instance = ModuleInstance.query.get_or_404(instance_id)
            tabs_instance = TabsModuleInstance.query.filter_by(module_instance_id=instance_id).first()
            tab_items = TabItem.query.filter_by(tabs_id=tabs_instance.id).all() if tabs_instance else []
        else:
            module_instance = None
            tabs_instance = None
            tab_items = []

        # ЗАГРУЗКА КАТЕГОРИЙ
        categories = Category.query.order_by(Category.name).all()

        # ЗАГРУЗКА ТОВАРОВ
        products = Product.query.order_by(Product.name).all()

        return {
            "module_instance": module_instance,
            "tabs_instance": tabs_instance,
            "items": tab_items,
            "categories": categories,
            "products": products
        }

    @staticmethod
    def del_instance(module_id, instance_id):
        module_instance = ModuleInstance.query.get(instance_id)
        if not module_instance:
            flash("Ошибка: Экземпляр модуля не найден!", "danger")
            return redirect(url_for('admin.modules_list'))

        # Удаляем вкладки
        tabs_instance = TabsModuleInstance.query.filter_by(module_instance_id=instance_id).first()
        if tabs_instance:
            TabItem.query.filter_by(tabs_id=tabs_instance.id).delete()
            db.session.delete(tabs_instance)

        # Удаляем сам module_instance
        db.session.delete(module_instance)
        db.session.commit()

        flash("Экземпляр «Табы» удалён.", "success")
        return redirect(url_for('admin.modules_list'))

    @staticmethod
    def get_instance_data(module_instance):
        # Проверяем наличие module_instance
        if not module_instance:
            return {
                'settings': {},
                'tabs_instance': None,
                'tab_items': [],
                'tab_products': {}
            }

        # Извлекаем и парсим настройки из module_instance.settings
        settings = json.loads(module_instance.settings) if module_instance.settings else {}

        # Получаем связанный экземпляр TabsModuleInstance
        tabs_instance = TabsModuleInstance.query.filter_by(module_instance_id=module_instance.id).first()

        # Получаем список вкладок (TabItem), если tabs_instance существует
        tab_items = TabItem.query.filter_by(tabs_id=tabs_instance.id).all() if tabs_instance else []

        # Инициализируем словарь для товаров по вкладкам
        tab_products = {}

        for tab_item in tab_items:
            if tab_item.mode == "category" and tab_item.category_id:
                # Получаем товары из указанной категории с ограничением по limit_count
                products = Product.query.filter_by(category_id=tab_item.category_id).limit(tab_item.limit_count).all()
                # Загружаем опции для каждого товара
                for product in products:
                    product.product_options = ProductOption.get_options_by_product_id(product.id)
                tab_products[tab_item.id] = products

            elif tab_item.mode == "custom" and tab_item.product_ids:
                # Разбиваем строку product_ids на список ID
                product_ids = tab_item.product_ids.split(",")
                # Получаем товары по списку ID
                products = Product.query.filter(Product.id.in_(product_ids)).all()
                # Загружаем опции для каждого товара
                for product in products:
                    product.product_options = ProductOption.get_options_by_product_id(product.id)
                tab_products[tab_item.id] = products

            elif tab_item.mode == "all":
                # Получаем все товары с ограничением по limit_count (по умолчанию 8, если не указано)
                products = Product.query.limit(tab_item.limit_count or 8).all()
                # Загружаем опции для каждого товара
                for product in products:
                    product.product_options = ProductOption.get_options_by_product_id(product.id)
                tab_products[tab_item.id] = products

            else:
                # Если режим не распознан или данных нет, устанавливаем пустой список
                tab_products[tab_item.id] = []

        return {
            'settings': settings,
            'tabs_instance': tabs_instance,
            'tab_items': tab_items,
            'tab_products': tab_products
        }