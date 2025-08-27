import re

import unicodedata

from ..extensions import db

class BaseModel(db.Model):
    __abstract__ = True
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    @staticmethod
    def slugify(value):
        """
        Простейшая функция для генерации slug:
        - Приводим к нижнему регистру
        - Удаляем диакритические знаки (unicode normalization)
        - Убираем все небуквенно-цифровые символы на дефисы
        - Убираем лишние дефисы
        """
        value = unicodedata.normalize('NFKD', value)
        value = value.encode('ascii', 'ignore').decode('ascii')  # убрать не-ASCII символы
        value = re.sub(r'[^a-zA-Z0-9]+', '-', value.lower())
        value = value.strip('-')
        return value