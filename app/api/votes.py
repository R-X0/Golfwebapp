from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime

from .. import db
from ..models.vote import Vote, Comment
from ..models.club import Club
from ..models.player import Player
from ..models.course import Course

votes = Blueprint('votes', __name__)

@votes.route('/', methods=['POST'])
@login_required
def add_vote():
    """Add or update a vote on a votable item (club, player, course)"""
    data = request.get_json()
    
    # Validate data
    votable_type = data.get('votable_type')
    votable_id = data.get('votable_id')
    vote_type = data.get('vote_type')  # 'up', 'down', or null (to remove vote)
    
    if not votable_type or not votable_id:
        return jsonify({
            'success': False,
            'message': 'votable_type and votable_id are required'
        }), 400
    
    if votable_type not in ['club', 'player', 'course']:
        return jsonify({
            'success': False,
            'message': 'Invalid votable_type. Must be "club", "player", or "course"'
        }), 400
    
    if vote_type not in ['up', 'down', None]:
        return jsonify({
            'success': False,
            'message': 'Invalid vote_type. Must be "up", "down", or null to remove vote'
        }), 400
    
    # Get the item being voted on
    item = None
    if votable_type == 'club':
        item = Club.query.get_or_404(votable_id)
    elif votable_type == 'player':
        item = Player.query.get_or_404(votable_id)
    elif votable_type == 'course':
        item = Course.query.get_or_404(votable_id)
    
    # Check if item is approved
    if not item.is_approved:
        return jsonify({
            'success': False,
            'message': f'Cannot vote on unapproved {votable_type}'
        }), 400
    
    # Check if user has already voted
    existing_vote = Vote.query.filter_by(
        user_id=current_user.id,
        votable_type=votable_type,
        votable_id=votable_id
    ).first()
    
    if vote_type is None:
        # Remove vote if it exists
        if existing_vote:
            db.session.delete(existing_vote)
            db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Vote removed',
            'vote_score': item.vote_score,
            'upvotes': item.upvote_count,
            'downvotes': item.downvote_count
        })
    
    vote_value = vote_type == 'up'
    
    if existing_vote:
        # Update existing vote
        existing_vote.vote_type = vote_value
    else:
        # Create new vote
        vote = Vote(
            user_id=current_user.id,
            votable_type=votable_type,
            votable_id=votable_id,
            vote_type=vote_value
        )
        db.session.add(vote)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Vote {"up" if vote_value else "down"} recorded',
        'vote_score': item.vote_score,
        'upvotes': item.upvote_count,
        'downvotes': item.downvote_count
    })

@votes.route('/comments', methods=['POST'])
@login_required
def add_comment():
    """Add a comment to a votable item (club, player, course)"""
    data = request.get_json()
    
    # Validate data
    commentable_type = data.get('commentable_type')
    commentable_id = data.get('commentable_id')
    content = data.get('content')
    parent_id = data.get('parent_id')  # For replies to other comments
    
    if not commentable_type or not commentable_id or not content:
        return jsonify({
            'success': False,
            'message': 'commentable_type, commentable_id, and content are required'
        }), 400
    
    if commentable_type not in ['club', 'player', 'course']:
        return jsonify({
            'success': False,
            'message': 'Invalid commentable_type. Must be "club", "player", or "course"'
        }), 400
    
    # Get the item being commented on
    item = None
    if commentable_type == 'club':
        item = Club.query.get_or_404(commentable_id)
    elif commentable_type == 'player':
        item = Player.query.get_or_404(commentable_id)
    elif commentable_type == 'course':
        item = Course.query.get_or_404(commentable_id)
    
    # Check if item is approved
    if not item.is_approved:
        return jsonify({
            'success': False,
            'message': f'Cannot comment on unapproved {commentable_type}'
        }), 400
    
    # Check if parent comment exists (if provided)
    if parent_id:
        parent_comment = Comment.query.get_or_404(parent_id)
        if parent_comment.commentable_type != commentable_type or parent_comment.commentable_id != commentable_id:
            return jsonify({
                'success': False,
                'message': 'Invalid parent comment'
            }), 400
    
    # Create comment
    comment = Comment(
        user_id=current_user.id,
        commentable_type=commentable_type,
        commentable_id=commentable_id,
        content=content,
        parent_id=parent_id
    )
    
    db.session.add(comment)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Comment added',
        'comment': {
            'id': comment.id,
            'content': comment.content,
            'user': {
                'id': current_user.id,
                'username': current_user.username,
                'profile_picture': current_user.profile_picture
            },
            'created_at': comment.created_at,
            'parent_id': comment.parent_id
        }
    }), 201

@votes.route('/comments/<int:comment_id>', methods=['PUT'])
@login_required
def update_comment(comment_id):
    """Update a comment"""
    comment = Comment.query.get_or_404(comment_id)
    
    # Check if user is the comment owner
    if comment.user_id != current_user.id and not current_user.is_employee():
        return jsonify({
            'success': False,
            'message': 'You can only edit your own comments'
        }), 403
    
    data = request.get_json()
    content = data.get('content')
    
    if not content:
        return jsonify({
            'success': False,
            'message': 'Content is required'
        }), 400
    
    comment.content = content
    comment.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Comment updated',
        'comment': {
            'id': comment.id,
            'content': comment.content,
            'updated_at': comment.updated_at
        }
    })

@votes.route('/comments/<int:comment_id>', methods=['DELETE'])
@login_required
def delete_comment(comment_id):
    """Delete a comment"""
    comment = Comment.query.get_or_404(comment_id)
    
    # Check if user is the comment owner or an employee
    if comment.user_id != current_user.id and not current_user.is_employee():
        return jsonify({
            'success': False,
            'message': 'You can only delete your own comments'
        }), 403
    
    # Soft delete (mark as deleted but keep in DB)
    comment.is_deleted = True
    comment.content = "[deleted]"  # Optionally clear content
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Comment deleted'
    })

@votes.route('/comments', methods=['GET'])
def get_comments():
    """Get comments for a votable item"""
    commentable_type = request.args.get('commentable_type')
    commentable_id = request.args.get('commentable_id')
    
    if not commentable_type or not commentable_id:
        return jsonify({
            'success': False,
            'message': 'commentable_type and commentable_id are required'
        }), 400
    
    if commentable_type not in ['club', 'player', 'course']:
        return jsonify({
            'success': False,
            'message': 'Invalid commentable_type. Must be "club", "player", or "course"'
        }), 400
    
    # Get top-level comments (not replies)
    comments = Comment.query.filter_by(
        commentable_type=commentable_type,
        commentable_id=commentable_id,
        parent_id=None,
        is_deleted=False
    ).order_by(Comment.created_at.desc()).all()
    
    comments_data = []
    for comment in comments:
        # Get replies for this comment
        replies = Comment.query.filter_by(
            parent_id=comment.id,
            is_deleted=False
        ).order_by(Comment.created_at).all()
        
        replies_data = []
        for reply in replies:
            replies_data.append({
                'id': reply.id,
                'content': reply.content,
                'user': {
                    'id': reply.user.id,
                    'username': reply.user.username,
                    'profile_picture': reply.user.profile_picture
                },
                'created_at': reply.created_at,
                'updated_at': reply.updated_at
            })
        
        comments_data.append({
            'id': comment.id,
            'content': comment.content,
            'user': {
                'id': comment.user.id,
                'username': comment.user.username,
                'profile_picture': comment.user.profile_picture
            },
            'created_at': comment.created_at,
            'updated_at': comment.updated_at,
            'replies': replies_data
        })
    
    return jsonify({
        'comments': comments_data
    })