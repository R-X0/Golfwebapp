from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, current_app, session
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime

# Helper function for URL parsing compatibility with different Werkzeug versions
def safe_url_parse(url):
    """Parse a URL safely across different Werkzeug versions"""
    try:
        # Try newer Werkzeug versions
        from werkzeug.urls import parse_url
        return parse_url(url)
    except ImportError:
        # Fall back to older versions
        from werkzeug.urls import url_parse
        return url_parse(url)

from .. import db, oauth
from ..models.user import User, Role, init_roles

auth = Blueprint('auth', __name__)

# OAuth setup for Google with Authlib
def setup_oauth(app):
    oauth.register(
        name='google',
        client_id=app.config.get('GOOGLE_ID'),
        client_secret=app.config.get('GOOGLE_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )

@auth.record_once
def on_load(state):
    app = state.app
    setup_oauth(app)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        # Handle form submission
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember', False) == 'true'
        
        user = User.query.filter_by(email=email).first()
        
        if user is not None and user.verify_password(password):
            login_user(user, remember=remember)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            next_page = request.args.get('next')
            if not next_page or safe_url_parse(next_page).netloc != '':
                next_page = url_for('main.index')
            
            return redirect(next_page)
        
        flash('Invalid email or password.')
    
    return render_template('auth/login.html')


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('main.index'))


@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        # Get form data
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate form data
        if password != confirm_password:
            flash('Passwords do not match.')
            return render_template('auth/register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered.')
            return render_template('auth/register.html')
        
        if User.query.filter_by(username=username).first():
            flash('Username already taken.')
            return render_template('auth/register.html')
        
        # Get the user role
        user_role = Role.query.filter_by(name=Role.USER_ROLE).first()
        if not user_role:
            # Initialize roles if they don't exist
            init_roles()
            user_role = Role.query.filter_by(name=Role.USER_ROLE).first()
        
        # Create new user
        user = User(
            username=username,
            email=email,
            role=user_role
        )
        user.password = password
        
        db.session.add(user)
        db.session.commit()
        
        flash('You have successfully registered! Please log in.')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')


# OAuth routes
@auth.route('/login/google')
def google_login():
    redirect_uri = url_for('auth.google_authorized', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth.route('/login/google/callback')
def google_authorized():
    try:
        token = oauth.google.authorize_access_token()
        resp = oauth.google.parse_id_token(token)
        user_info = resp
    except Exception as e:
        flash(f'Access denied: {str(e)}')
        return redirect(url_for('auth.login'))
    
    # Check if user exists with this OAuth ID
    user = User.query.filter_by(oauth_id=user_info['sub'], oauth_provider='google').first()
    
    if not user:
        # Check if user exists with this email
        user = User.query.filter_by(email=user_info['email']).first()
        
        if user:
            # Update existing user with OAuth info
            user.oauth_id = user_info['sub']
            user.oauth_provider = 'google'
        else:
            # Create new user
            username = user_info['email'].split('@')[0]
            base_username = username
            counter = 1
            
            # Ensure username is unique
            while User.query.filter_by(username=username).first():
                username = f"{base_username}{counter}"
                counter += 1
            
            # Get the user role
            user_role = Role.query.filter_by(name=Role.USER_ROLE).first()
            if not user_role:
                # Initialize roles if they don't exist
                init_roles()
                user_role = Role.query.filter_by(name=Role.USER_ROLE).first()
            
            user = User(
                username=username,
                email=user_info['email'],
                oauth_id=user_info['sub'],
                oauth_provider='google',
                profile_picture=user_info.get('picture'),
                role=user_role
            )
            
            db.session.add(user)
    
    user.last_login = datetime.utcnow()
    db.session.commit()
    
    login_user(user)
    flash('You have been logged in.')
    
    next_page = request.args.get('next')
    if not next_page or safe_url_parse(next_page).netloc != '':
        next_page = url_for('main.index')
    
    return redirect(next_page)


# API routes for authentication
@auth.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    user = User.query.filter_by(email=email).first()
    
    if user is not None and user.verify_password(password):
        login_user(user)
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'profile_url': user.profile_url,
                'role': user.role.name
            }
        }), 200
    
    return jsonify({
        'success': False,
        'message': 'Invalid email or password'
    }), 401


@auth.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    # Validate data
    if User.query.filter_by(email=email).first():
        return jsonify({
            'success': False,
            'message': 'Email already registered'
        }), 400
    
    if User.query.filter_by(username=username).first():
        return jsonify({
            'success': False,
            'message': 'Username already taken'
        }), 400
    
    # Get the user role
    user_role = Role.query.filter_by(name=Role.USER_ROLE).first()
    if not user_role:
        # Initialize roles if they don't exist
        init_roles()
        user_role = Role.query.filter_by(name=Role.USER_ROLE).first()
    
    # Create new user
    user = User(
        username=username,
        email=email,
        role=user_role
    )
    user.password = password
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'User registered successfully'
    }), 201


@auth.route('/api/logout', methods=['POST'])
@login_required
def api_logout():
    logout_user()
    return jsonify({
        'success': True,
        'message': 'Logged out successfully'
    }), 200


@auth.route('/api/user', methods=['GET'])
@login_required
def api_user():
    return jsonify({
        'id': current_user.id,
        'username': current_user.username,
        'email': current_user.email,
        'profile_url': current_user.profile_url,
        'profile_picture': current_user.profile_picture,
        'role': current_user.role.name
    }), 200