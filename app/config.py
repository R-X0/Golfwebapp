import os
from datetime import timedelta

class Config:
    """Base config."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-for-development-only')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@localhost/pars_golf')
    
    # Golf API Configuration
    GOLF_API_KEY = os.environ.get('GOLF_API_KEY', '')
    GOLF_API_BASE_URL = 'https://golf-api.example.com'  # Replace with actual GolfAPI.io URL
    
    # OAuth Configuration
    GOOGLE_ID = os.environ.get('GOOGLE_ID', '')
    GOOGLE_SECRET = os.environ.get('GOOGLE_SECRET', '')
    
    # JWT Configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-dev-key-for-development-only')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # File Upload Configuration
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
    
    # Pars.Golf Specific Configuration
    ITEMS_PER_PAGE = 20


class DevelopmentConfig(Config):
    """Development config."""
    DEBUG = True
    SQLALCHEMY_ECHO = True


class TestingConfig(Config):
    """Testing config."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:postgres@localhost/pars_golf_test'
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    """Production config."""
    DEBUG = False
    # Use stronger secret keys in production
    SECRET_KEY = os.environ.get('SECRET_KEY')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    
    # We'd likely use a different database URL in production
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')


config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig
}