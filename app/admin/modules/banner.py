import json
from flask import flash, redirect, url_for

from ...models.module import ModuleInstance
from ...models.modules.banner import BannerModuleInstance, BannerItem
from ...extensions import db


class BannerModule:
    """Админ-обработчик для BannerModule.

    Имена класса должны совпадать с полем Module.name в БД ("BannerModule"),
    чтобы `module_views._load_admin_module_classes()` корректно нашёл обработчик.
    """

    @staticmethod
    def save_instance(module_id, form_data, instance_id=None):
        """Создание/обновление экземпляра баннера и карточек.

        Ожидаемые поля формы:
          - title, cards_in_row
          - show_arrows, show_indicators, auto_scroll, scroll_interval (в settings ModuleInstance)
          - banners[<idx>][background_image_id|text|link_text|link_url]
        """
        if not module_id:
            flash("Ошибка: module_id не передан!", "danger")
            return redirect(url_for('admin.modules_list'))

        # Настройки для ModuleInstance.settings
        settings = {
            'status': form_data.get('status') == 'on',
            'show_arrows': form_data.get('show_arrows') == 'on',
            'show_indicators': form_data.get('show_indicators') == 'on',
            'auto_scroll': form_data.get('auto_scroll') == 'on',
            'scroll_interval': int(form_data.get('scroll_interval') or 5000),
        }

        # ModuleInstance
        module_instance = ModuleInstance.query.get(instance_id) if instance_id else None
        if not module_instance:
            module_instance = ModuleInstance(
                module_id=module_id,
                settings=json.dumps(settings),
                selected_template='default'
            )
            db.session.add(module_instance)
            db.session.flush()
        else:
            ModuleInstance.query.filter_by(id=module_instance.id).update({
                'settings': json.dumps(settings)
            })

        # BannerModuleInstance
        banner_instance = BannerModuleInstance.query.filter_by(module_instance_id=module_instance.id).first()
        if not banner_instance:
            banner_instance = BannerModuleInstance(module_instance_id=module_instance.id)
            db.session.add(banner_instance)
            db.session.flush()

        # Обновляем поля баннера
        banner_instance.title = form_data.get('title') or ''
        try:
            banner_instance.cards_in_row = int(form_data.get('cards_in_row') or 3)
        except Exception:
            banner_instance.cards_in_row = 3

        db.session.flush()

        # Удаляем старые элементы через ORM, чтобы гарантировать каскад
        for it in list(banner_instance.banner_items or []):
            db.session.delete(it)
        db.session.flush()

        # Собираем новые карточки из формы
        banners = {}
        for key, value in form_data.items():
            if key.startswith('banners['):
                # banners[<idx>][field]
                parts = key.split('[')
                if len(parts) < 3:
                    continue
                b_idx = parts[1].split(']')[0]
                field = parts[2].split(']')[0]
                banners.setdefault(b_idx, {})[field] = value

        for _, bdata in banners.items():
            # Приводим image_id к int
            try:
                bg_id = int(bdata.get('background_image_id') or 0)
            except Exception:
                bg_id = 0
            item = BannerItem(
                banner_id=banner_instance.id,
                background_image_id=bg_id if bg_id > 0 else None,
                text=bdata.get('text') or '',
                link_text=bdata.get('link_text') or '',
                link_url=bdata.get('link_url') or ''
            )
            db.session.add(item)

        db.session.commit()
        flash("Баннер сохранён!", "success")
        return redirect(url_for('admin.create_or_edit_module_instance', module_id=module_instance.module_id,
                                instance_id=module_instance.id))

    @staticmethod
    def load_instance_data(instance_id):
        """Загружает данные для формы редактирования баннера."""
        if instance_id:
            module_instance = ModuleInstance.query.get_or_404(instance_id)
            banner = BannerModuleInstance.query.filter_by(module_instance_id=instance_id).first()
            items = BannerItem.query.filter_by(banner_id=banner.id).all() if banner else []
            parsed_settings = json.loads(module_instance.settings) if module_instance and module_instance.settings else {}
        else:
            module_instance = None
            banner = None
            items = []
            parsed_settings = {}
        return {
            'module_instance': module_instance,
            'banner': banner,
            'banner_items': items,
            'settings': parsed_settings,
        }

    @staticmethod
    def del_instance(module_id, instance_id):
        """Удаление инстанса баннера с каскадом."""
        module_instance = ModuleInstance.query.get_or_404(instance_id)
        banner = BannerModuleInstance.query.filter_by(module_instance_id=instance_id).first()
        if banner:
            for it in list(banner.banner_items or []):
                db.session.delete(it)
            db.session.delete(banner)
        db.session.delete(module_instance)
        db.session.commit()
        flash("Экземпляр баннера удалён", "success")
        return redirect(url_for('admin.modules_list'))


