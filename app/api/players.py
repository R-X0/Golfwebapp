from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import desc
from datetime import datetime

from .. import db
from ..models.player import Player, PlayerAchievement
from ..models.user import Role
from ..models.vote import Vote

players = Blueprint('players', __name__)

# Basic route to get all players
@players.route('/', methods=['GET'])
def get_players():
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('ITEMS_PER_PAGE', 20)
    sort_by = request.args.get('sort_by', 'votes')  # 'votes', 'newest', 'name', 'rank'
    
    # Base query for approved players
    query = Player.query.filter_by(is_approved=True)
    
    # Apply sorting
    if sort_by == 'newest':
        query = query.order_by(desc(Player.created_at))
    elif sort_by == 'name':
        query = query.order_by(Player.name)
    elif sort_by == 'rank':
        query = query.order_by(Player.world_ranking)
    else:  # Default: sort by votes
        # This is a simplified version - would need a subquery for accurate vote sorting
        players_with_votes = []
        all_players = query.all()
        for player in all_players:
            players_with_votes.append((player, player.vote_score))
        
        # Sort by vote score
        players_with_votes.sort(key=lambda x: x[1], reverse=True)
        
        # Paginate manually
        start = (page - 1) * per_page
        end = start + per_page
        paginated_players = players_with_votes[start:end]
        
        # Format response
        players_data = []
        for player, vote_score in paginated_players:
            players_data.append({
                'id': player.id,
                'name': player.name,
                'profile_picture': player.profile_picture,
                'country': player.country,
                'world_ranking': player.world_ranking,
                'vote_score': vote_score,
                'upvotes': player.upvote_count,
                'downvotes': player.downvote_count
            })
        
        return jsonify({
            'players': players_data,
            'page': page,
            'per_page': per_page,
            'total': len(all_players),
            'pages': (len(all_players) + per_page - 1) // per_page
        })
    
    # Standard pagination for other sort options
    paginated_players = query.paginate(page=page, per_page=per_page, error_out=False)
    
    players_data = []
    for player in paginated_players.items:
        players_data.append({
            'id': player.id,
            'name': player.name,
            'profile_picture': player.profile_picture,
            'country': player.country,
            'world_ranking': player.world_ranking,
            'vote_score': player.vote_score,
            'upvotes': player.upvote_count,
            'downvotes': player.downvote_count
        })
    
    return jsonify({
        'players': players_data,
        'page': page,
        'per_page': per_page,
        'total': paginated_players.total,
        'pages': paginated_players.pages
    })

# Get a specific player
@players.route('/<int:player_id>', methods=['GET'])
def get_player(player_id):
    player = Player.query.get_or_404(player_id)
    
    # Check if player is approved
    if not player.is_approved and (not current_user.is_authenticated or not current_user.is_employee()):
        return jsonify({
            'success': False,
            'message': 'Player not found or not approved yet'
        }), 404
    
    # Get user's vote if authenticated
    user_vote = None
    if current_user.is_authenticated:
        vote = Vote.query.filter_by(
            user_id=current_user.id,
            votable_type='player',
            votable_id=player.id
        ).first()
        if vote:
            user_vote = 'up' if vote.vote_type else 'down'
    
    # Get achievements
    achievements = []
    for achievement in player.achievements:
        achievements.append({
            'id': achievement.id,
            'title': achievement.title,
            'year': achievement.year,
            'description': achievement.description
        })
    
    return jsonify({
        'id': player.id,
        'name': player.name,
        'profile_picture': player.profile_picture,
        'country': player.country,
        'birthdate': player.birthdate.isoformat() if player.birthdate else None,
        'age': player.age,
        'turned_pro': player.turned_pro,
        'bio': player.bio,
        'website': player.website,
        'twitter_handle': player.twitter_handle,
        'instagram_handle': player.instagram_handle,
        'world_ranking': player.world_ranking,
        'achievements': achievements,
        'vote_score': player.vote_score,
        'upvotes': player.upvote_count,
        'downvotes': player.downvote_count,
        'user_vote': user_vote,
        'created_at': player.created_at,
        'updated_at': player.updated_at,
        'is_approved': player.is_approved,
        'submitted_by': player.submitter.username if player.submitter else None,
    })