import json
import logging
from flask import flash, redirect, url_for
from ...models.module import ModuleInstance
from ...models.modules.banner import BannerModuleInstance, BannerItem
from ...extensions import db

__all__ = ['BannerModule']

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class BannerModule:
    """Логика обработки экземпляра слайд-баннера и его карточек"""

    @staticmethod
    def get_instance_data(module_instance):
        """
        Получает данные модуля по объекту ModuleInstance.
        Возвращает словарь с данными для рендеринга слайд-баннера в шаблоне.

        Аргументы:
            module_instance: Экземпляр ModuleInstance, связанный с модулем слайд-баннера.

        Возвращает:
            dict: Словарь с ключами:
                - 'settings': Настройки модуля (распарсенный JSON).
                - 'banner': Экземпляр BannerModuleInstance или None.
                - 'banner_items': Список объектов BannerItem или пустой список.
        """
        logger.debug(f"Получение данных для module_instance={module_instance}")
        # Проверяем наличие module_instance
        if not module_instance:
            return {
                'settings': {},
                'banner': None,
                'banner_items': []
            }

        # Извлекаем и парсим настройки из module_instance.settings
        settings = json.loads(module_instance.settings) if module_instance.settings else {}

        # Получаем связанный экземпляр BannerModuleInstance
        banner_instance = BannerModuleInstance.query.filter_by(module_instance_id=module_instance.id).first()

        # Получаем список карточек (BannerItem), если banner_instance существует
        banner_items = BannerItem.query.filter_by(banner_id=banner_instance.id).all() if banner_instance else []
        
        logger.debug(f"Данные для рендеринга: settings={settings}, banner_instance={banner_instance}, banner_items={banner_items}")
        
        # Формируем и возвращаем структурированные данные
        return {
            'settings': settings,
            'banner': banner_instance,
            'banner_items': banner_items
        }