import os
import importlib
from flask import render_template, request, flash, redirect, url_for
from . import admin_bp
from .decorators import admin_required
from ..models.module import Module, ModuleInstance
from ..extensions import db


@admin_bp.route('/modules', methods=['GET'])
@admin_required
def modules_list():
    modules = Module.query.order_by(Module.id.asc()).all()
    instances = ModuleInstance.query.all()

    # Группируем экземпляры по module_id
    instances_by_module = {}
    for inst in instances:
        instances_by_module.setdefault(inst.module_id, []).append(inst)

    return render_template(
        'admin/modules/all_modules.html',
        modules=modules,
        instances_by_module=instances_by_module
    )


_admin_module_classes = None


def _load_admin_module_classes():
    global _admin_module_classes
    if _admin_module_classes is not None:
        return _admin_module_classes
    _admin_module_classes = {}
    modules_path = os.path.join(os.path.dirname(__file__), 'modules')
    for filename in os.listdir(modules_path):
        if filename.endswith('.py') and filename != '__init__.py':
            module_name = f"app.admin.modules.{filename[:-3]}"
            try:
                module = importlib.import_module(module_name)
                for attr in dir(module):
                    obj = getattr(module, attr)
                    if isinstance(obj, type) and hasattr(obj, 'save_instance'):
                        _admin_module_classes[attr] = obj
            except Exception as e:
                print(f"Ошибка загрузки модуля {module_name}: {e}")
    return _admin_module_classes


@admin_bp.route('/modules/<int:module_id>/instance', defaults={'instance_id': None}, methods=['GET', 'POST'])
@admin_bp.route('/modules/<int:module_id>/instance/<int:instance_id>', methods=['GET', 'POST'])
@admin_required
def create_or_edit_module_instance(module_id, instance_id):
    module = Module.query.get_or_404(module_id)
    module_classes = _load_admin_module_classes()
    handler_class = module_classes.get(module.name)  # Имена классов совпадают с Module.name, напр. SliderModule

    # POST -> сохраняем через обработчик, если он есть
    if request.method == 'POST':
        if handler_class and hasattr(handler_class, 'save_instance'):
            return handler_class.save_instance(module_id, request.form, instance_id)
        flash('Обработчик модуля не найден.', 'danger')
        return redirect(url_for('admin.modules_list'))

    # GET -> загружаем данные для формы и выводим шаблон создания/редактирования
    context = {}
    if handler_class and hasattr(handler_class, 'load_instance_data'):
        context = handler_class.load_instance_data(instance_id)
    # Всегда добавляем module и instance_id в контекст
    context.update({
        'module': module,
        'instance_id': instance_id,
    })

    # Выберем шаблон: берем creation_template из БД (например, banner.html)
    template_name = module.creation_template or 'all_modules.html'
    template_path = f"admin/modules/{template_name}"
    return render_template(template_path, **context)


@admin_bp.route('/modules/<int:module_id>/instance/<int:instance_id>/delete', methods=['GET'])
@admin_required
def delete_module_instance(module_id, instance_id):
    """Удаление экземпляра модуля. Если у модуля есть делегат с del_instance — используем его."""
    module = Module.query.get_or_404(module_id)
    module_classes = _load_admin_module_classes()
    handler_class = module_classes.get(module.name)

    # Если у обработчика есть собственная логика удаления — используем её
    if handler_class and hasattr(handler_class, 'del_instance'):
        try:
            return handler_class.del_instance(module_id, instance_id)
        except Exception as e:
            flash(f'Ошибка удаления через обработчик: {e}', 'danger')

    # Универсальное удаление ModuleInstance
    instance = ModuleInstance.query.get_or_404(instance_id)
    try:
        db.session.delete(instance)
        db.session.commit()
        flash('Экземпляр модуля удалён.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка удаления: {e}', 'danger')
    return redirect(url_for('admin.modules_list'))