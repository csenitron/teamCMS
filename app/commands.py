from app.extensions import db
from app.models.user import User
from app.models.role import Role
import bcrypt

# Создаем приложение и контекст
app = create_app()
with app.app_context():
    # Проверяем, есть ли роль admin
    admin_role = Role.query.filter_by(name='admin').first()
    if not admin_role:
        admin_role = Role(name='admin', permissions={})
        db.session.add(admin_role)
        db.session.commit()
        print("Role 'admin' created.")

    # Проверяем, есть ли пользователь admin
    admin_user = User.query.filter_by(username='admin').first()
    if admin_user:
        print("User 'admin' уже существует.")
    else:
        # Создаем админа
        username = 'admin'
        email = 'admin@example.com'
        password = 'secret'  # В реальном проекте используйте более надежный пароль

        # Хэшируем пароль
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        admin_user = User(username=username, email=email, password=hashed, role_id=admin_role.id)
        db.session.add(admin_user)
        db.session.commit()
        print("Admin user created: username=admin, password=secret")

