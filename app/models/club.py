from datetime import datetime
from .. import db

class ClubType(db.Model):
    """Types of golf clubs (e.g., Driver, Putter, Iron, etc.)"""
    __tablename__ = 'club_types'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, index=True)
    description = db.Column(db.String(255))
    
    def __repr__(self):
        return f'<ClubType {self.name}>'


class ClubBrand(db.Model):
    """Golf club manufacturers/brands"""
    __tablename__ = 'club_brands'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, index=True)
    logo_url = db.Column(db.String(255), nullable=True)
    website = db.Column(db.String(255), nullable=True)
    
    # Relationships
    clubs = db.relationship('Club', backref='brand', lazy='dynamic')
    
    def __repr__(self):
        return f'<ClubBrand {self.name}>'


class Club(db.Model):
    """Golf club model"""
    __tablename__ = 'clubs'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    description = db.Column(db.Text, nullable=True)
    purchase_link = db.Column(db.String(255), nullable=True)
    image_url = db.Column(db.String(255), nullable=True)
    release_year = db.Column(db.Integer, nullable=True)
    price = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_approved = db.Column(db.Boolean, default=False)
    
    # Foreign keys
    brand_id = db.Column(db.Integer, db.ForeignKey('club_brands.id'))
    club_type_id = db.Column(db.Integer, db.ForeignKey('club_types.id'))
    submitted_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Relationships
    club_type = db.relationship('ClubType', backref='clubs')
    submitter = db.relationship('User', foreign_keys=[submitted_by], backref='submitted_clubs')
    approver = db.relationship('User', foreign_keys=[approved_by], backref='approved_clubs')
    votes = db.relationship('Vote', backref='club', lazy='dynamic', 
                          primaryjoin="and_(Vote.votable_type=='club', "
                                      "Vote.votable_id==Club.id)")
    
    @property
    def vote_score(self):
        """Calculate the vote score (upvotes - downvotes)"""
        from .vote import Vote
        upvotes = Vote.query.filter_by(
            votable_type='club', 
            votable_id=self.id, 
            vote_type=True
        ).count()
        
        downvotes = Vote.query.filter_by(
            votable_type='club', 
            votable_id=self.id, 
            vote_type=False
        ).count()
        
        return upvotes - downvotes
    
    @property
    def upvote_count(self):
        """Count of upvotes"""
        from .vote import Vote
        return Vote.query.filter_by(
            votable_type='club', 
            votable_id=self.id, 
            vote_type=True
        ).count()
    
    @property
    def downvote_count(self):
        """Count of downvotes"""
        from .vote import Vote
        return Vote.query.filter_by(
            votable_type='club', 
            votable_id=self.id, 
            vote_type=False
        ).count()
    
    def __repr__(self):
        return f'<Club {self.name}>'


# Initialize default club types
def init_club_types():
    default_types = [
        ('Driver', 'Used for long-distance tee shots'),
        ('Fairway Wood', 'Used for long shots from the fairway'),
        ('Hybrid', 'Combines features of woods and irons'),
        ('Iron', 'Used for approaching the green'),
        ('Wedge', 'Used for short shots near the green'),
        ('Putter', 'Used on the green to roll the ball into the hole')
    ]
    
    for name, description in default_types:
        club_type = ClubType.query.filter_by(name=name).first()
        if club_type is None:
            club_type = ClubType(name=name, description=description)
            db.session.add(club_type)
    
    db.session.commit()