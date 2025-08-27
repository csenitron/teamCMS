from flask import redirect, url_for, request, flash
from flask_login import current_user, login_required
from functools import wraps
from . import admin_bp
import logging
def admin_required(f):
    """Декоратор, разрешающий доступ только админам (User)."""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        logging.debug(f"Admin route accessed, user: {current_user.__class__.__name__ if current_user.is_authenticated else 'None'}")
        if current_user.__class__.__name__ != 'User':
            logging.debug("User is not admin, redirecting to main.index")
            flash('Доступ разрешён только администраторам.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function