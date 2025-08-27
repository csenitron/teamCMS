import json
import bcrypt

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from .forms import UserForm
from ..extensions import db
from . import admin_bp, admin_required
from ..models.user import *
from ..models.role import *
from datetime import datetime
from sqlalchemy.exc import IntegrityError
import logging

logging.basicConfig(level=logging.DEBUG)

@admin_bp.route('/users', methods=['GET', 'POST'])
@admin_required
def users():
    try:
        if request.method == 'POST':

            user_id = request.form.get('user_id')
            print(user_id)
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            role = request.form.get('role')

            if not user_id:  # Добавление нового пользователя
                print('Создание')
                addUser(username, email, password, role)
                return redirect(url_for('admin.users'))
            else:  # Редактирование существующего пользователя
                editUser(user_id, username, email, password, role)
                return redirect(url_for('admin.users'))

        elif request.method == 'GET':
            user_id = request.args.get('user_id')
            print(user_id)
            if user_id:
                user = getUser(user_id)
                us = {
                    'username': user.username,
                    'email': user.email,
                    'role': user.role_id
                }
                return jsonify(us), 200  # Сериализуем словарь в JSON
            else:
                form = UserForm()
                users_list = getUsers()
                return render_template('admin/users_list.html', users=users_list, form=form)

    except IntegrityError as e:
        # Обработка ошибки дублирования email
        logging.error(f"Database error: {str(e)}")
        return jsonify({'error': 'Email already exists'}), 400
    except Exception as e:
        # Обработка других ошибок
        logging.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

    return jsonify({'error': 'Method not allowed'}), 405



