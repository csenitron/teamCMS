import os
import re
import uuid

from flask import current_app


def save_image_file(file, sanitized_filename=None):
    # Определяем имя файла, если передано преобразованное название
    original_filename = file.filename
    filename = sanitized_filename if sanitized_filename else original_filename

    # Извлекаем расширение файла
    ext = filename.rsplit('.', 1)[1].lower()

    # Оставляем первые 10 символов от имени файла (без расширения) для наглядности
    base_name = filename.rsplit('.', 1)[0][:20]  # Не больше 10 символов
    base_name = re.sub(r'[^a-zA-Z0-9_-]', '_', base_name)  # Убираем недопустимые символы

    # Генерируем уникальное имя
    unique_filename = f"{base_name}_{uuid.uuid4().hex[:8]}.{ext}"

    # Путь загрузки
    upload_path = current_app.config['UPLOAD_FOLDER']
    file.save(os.path.join(upload_path, unique_filename))

    return unique_filename