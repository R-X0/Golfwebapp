from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.urls import url_parse
from datetime import datetime

from .. import db, oauth
from ..models.user import User, Role, init_roles

auth = Blueprint('auth', __name__)

# OAuth setup for Google
google = oauth.remote_app(
    'google',
    consumer_key=lambda: current_app.config.get('GOOGLE_ID'),
    consumer_secret=lambda: current_app.config.get('GOOGLE_SECRET'),
    request_token_params={
        'scope': 'email profile'
    },
    base_url='https://www.googleapis.com/oauth2/v1/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://accounts.google.com/o/oauth2/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth'
)


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
            if not next_page or url_parse(next_page).netloc != '':
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
    return google.authorize(callback=url_for('auth.google_authorized', _external=True))


@auth.route('/login/google/callback')
def google_authorized():
    resp = google.authorized_response()
    if resp is None or resp.get('access_token') is None:
        flash('Access denied: reason={0} error={1}'.format(
            request.args['error_reason'],
            request.args['error_description']
        ))
        return redirect(url_for('auth.login'))
    
    # Get user info from Google
    me = google.get('userinfo')
    
    # Check if user exists with this OAuth ID
    user = User.query.filter_by(oauth_id=me.data['id'], oauth_provider='google').first()
    
    if not user:
        # Check if user exists with this email
        user = User.query.filter_by(email=me.data['email']).first()
        
        if user:
            # Update existing user with OAuth info
            user.oauth_id = me.data['id']
            user.oauth_provider = 'google'
        else:
            # Create new user
            username = me.data['email'].split('@')[0]
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
                email=me.data['email'],
                oauth_id=me.data['id'],
                oauth_provider='google',
                profile_picture=me.data.get('picture'),
                role=user_role
            )
            
            db.session.add(user)
    
    user.last_login = datetime.utcnow()
    db.session.commit()
    
    login_user(user)
    flash('You have been logged in.')
    
    next_page = request.args.get('next')
    if not next_page or url_parse(next_page).netloc != '':
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