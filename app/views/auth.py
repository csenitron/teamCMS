from flask import Blueprint, request, render_template, redirect, url_for, session, flash
from flask_login import login_user, current_user, logout_user, login_required
from urllib.parse import urlparse, urljoin
from ..extensions import db
from ..models.user import User
import bcrypt

auth_bp = Blueprint('auth', __name__)


def is_safe_url(target):
    """Проверяет, что URL безопасен для редиректа."""
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Если пользователь авторизован как User, перенаправляем в админ-панель
    if current_user.is_authenticated and current_user.__class__.__name__ == 'User':
        return redirect(url_for('admin.admin_index'))

    # Если пользователь авторизован как Customer, перенаправляем на главную
    if current_user.is_authenticated and current_user.__class__.__name__ == 'Customer':
        next_url = request.args.get('next') or url_for('main.index')
        if is_safe_url(next_url):
            return redirect(next_url)
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        next_url = request.form.get('next') or request.args.get('next') or url_for('admin.admin_index')

        if not username or not password:

            flash('Логин и пароль обязательны.', 'error')
            return render_template('login.html', next=next_url)

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            print(f"Пользователь {username} успешно авторизован")
            login_user(user)
            flash('Вход выполнен успешно!', 'success')
            # Отмечаем тип авторизации как 'admin'
            session['auth_type'] = 'admin'
            if is_safe_url(next_url):
                return redirect(next_url)
            return redirect(url_for('admin.admin_index'))
        else:
            if user:
                print(f"Неверный пароль для пользователя {username}")
            else:
                print(f"Пользователь {username} не найден")
            flash('Неверный логин или пароль.', 'error')
            return render_template('login.html', next=next_url)

    # Для GET-запроса передаём next из параметров
    next_url = request.args.get('next') or url_for('admin.admin_index')
    return render_template('login.html', next=next_url)

@auth_bp.route('/logout')
@login_required
def logout():
    """Выход пользователя из системы"""
    # Чистим тип авторизации
    session.pop('auth_type', None)
    logout_user()
    flash('Вы успешно вышли из системы.', 'success')
    return redirect(url_for('auth.login'))
