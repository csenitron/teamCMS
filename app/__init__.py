import os
import json
from flask import Flask
from .config import Config
from .extensions import db, migrate, csrf
from .views.main import main_bp
from .views.auth import auth_bp
from .admin import admin_bp
from .models.user import User
from .models.role import Role
from .models.category import Category
from .models.image import Image
from .models.directory import Directory
from .models.seo_settings import SEOSettings
from .models.order import Order
from .models.customer import Customer
from .models.audit_log import AuditLog
from .models.comparison import ComparisonItem, ComparisonList
from .models.menu import Menu, MenuItem
from .models.page import Page
from .models.product import Product
from .models.promocode import Promocode
from .models.referral import Referral
from .models.region import Region
from .models.review import Review
from .models.shipping import ShippingZone, ShippingMethod
from .models.tax import TaxRate
from .models.warehouse import Warehouse, WarehouseStock
from .models.wishlist import Wishlist, WishlistItem
from .models.attribute import Attribute
from .models.attributeValue import AttributeValue
from .models.productAttribute import ProductAttribute
# from .models.productOptions import *
from .models.module import Module, ModuleInstance
from .models.modules.slider import *
from .models.modules.menu import *
from flask_login import LoginManager
from flask import session
from flask_talisman import Talisman

login_manager = LoginManager()

def create_app():
    app = Flask(__name__, static_folder='static')
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    
    # Добавляем фильтр from_json для Jinja2
    @app.template_filter('from_json')
    def from_json_filter(value):
        if not value:
            return {}
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return {}

    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(user_id):
        auth_type = session.get('auth_type')
        if auth_type == 'admin':
            return User.query.get(int(user_id))
        if auth_type == 'customer':
            return Customer.query.get(int(user_id))
        # По умолчанию никого не аутентифицируем, чтобы не путать роли
        return None

    # Настройка CSP в Talisman
    csp = {
        'default-src': "'self'",
        'script-src': ["'self'", 'https://code.jquery.com', "'unsafe-inline'"],  # Разрешаем jQuery и inline-скрипты
        'style-src': ["'self'", "'unsafe-inline'"],  # Разрешаем inline-стили
        'img-src': ["'self'", 'data:'],  # Разрешаем data: изображения
        'script-src-elem': ["'self'", 'https://code.jquery.com', "'unsafe-inline'"],
        'style-src-elem': ["'self'", "'unsafe-inline'"],
        'connect-src': "'self'",
        'font-src': "'self'",
        'object-src': "'none'",
        'base-uri': "'self'",
        'form-action': "'self'",
    }

    talisman = Talisman(
        app,
        content_security_policy=csp,
        force_https=True,
    )

    @app.after_request
    def add_security_headers(response):
        # Оставляем только остальные заголовки
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer-when-downgrade'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        response.headers['X-Debug-CSP'] = 'Test-Header'  # Для отладки
        return response

    from .views.main import main_bp
    from .views.auth import auth_bp
    from .admin.views import admin_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    
    # Регистрируем команды
    from .cli_commands import register_commands
    register_commands(app)
    app.register_blueprint(admin_bp, url_prefix='/admin')

    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    with app.app_context():
        db.create_all()
    _register_context_processors(app)
    return app


def _build_main_menu_context():
    """Helper to build context for the main (header) menu.

    Returns a dict compatible with rendering `front/extations/menumodule.html`:
    { 'instance': ModuleInstance, 'menu_title', 'menu_style', 'show_icons', 'enable_videos', 'max_depth', 'menu_tree' }
    or None if no main menu configured.
    """
    try:
        from .models.modules.menu import MenuModuleInstance
        from .models.module import ModuleInstance as ModuleInstanceModel
        # Import frontend module class lazily to avoid circular imports at app init
        from .views.modules.menu import MenuModule as FrontMenuModule

        menu_instance = MenuModuleInstance.query.filter_by(is_main=True).first()
        if not menu_instance:
            return None
        module_instance = ModuleInstanceModel.query.get(menu_instance.module_instance_id)
        if not module_instance:
            return None

        data = FrontMenuModule.get_instance_data(module_instance)
        if not data or data.get('menu_tree') is None:
            return None

        return {
            'module_instance': module_instance,
            **data,
        }
    except Exception:
        return None


def _register_context_processors(app):
    @app.context_processor
    def inject_main_menu():
        # context processor is called per-request; if DB not ready, fail silently
        ctx = _build_main_menu_context()
        return { 'main_menu': ctx }
    return app