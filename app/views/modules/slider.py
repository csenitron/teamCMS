import json

from flask import flash, redirect, url_for, jsonify

from ...models.module import *
from ...models.modules.slider import *
from ...extensions import db


class SliderModule:
    """Логика сохранения экземпляра слайдера и слайдов"""

    @staticmethod
    def get_instance_data(module_instance):
        """
        Получает данные модуля по объекту ModuleInstance.
        Возвращает словарь с данными для рендеринга или редактирования.
        """
        if not module_instance:
            return {
                'settings': {},
                'slider': None,
                'slides': []
            }

        # Парсим настройки из JSON
        settings = json.loads(module_instance.settings) if module_instance.settings else {}

        # Получаем связанный слайдер и слайды через отношения
        slider_instance = module_instance.slider_instance
        slides = slider_instance.slides if slider_instance else []

        return {
            'settings': settings,
            'slider': slider_instance,
            'slides': slides
        }


