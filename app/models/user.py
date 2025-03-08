from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime
from .. import db, login_manager
import uuid

class Role(db.Model):
    """User roles for role-based access control"""
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    description = db.Column(db.String(255))
    
    # Define default roles
    USER_ROLE = 'user'
    EMPLOYEE_ROLE = 'employee'
    ADMIN_ROLE = 'admin'
    PLAYER_ROLE = 'player'  # For VIP/Pro players
    
    def __repr__(self):
        return f'<Role {self.name}>'


class User(UserMixin, db.Model):
    """User model for authentication and profile information"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(64), unique=True, index=True)
    email = db.Column(db.String(120), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    profile_picture = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # OAuth related fields
    oauth_provider = db.Column(db.String(20), nullable=True)
    oauth_id = db.Column(db.String(255), nullable=True)
    
    # Role relationship
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    role = db.relationship('Role', backref=db.backref('users', lazy='dynamic'))
    
    # Relationships
    votes = db.relationship('Vote', backref='user', lazy='dynamic')
    
    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')
    
    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @property
    def profile_url(self):
        """Returns the user's profile URL in the format pars.golf/@username"""
        return f'pars.golf/@{self.username}'
    
    def has_role(self, role_name):
        """Check if user has a specific role"""
        return self.role and self.role.name == role_name
    
    def is_admin(self):
        """Check if user is admin"""
        return self.has_role(Role.ADMIN_ROLE)
    
    def is_employee(self):
        """Check if user is employee"""
        return self.has_role(Role.EMPLOYEE_ROLE) or self.is_admin()
    
    def is_player(self):
        """Check if user is a VIP/Pro player"""
        return self.has_role(Role.PLAYER_ROLE)
    
    def __repr__(self):
        return f'<User {self.username}>'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Create initial roles
def init_roles():
    roles = {
        Role.USER_ROLE: 'Regular user with voting and submission privileges',
        Role.EMPLOYEE_ROLE: 'Employee with content moderation capabilities',
        Role.ADMIN_ROLE: 'Administrator with full system access',
        Role.PLAYER_ROLE: 'Professional or VIP golf player'
    }
    
    for role_name, description in roles.items():
        role = Role.query.filter_by(name=role_name).first()
        if role is None:
            role = Role(name=role_name, description=description)
            db.session.add(role)
    
    db.session.commit()