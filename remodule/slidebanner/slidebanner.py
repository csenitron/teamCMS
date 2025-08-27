import json
import logging
from flask import flash, redirect, url_for
from ...models.module import ModuleInstance
from ...models.modules.slidebanner_models import SlideBannerModuleInstance, SlideBannerItem
from ...extensions import db

__all__ = ['SlideBannerModule']

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class SlideBannerModule:
    """Логика обработки экземпляра слайд-баннера и его карточек"""

    @staticmethod
    def save_instance(module_id, form_data, instance_id=None):
        logger.debug(f"Сохранение слайд-баннера: module_id={module_id}, instance_id={instance_id}, form_data={form_data}")
        if not module_id:
            logger.error("Ошибка: module_id не передан")
            flash("Ошибка: module_id не передан!", "danger")
            return redirect(url_for('admin.modules_list'))

        # Получаем или создаем ModuleInstance
        module_instance = ModuleInstance.query.get(instance_id) if instance_id else None
        settings = {
            'name': form_data.get("title", ""),
            'status': form_data.get("status", "off") == "on",
            'show_arrows': form_data.get("show_arrows", "off") == "on",
            'show_indicators': form_data.get("show_indicators", "off") == "on",
            'auto_scroll': form_data.get("auto_scroll", "off") == "on",
            'scroll_interval': int(form_data.get("scroll_interval", 5000))
        }
        logger.debug(f"Настройки модуля: {settings}")

        if not module_instance:
            module_instance = ModuleInstance(
                module_id=module_id,
                settings=json.dumps(settings),
                selected_template="default"
            )
            db.session.add(module_instance)
            db.session.flush()
            logger.debug(f"Создан новый ModuleInstance: id={module_instance.id}")
        else:
            ModuleInstance.query.filter_by(id=module_instance.id).update({
                'settings': json.dumps(settings)
            })
            logger.debug(f"Обновлён ModuleInstance: id={module_instance.id}")

        # Получаем или создаем SlideBannerModuleInstance
        banner_instance = SlideBannerModuleInstance.query.filter_by(module_instance_id=module_instance.id).first()
        if not banner_instance:
            banner_instance = SlideBannerModuleInstance(module_instance_id=module_instance.id)
            db.session.add(banner_instance)
        else:
            SlideBannerItem.query.filter_by(banner_id=banner_instance.id).delete()
            logger.debug(f"Удалены старые SlideBannerItem для banner_id={banner_instance.id}")

        banner_instance.title = form_data.get("title", "")
        banner_instance.cards_in_row = int(form_data.get("cards_in_row", 3))
        db.session.commit()
        logger.debug(f"Сохранён banner_instance: id={banner_instance.id}, title={banner_instance.title}")

        # Собираем данные для баннеров
        banners = {}
        for key, value in form_data.items():
            if key.startswith("banners["):
                parts = key.split('[')
                banner_index = parts[1].split(']')[0]
                field_name = parts[2].split(']')[0]
                if banner_index not in banners:
                    banners[banner_index] = {}
                banners[banner_index][field_name] = value
        logger.debug(f"Данные баннеров: {banners}")

        if not banners:
            logger.warning("Баннеры не добавлены в форму")
            flash("Предупреждение: баннеры не добавлены, сохранён только заголовок и настройки!", "warning")

        # Создаем объекты SlideBannerItem
        for banner_index, banner_data in banners.items():
            try:
                bg_img_id = int(banner_data.get("background_image_id", 0))
            except (TypeError, ValueError):
                bg_img_id = 0
                logger.warning(f"Некорректный background_image_id для баннера {banner_index}")

            banner_item = SlideBannerItem(
                banner_id=banner_instance.id,
                background_image_id=bg_img_id,
                text=banner_data.get("text", ""),
                link_text=banner_data.get("link_text", ""),
                link_url=banner_data.get("link_url", "")
            )
            db.session.add(banner_item)
            logger.debug(f"Добавлен banner_item: {banner_item}")

        db.session.commit()
        logger.info("Слайд-баннер успешно сохранён")
        flash("Слайд-баннер сохранён!", "success")
        return redirect(url_for('admin.create_or_edit_module_instance',
                                module_id=module_instance.module_id,
                                instance_id=module_instance.id))

    @staticmethod
    def load_instance_data(instance_id):
        logger.debug(f"Загрузка данных для instance_id={instance_id}")
        if instance_id:
            module_instance = ModuleInstance.query.get_or_404(instance_id)
            banner_instance = SlideBannerModuleInstance.query.filter_by(module_instance_id=instance_id).first()
            banner_items = SlideBannerItem.query.filter_by(banner_id=banner_instance.id).all() if banner_instance else []
        else:
            module_instance = None
            banner_instance = None
            banner_items = []
        logger.debug(f"Загруженные данные: module_instance={module_instance}, banner_instance={banner_instance}, banner_items={banner_items}")
        return {
            "module_instance": module_instance,
            "banner": banner_instance,
            "banner_items": banner_items
        }

    @staticmethod
    def del_instance(module_id, instance_id):
        logger.debug(f"Удаление экземпляра: module_id={module_id}, instance_id={instance_id}")
        module_instance = ModuleInstance.query.get(instance_id)
        if not module_instance:
            logger.error("Экземпляр модуля не найден")
            flash("Ошибка: Экземпляр модуля не найден!", "danger")
            return redirect(url_for('admin.modules_list'))

        banner_instance = SlideBannerModuleInstance.query.filter_by(module_instance_id=instance_id).first()
        if banner_instance:
            SlideBannerItem.query.filter_by(banner_id=banner_instance.id).delete()
            db.session.delete(banner_instance)

        db.session.delete(module_instance)
        db.session.commit()
        logger.info("Экземпляр модуля успешно удалён")
        flash("Экземпляр модуля успешно удалён.", "success")
        return redirect(url_for('admin.modules_list'))

    @staticmethod
    def get_instance_data(module_instance):
        logger.debug(f"Получение данных для module_instance={module_instance}")
        if not module_instance:
            return {
                'settings': {},
                'banner': None,
                'banner_items': []
            }

        settings = json.loads(module_instance.settings) if module_instance.settings else {}
        banner_instance = SlideBannerModuleInstance.query.filter_by(module_instance_id=module_instance.id).first()
        banner_items = SlideBannerItem.query.filter_by(banner_id=banner_instance.id).all() if banner_instance else []
        logger.debug(f"Данные для рендеринга: settings={settings}, banner_instance={banner_instance}, banner_items={banner_items}")
        return {
            'settings': settings,
            'banner': banner_instance,
            'banner_items': banner_items
        }