import json

from flask import flash, redirect, url_for, jsonify

from ...models.module import *
from ...models.modules.slider import *
from ...extensions import db


class SliderModule:
    """Логика сохранения экземпляра слайдера и слайдов"""

    @staticmethod
    def save_instance(module_id, form_data, instance_id=None):

        """Создание или обновление слайдера и его слайдов"""

        # Проверяем module_id
        if not module_id:
            flash("Ошибка: module_id не передан!", "danger")
            return redirect(url_for('admin.modules_list'))

        # Получаем или создаем ModuleInstance
        module_instance = ModuleInstance.query.get(instance_id) if instance_id else None

        if not module_instance:
            module_instance = ModuleInstance(
                module_id=module_id,
                settings=json.dumps({'name': form_data.get("title"), 'status': form_data.get("status") == "on"}),
                selected_template="default"
            )
            db.session.add(module_instance)
            db.session.flush()
        else:
            ModuleInstance.query.filter_by(id=module_instance.id).update({'settings':json.dumps({'name': form_data.get("title"), 'status': form_data.get("status") == "on"})})

        # Получаем или создаем SliderModuleInstance
        slider_instance = SliderModuleInstance.query.filter_by(module_instance_id=module_instance.id).first()

        if not slider_instance:
            slider_instance = SliderModuleInstance(
                module_instance_id=module_instance.id
            )
            db.session.add(slider_instance)
        else:
            SliderItem.query.filter_by(slider_id=slider_instance.id).delete()
        slider_instance.title = form_data.get("title")
        # Исправление: безопасное преобразование width в int с дефолтным значением
        try:
            slider_instance.width = int(form_data.get("width", 100))
        except (ValueError, TypeError):
            slider_instance.width = 100  # Дефолтное значение
        # Исправление: проверка transition_type
        slider_instance.transition_type = form_data.get("transition_type") if form_data.get("transition_type") in ['fade', 'slide'] else 'slide'
        slider_instance.status = form_data.get("status") == "on"
        slider_instance.show_arrows = form_data.get("show_arrows") == "on"
        slider_instance.show_indicators = form_data.get("show_indicators") == "on"

        db.session.commit()  # Фиксируем изменения перед обработкой слайдов

        print("Форма передала:", form_data)  # Отладка

        slides = {}
        for key, value in form_data.items():
            if key.startswith("slides["):
                parts = key.split('[')
                slide_index = parts[1].split(']')[0]
                if slide_index not in slides:
                    slides[slide_index] = {'buttons': {}}

                if 'buttons' in parts[2]:
                    btn_index = parts[3].split(']')[0]
                    field_name = parts[4].split(']')[0]
                    if btn_index not in slides[slide_index]['buttons']:
                        slides[slide_index]['buttons'][btn_index] = {}
                    slides[slide_index]['buttons'][btn_index][field_name] = value
                else:
                    field_name = parts[2].split(']')[0]
                    slides[slide_index][field_name] = value

        print(slides)
        for slide_index, slide_data in slides.items():
            buttons_list = []
            for btn_index, btn_data in slide_data.get('buttons', {}).items():
                buttons_list.append({
                    'text': btn_data.get('text'),
                    'link': btn_data.get('link'),
                    'color': btn_data.get('color'),
                    'text_color': btn_data.get('text_color')
                })

            slide = SliderItem(
                slider_id=slider_instance.id,
                image_pc_id=int(slide_data.get("image_pc_id", 0)),
                image_mobile_id=int(slide_data.get("image_mobile_id", 0)),
                title=slide_data.get("title"),
                description=slide_data.get("description"),
                text_color=slide_data.get("text_color", '#000000'),
                buttons=json.dumps(buttons_list) if buttons_list else None
            )
            db.session.add(slide)

        db.session.commit()

        flash("Слайдер сохранён!", "success")
        return redirect(url_for('admin.create_or_edit_module_instance', module_id=module_instance.module_id,
                                instance_id=module_instance.id))

    @staticmethod
    def load_instance_data(instance_id):
        """
        Загружает данные для редактирования экземпляра слайдера.
        """

        if instance_id:
            module_instance = ModuleInstance.query.get_or_404(instance_id)
            slider_instance = SliderModuleInstance.query.filter_by(module_instance_id=instance_id).first()
            slides = SliderItem.query.filter_by(slider_id=slider_instance.id).all() if slider_instance else []
            for slide in slides:
                slide.buttons = json.loads(slide.buttons) if slide.buttons else []
        else:
            module_instance = None
            slider_instance = None
            slides = []

        return {
            "module_instance": module_instance,
            "slider": slider_instance,
            "slides": slides
        }

    @staticmethod
    def del_instance(module_id, instance_id):
        """
        Удаляет экземпляр модуля и связанные с ним данные.
        """

        module_instance = ModuleInstance.query.get(instance_id)
        if not module_instance:
            flash("Ошибка: Экземпляр модуля не найден!", "danger")
            return redirect(url_for('admin.modules_list'))

        slider_instance = SliderModuleInstance.query.filter_by(module_instance_id=instance_id).first()
        if slider_instance:
            SliderItem.query.filter_by(slider_id=slider_instance.id).delete()
            db.session.delete(slider_instance)

        db.session.delete(module_instance)
        db.session.commit()

        flash("Экземпляр модуля успешно удалён.", "success")
        return redirect(url_for('admin.modules_list'))

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

        settings = json.loads(module_instance.settings) if module_instance.settings else {}
        slider_instance = module_instance.slider_instance
        slides = slider_instance.slides if slider_instance else []
        for slide in slides:
            slide.buttons = json.loads(slide.buttons) if slide.buttons else []

        return {
            'settings': settings,
            'slider': slider_instance,
            'slides': slides
        }