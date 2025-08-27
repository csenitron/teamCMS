import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev")
    WTF_CSRF_SECRET_KEY = SECRET_KEY
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{os.environ.get('DB_USER')}:{os.environ.get('DB_PASSWORD')}@{os.environ.get('DB_HOST')}:{os.environ.get('DB_PORT')}/{os.environ.get('DB_NAME')}?charset=utf8mb4"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
    LOGIN_DISABLED = False  # Включаем проверку аутентификации
    LOGIN_VIEW = 'auth.login'  # Маршрут для страницы логина (замените на ваш)
    LOGIN_MESSAGE = 'Пожалуйста, войдите, чтобы получить доступ к этой странице.'
    LOGIN_MESSAGE_CATEGORY = 'warning'  # Категория сообщения для flash
    SESSION_PROTECTION = 'strong'  # Строгая защита сессии