import json
from flask import flash, redirect, url_for
from ...extensions import db
from ...models.module import ModuleInstance
from ...models.modules.gallery import GalleryModuleInstance, GalleryItem

class GalleryModule:
    """Логика сохранения / загрузки / удаления экземпляра галереи"""

    @staticmethod
    def save_instance(module_id, form_data, instance_id=None):
        # 1) Проверка module_id
        if not module_id:
            flash("Ошибка: module_id не передан!", "danger")
            return redirect(url_for('admin.modules_list'))

        # 2) Получаем / создаём ModuleInstance
        module_instance = ModuleInstance.query.get(instance_id) if instance_id else None
        if not module_instance:
            # Создание
            module_instance = ModuleInstance(
                module_id=module_id,
                settings=json.dumps({'name': form_data.get("title")}),
                selected_template="default"
            )
            db.session.add(module_instance)
            db.session.flush()
        else:
            # Обновление
            module_instance.settings = json.dumps({'name': form_data.get("title")})

        # 3) Получаем / создаём GalleryModuleInstance (аналог SliderModuleInstance)
        gallery_instance = GalleryModuleInstance.query.filter_by(module_instance_id=module_instance.id).first()
        if not gallery_instance:
            gallery_instance = GalleryModuleInstance(module_instance_id=module_instance.id)
            db.session.add(gallery_instance)
        else:
            # Если нужно, очищаем старые элементы галереи
            GalleryItem.query.filter_by(gallery_id=gallery_instance.id).delete()

        # Заполняем поля галереи
        gallery_instance.title = form_data.get("title")
        gallery_instance.description = form_data.get("description") or ""
        db.session.commit()

        # 4) Сохраняем элементы галереи (например, images[...] из формы)
        #    (пример — как со слайдами)
        images = {}
        for key, value in form_data.items():
            if key.startswith("images["):
                # Пример: images[10][image_id], images[10][caption]
                img_index = key.split("[")[1].split("]")[0]
                field_name = key.split("[")[2].split("]")[0]
                if img_index not in images:
                    images[img_index] = {}
                images[img_index][field_name] = value

        for img_index, data in images.items():
            # Безопасное преобразование ID изображения
            image_id = None
            if data.get("image_id") and str(data.get("image_id")).strip():
                try:
                    image_id = int(data["image_id"])
                except (ValueError, TypeError):
                    image_id = None
            
            if image_id:  # Создаем элемент только если есть изображение
                item = GalleryItem(
                    gallery_id=gallery_instance.id,
                    image_id=image_id,
                    caption=data.get("caption", "")
                )
                db.session.add(item)

        db.session.commit()
        flash("Галерея сохранена!", "success")
        return redirect(url_for('admin.create_or_edit_module_instance',
                                module_id=module_instance.module_id,
                                instance_id=module_instance.id))

    @staticmethod
    def load_instance_data(instance_id):
        """Загрузка данных для формы редактирования галереи"""
        if instance_id:
            module_instance = ModuleInstance.query.get_or_404(instance_id)
            gallery_instance = GalleryModuleInstance.query.filter_by(module_instance_id=instance_id).first()
            items = GalleryItem.query.filter_by(gallery_id=gallery_instance.id).all() if gallery_instance else []
        else:
            module_instance = None
            gallery_instance = None
            items = []
        return {
            "module_instance": module_instance,
            "gallery": gallery_instance,
            "items": items
        }

    @staticmethod
    def del_instance(module_id, instance_id):
        """Удаление галереи и всех её элементов"""
        module_instance = ModuleInstance.query.get(instance_id)
        if not module_instance:
            flash("Ошибка: Экземпляр модуля не найден!", "danger")
            return redirect(url_for('admin.modules_list'))

        gallery_instance = GalleryModuleInstance.query.filter_by(module_instance_id=instance_id).first()
        if gallery_instance:
            GalleryItem.query.filter_by(gallery_id=gallery_instance.id).delete()
            db.session.delete(gallery_instance)

        db.session.delete(module_instance)
        db.session.commit()
        flash("Экземпляр галереи успешно удалён.", "success")
        return redirect(url_for('admin.modules_list'))
