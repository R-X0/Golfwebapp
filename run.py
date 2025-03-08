import os
from app import create_app, db
from app.models.user import User, Role, init_roles
from app.models.club import Club, ClubBrand, ClubType, init_club_types
from app.models.player import Player, PlayerAchievement
from app.models.course import Course, CourseHole
from app.models.vote import Vote, Comment
from flask_migrate import Migrate

app = create_app(os.getenv('FLASK_CONFIG', 'development'))
migrate = Migrate(app, db)

@app.shell_context_processor
def make_shell_context():
    return dict(
        app=app,
        db=db,
        User=User,
        Role=Role,
        Club=Club,
        ClubBrand=ClubBrand,
        ClubType=ClubType,
        Player=Player,
        PlayerAchievement=PlayerAchievement,
        Course=Course,
        CourseHole=CourseHole,
        Vote=Vote,
        Comment=Comment
    )

@app.cli.command("init-db")
def init_db():
    """Initialize the database with initial data"""
    # Create database tables
    db.create_all()
    
    # Initialize roles
    init_roles()
    
    # Initialize club types
    init_club_types()
    
    print("Database initialized with initial data.")

@app.cli.command("create-admin")
def create_admin():
    """Create an admin user"""
    import getpass
    
    # Initialize roles if they don't exist
    init_roles()
    
    # Get admin role
    admin_role = Role.query.filter_by(name=Role.ADMIN_ROLE).first()
    if not admin_role:
        print("Admin role not found. Please run init-db first.")
        return
    
    # Get user input
    username = input("Admin username: ")
    email = input("Admin email: ")
    password = getpass.getpass("Admin password: ")
    confirm_password = getpass.getpass("Confirm password: ")
    
    if password != confirm_password:
        print("Passwords do not match.")
        return
    
    # Check if user already exists
    if User.query.filter_by(username=username).first():
        print(f"User with username '{username}' already exists.")
        return
    
    if User.query.filter_by(email=email).first():
        print(f"User with email '{email}' already exists.")
        return
    
    # Create admin user
    admin = User(
        username=username,
        email=email,
        role=admin_role
    )
    admin.password = password
    
    db.session.add(admin)
    db.session.commit()
    
    print(f"Admin user '{username}' created successfully.")

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)