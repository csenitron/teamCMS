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

        # Собираем settings так же, как в slidebanner: централизуем флаги UI и авто‑прокрутки
        settings = {
            'name': form_data.get("title"),
            'status': form_data.get("status") == "on",
            'show_arrows': form_data.get("show_arrows") == "on",
            'show_indicators': form_data.get("show_indicators") == "on",
            'auto_scroll': form_data.get("auto_scroll") == "on",
            # MultiDict поддерживает type, но здесь безопаснее обработать вручную
            'scroll_interval': int(form_data.get("scroll_interval") or 5000)
        }

        if not module_instance:
            module_instance = ModuleInstance(
                module_id=module_id,
                settings=json.dumps(settings),
                selected_template="default"
            )
            db.session.add(module_instance)
            db.session.flush()
        else:
            ModuleInstance.query.filter_by(id=module_instance.id).update({'settings': json.dumps(settings)})

        # Получаем или создаем SliderModuleInstance
        slider_instance = SliderModuleInstance.query.filter_by(module_instance_id=module_instance.id).first()

        if not slider_instance:
            slider_instance = SliderModuleInstance(
                module_instance_id=module_instance.id
            )
            db.session.add(slider_instance)
        else:
            # Удаляем старые слайды корректно через ORM, чтобы сработал каскад на кнопки
            old_slides = SliderItem.query.filter_by(slider_id=slider_instance.id).all()
            for _s in old_slides:
                db.session.delete(_s)
            db.session.flush()
        slider_instance.title = form_data.get("title")
        slider_instance.width = form_data.get("width", type=int)
        slider_instance.transition_type = form_data.get("transition_type")
        slider_instance.status = settings['status']
        # Дублируем флаги в инстанс для обратной совместимости шаблонов
        slider_instance.show_arrows = settings['show_arrows']
        slider_instance.show_indicators = settings['show_indicators']

        db.session.commit()  # ✅ Фиксируем изменения перед обработкой слайдов

        print("Форма передала:", form_data)  # 🔥 Отладка

        slides = {}
        for key, value in form_data.items():
            if key.startswith("slides["):
                slide_index = key.split("[")[1].split("]")[0]
                field_name = key.split("[")[2].split("]")[0]

                # Проверяем, существует ли уже словарь для slide_index, если нет - создаем
                if slide_index not in slides:
                    slides[slide_index] = {}

                slides[slide_index][field_name] = value
        print(slides)
        for slide_index, slide_data in slides.items():  # ✅ Получаем ключ и сам словарь
            # Безопасное преобразование ID изображений
            image_pc_id = None
            if slide_data.get("image_pc_id") and slide_data["image_pc_id"].strip():
                try:
                    image_pc_id = int(slide_data["image_pc_id"])
                except (ValueError, TypeError):
                    image_pc_id = None
            
            image_mobile_id = None
            if slide_data.get("image_mobile_id") and slide_data["image_mobile_id"].strip():
                try:
                    image_mobile_id = int(slide_data["image_mobile_id"])
                except (ValueError, TypeError):
                    image_mobile_id = None
            # Цвета заголовка/описания
            title_color = slide_data.get("title_color") or None
            description_color = slide_data.get("description_color") or None

            slide = SliderItem(
                slider_id=slider_instance.id,
                image_pc_id=image_pc_id,
                image_mobile_id=image_mobile_id,
                title=slide_data.get("title", ""),
                description=slide_data.get("description", ""),
                title_color=title_color,
                description_color=description_color,
                link_text=None,
                link_url=None,
            )
            db.session.add(slide)
            db.session.flush()
            # Кнопки: slides[i][buttons][j][text|url|bg_color|text_color]
            for key, value in slide_data.items():
                # Пройдёмся по вложенным ключам через шаблон buttons
                # Здесь slide_data уже плоский; кнопки приходят как отдельные поля в form_data,
                # поэтому лучше парсить исходный form_data
                pass

        # Вторая фаза: создаём кнопки из исходного form_data
        for key, value in form_data.items():
            if key.startswith('slides[') and '][buttons][' in key:
                # slides[<idx>][buttons][<bidx>][field]
                try:
                    parts = key.split('[')
                    sidx = parts[1].split(']')[0]
                    bidx = parts[3].split(']')[0]
                    field = parts[4].split(']')[0]
                except Exception:
                    continue
                # найдём только что созданный slide для этого индекса sidx (по порядку вставки)
                # упрощённо: соберём кэш индекса -> id
        db.session.flush()
        slides_map = {str(i): s.id for i, s in enumerate(SliderItem.query.filter_by(slider_id=slider_instance.id).order_by(SliderItem.id).all())}
        buttons_tmp = {}
        for key, value in form_data.items():
            if key.startswith('slides[') and '][buttons][' in key:
                parts = key.split('[')
                sidx = parts[1].split(']')[0]
                bidx = parts[3].split(']')[0]
                field = parts[4].split(']')[0]
                buttons_tmp.setdefault((sidx, bidx), {})[field] = value
        for (sidx, bidx), bdata in buttons_tmp.items():
            slide_id = slides_map.get(str(sidx))
            if not slide_id:
                continue
            from ...models.modules.slider import SliderButton
            btn = SliderButton(
                slide_id=slide_id,
                text=bdata.get('text') or '',
                url=bdata.get('url') or None,
                bg_color=bdata.get('bg_color') or None,
                text_color=bdata.get('text_color') or None,
                order=int(bidx)
            )
            db.session.add(btn)
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
        else:
            module_instance = None
            slider_instance = None  # ✅ Добавляем `None`, чтобы избежать ошибки в шаблоне
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

        # Проверяем, существует ли экземпляр модуля
        module_instance = ModuleInstance.query.get(instance_id)
        if not module_instance:
            flash("Ошибка: Экземпляр модуля не найден!", "danger")
            return redirect(url_for('admin.modules_list'))

        # Удаляем связанные записи из SliderModuleInstance
        slider_instance = SliderModuleInstance.query.filter_by(module_instance_id=instance_id).first()
        if slider_instance:
            # Удаляем все слайды, связанные с этим слайдером
            SliderItem.query.filter_by(slider_id=slider_instance.id).delete()

            # Удаляем сам слайдер
            db.session.delete(slider_instance)

        # Удаляем сам экземпляр модуля
        db.session.delete(module_instance)

        # Фиксируем изменения в БД
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


