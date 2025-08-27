from datetime import datetime
from ..extensions import db
from .base import BaseModel
from .role import Role
from flask_login import UserMixin
import bcrypt
class User(BaseModel, UserMixin):
    __tablename__ = 'users'


    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    role = db.relationship('Role', backref='users')

    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password.encode('utf-8'))

    @property
    def is_admin(self):
        return self.role_id == 1

def hash_password(password):
    """Хеширует пароль с помощью bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def addUser(username, email, password, role_id):
    password_hash = hash_password(password)
    user = User(username=username, email=email, password=password_hash, role_id=role_id)
    db.session.add(user)
    db.session.commit()
    return user

def getUser(user_id):
    user = User.query.filter_by(id=user_id).first()
    return user

def getUsers():
    users = User.query.all()
    return users

def editUser(user_id,username, email, password, role_id):

    user = User.query.filter_by(id = user_id).first()
    print(user)
    user.username = username
    user.email = email
    if password:
        password_hash = hash_password(password)
        user.password = password_hash
    user.role_id = role_id
    db.session.commit()
    return user

def deleteUser(username):
    user = User.query.filter_by(username=username).first()
    db.session.delete(user)
    db.session.commit()
    return True