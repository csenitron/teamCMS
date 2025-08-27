from flask import Blueprint

# Создаём Blueprint для админки
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


from .module_views import *
from .pages_views import *
from .posts_views import *
from .users_views import *
from .views import *
