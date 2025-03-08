from datetime import datetime
from .. import db

class Vote(db.Model):
    """Voting model for clubs, players, and courses"""
    __tablename__ = 'votes'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    votable_type = db.Column(db.String(20))  # 'club', 'player', or 'course'
    votable_id = db.Column(db.Integer)
    vote_type = db.Column(db.Boolean)  # True for upvote, False for downvote
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Ensure a user can only vote once per item
    __table_args__ = (
        db.UniqueConstraint('user_id', 'votable_type', 'votable_id', name='unique_user_vote'),
    )
    
    def __repr__(self):
        vote_direction = "up" if self.vote_type else "down"
        return f'<Vote {vote_direction} on {self.votable_type} {self.votable_id} by User {self.user_id}>'


class Comment(db.Model):
    """Comments on votable items"""
    __tablename__ = 'comments'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    commentable_type = db.Column(db.String(20))  # 'club', 'player', or 'course'
    commentable_id = db.Column(db.Integer)
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = db.Column(db.Boolean, default=False)
    
    # User relationship
    user = db.relationship('User', backref='comments')
    
    # Parent-child relationship for nested comments
    parent_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=True)
    replies = db.relationship('Comment', 
                             backref=db.backref('parent', remote_side=[id]),
                             lazy='dynamic')
    
    def __repr__(self):
        return f'<Comment by User {self.user_id} on {self.commentable_type} {self.commentable_id}>'