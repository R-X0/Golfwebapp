from datetime import datetime
from .. import db

class Player(db.Model):
    """Golf player model for professionals and notable players"""
    __tablename__ = 'players'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    profile_picture = db.Column(db.String(255), nullable=True)
    country = db.Column(db.String(64), nullable=True)
    birthdate = db.Column(db.Date, nullable=True)
    turned_pro = db.Column(db.Integer, nullable=True)  # Year turned professional
    bio = db.Column(db.Text, nullable=True)
    website = db.Column(db.String(255), nullable=True)
    twitter_handle = db.Column(db.String(64), nullable=True)
    instagram_handle = db.Column(db.String(64), nullable=True)
    world_ranking = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_approved = db.Column(db.Boolean, default=False)
    
    # Foreign keys
    submitted_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    user_account_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # If player has a user account
    
    # Relationships
    submitter = db.relationship('User', foreign_keys=[submitted_by], backref='submitted_players')
    approver = db.relationship('User', foreign_keys=[approved_by], backref='approved_players')
    user_account = db.relationship('User', foreign_keys=[user_account_id], backref='player_profile')
    achievements = db.relationship('PlayerAchievement', backref='player', lazy='dynamic')
    votes = db.relationship('Vote', backref='player', lazy='dynamic', 
                          primaryjoin="and_(Vote.votable_type=='player', "
                                      "Vote.votable_id==Player.id)")
    
    @property
    def vote_score(self):
        """Calculate the vote score (upvotes - downvotes)"""
        from .vote import Vote
        upvotes = Vote.query.filter_by(
            votable_type='player', 
            votable_id=self.id, 
            vote_type=True
        ).count()
        
        downvotes = Vote.query.filter_by(
            votable_type='player', 
            votable_id=self.id, 
            vote_type=False
        ).count()
        
        return upvotes - downvotes
    
    @property
    def upvote_count(self):
        """Count of upvotes"""
        from .vote import Vote
        return Vote.query.filter_by(
            votable_type='player', 
            votable_id=self.id, 
            vote_type=True
        ).count()
    
    @property
    def downvote_count(self):
        """Count of downvotes"""
        from .vote import Vote
        return Vote.query.filter_by(
            votable_type='player', 
            votable_id=self.id, 
            vote_type=False
        ).count()
    
    @property
    def age(self):
        """Calculate player's age"""
        if self.birthdate:
            today = datetime.now().date()
            return today.year - self.birthdate.year - (
                (today.month, today.day) < (self.birthdate.month, self.birthdate.day)
            )
        return None
    
    def __repr__(self):
        return f'<Player {self.name}>'


class PlayerAchievement(db.Model):
    """Achievements for golf players (tournaments won, awards, etc.)"""
    __tablename__ = 'player_achievements'
    
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'))
    title = db.Column(db.String(128))
    year = db.Column(db.Integer)
    description = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f'<PlayerAchievement {self.title} ({self.year})>'