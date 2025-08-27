#!/usr/bin/env python3
"""
Скрипт для отладки авторизации админа
Запускать: python debug_admin_auth.py
"""

from app import create_app
from app.extensions import db
from app.models.user import User, addUser
from app.models.role import Role
import bcrypt

def debug_admin_auth():
    """Отладка авторизации админа"""
    app = create_app()
    
    with app.app_context():
        print("=== DEBUG ADMIN AUTH ===")
        
        # Проверяем роли
        roles = Role.query.all()
        print(f"Roles in database: {len(roles)}")
        for role in roles:
            print(f"  Role {role.id}: {role.name}")
        
        # Проверяем пользователей
        users = User.query.all()
        print(f"\nUsers in database: {len(users)}")
        for user in users:
            print(f"  User {user.id}: {user.username} (role_id: {user.role_id})")
            print(f"    Email: {user.email}")
            print(f"    Password hash: {user.password[:20]}...")
        
        # Создаем тестового админа, если его нет
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            print("\n=== CREATING TEST ADMIN ===")
            try:
                # Проверяем, есть ли роль админа
                admin_role = Role.query.filter_by(name='Admin').first()
                if not admin_role:
                    print("Creating admin role...")
                    admin_role = Role(name='Admin', description='Administrator')
                    db.session.add(admin_role)
                    db.session.commit()
                    print(f"Created admin role with ID: {admin_role.id}")
                
                # Создаем админа
                admin_user = addUser(
                    username='admin',
                    email='admin@example.com',
                    password='admin123',
                    role_id=admin_role.id
                )
                print(f"Created admin user: {admin_user.username}")
                print(f"Admin user ID: {admin_user.id}")
                print(f"Admin role ID: {admin_user.role_id}")
                
            except Exception as e:
                print(f"Error creating admin: {e}")
                db.session.rollback()
        else:
            print(f"\nAdmin user exists: {admin_user.username}")
            print(f"Admin user ID: {admin_user.id}")
            print(f"Admin role ID: {admin_user.role_id}")
        
        # Тестируем проверку пароля
        if admin_user:
            print(f"\n=== TESTING PASSWORD CHECK ===")
            test_password = 'admin123'
            print(f"Testing password: {test_password}")
            
            # Проверяем пароль
            is_valid = admin_user.check_password(test_password)
            print(f"Password check result: {is_valid}")
            
            # Проверяем хеш пароля
            password_hash = admin_user.password
            print(f"Password hash: {password_hash}")
            
            # Тестируем bcrypt напрямую
            try:
                bcrypt_result = bcrypt.checkpw(test_password.encode('utf-8'), password_hash.encode('utf-8'))
                print(f"Direct bcrypt check: {bcrypt_result}")
            except Exception as e:
                print(f"Bcrypt error: {e}")

if __name__ == "__main__":
    debug_admin_auth() 