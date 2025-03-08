from datetime import datetime
from .. import db

class Course(db.Model):
    """Golf course model"""
    __tablename__ = 'courses'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    description = db.Column(db.Text, nullable=True)
    address = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(64), nullable=True)
    state = db.Column(db.String(64), nullable=True)
    country = db.Column(db.String(64), nullable=True)
    postal_code = db.Column(db.String(20), nullable=True)
    website = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(128), nullable=True)
    
    # Course details
    year_built = db.Column(db.Integer, nullable=True)
    architect = db.Column(db.String(128), nullable=True)
    course_type = db.Column(db.String(64), nullable=True)  # Public, Private, Resort, etc.
    num_holes = db.Column(db.Integer, default=18)
    par = db.Column(db.Integer, nullable=True)
    length_yards = db.Column(db.Integer, nullable=True)
    
    # Location data
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    
    # Media
    image_url = db.Column(db.String(255), nullable=True)
    logo_url = db.Column(db.String(255), nullable=True)
    
    # Golf API data
    golf_api_id = db.Column(db.String(64), nullable=True, unique=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_approved = db.Column(db.Boolean, default=False)
    
    # Foreign keys
    submitted_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Relationships
    submitter = db.relationship('User', foreign_keys=[submitted_by], backref='submitted_courses')
    approver = db.relationship('User', foreign_keys=[approved_by], backref='approved_courses')
    holes = db.relationship('CourseHole', backref='course', lazy='dynamic')
    votes = db.relationship('Vote', backref='course', lazy='dynamic', 
                          primaryjoin="and_(Vote.votable_type=='course', "
                                      "Vote.votable_id==Course.id)")
    
    @property
    def vote_score(self):
        """Calculate the vote score (upvotes - downvotes)"""
        from .vote import Vote
        upvotes = Vote.query.filter_by(
            votable_type='course', 
            votable_id=self.id, 
            vote_type=True
        ).count()
        
        downvotes = Vote.query.filter_by(
            votable_type='course', 
            votable_id=self.id, 
            vote_type=False
        ).count()
        
        return upvotes - downvotes
    
    @property
    def upvote_count(self):
        """Count of upvotes"""
        from .vote import Vote
        return Vote.query.filter_by(
            votable_type='course', 
            votable_id=self.id, 
            vote_type=True
        ).count()
    
    @property
    def downvote_count(self):
        """Count of downvotes"""
        from .vote import Vote
        return Vote.query.filter_by(
            votable_type='course', 
            votable_id=self.id, 
            vote_type=False
        ).count()
    
    @property
    def full_address(self):
        """Return the full address as a string"""
        components = [self.address, self.city, self.state, self.postal_code, self.country]
        return ', '.join(filter(None, components))
    
    def __repr__(self):
        return f'<Course {self.name}>'


class CourseHole(db.Model):
    """Individual holes on a golf course"""
    __tablename__ = 'course_holes'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'))
    hole_number = db.Column(db.Integer)
    par = db.Column(db.Integer)
    yards = db.Column(db.Integer, nullable=True)
    handicap = db.Column(db.Integer, nullable=True)  # Difficulty ranking
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(255), nullable=True)
    
    def __repr__(self):
        return f'<CourseHole {self.course.name} #{self.hole_number}>'