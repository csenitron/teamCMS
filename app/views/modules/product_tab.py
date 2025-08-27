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