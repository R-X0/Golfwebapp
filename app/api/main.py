from flask import Blueprint, render_template, current_app
from ..models.club import Club
from ..models.player import Player
from ..models.course import Course

main = Blueprint('main', __name__)

@main.route('/')
def index():
    """Render the main index page"""
    # Get top rated clubs
    top_clubs = Club.query.filter_by(is_approved=True).all()
    top_clubs = sorted(top_clubs, key=lambda c: c.vote_score, reverse=True)[:3]
    
    # Get popular players
    top_players = Player.query.filter_by(is_approved=True).all()
    top_players = sorted(top_players, key=lambda p: p.vote_score, reverse=True)[:3]
    
    # Get featured courses
    top_courses = Course.query.filter_by(is_approved=True).all()
    top_courses = sorted(top_courses, key=lambda c: c.vote_score, reverse=True)[:3]
    
    return render_template('main/index.html', 
                           top_clubs=top_clubs,
                           top_players=top_players,
                           top_courses=top_courses)