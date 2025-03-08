from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_oauthlib.client import OAuth
from flask_cors import CORS

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
oauth = OAuth()
cors = CORS()

def create_app(config_name='development'):
    app = Flask(__name__)
    
    # Load configuration
    from .config import config_by_name
    app.config.from_object(config_by_name[config_name])
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    oauth.init_app(app)
    cors.init_app(app)
    
    # Set up login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    
    # Register blueprints
    from .api.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')
    
    from .api.clubs import clubs as clubs_blueprint
    app.register_blueprint(clubs_blueprint, url_prefix='/api/clubs')
    
    from .api.players import players as players_blueprint
    app.register_blueprint(players_blueprint, url_prefix='/api/players')
    
    from .api.courses import courses as courses_blueprint
    app.register_blueprint(courses_blueprint, url_prefix='/api/courses')
    
    from .api.votes import votes as votes_blueprint
    app.register_blueprint(votes_blueprint, url_prefix='/api/votes')
    
    # Shell context
    @app.shell_context_processor
    def make_shell_context():
        return dict(app=app, db=db)
    
    return app