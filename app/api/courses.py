from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import desc
from datetime import datetime

from .. import db
from ..models.course import Course, CourseHole
from ..models.user import Role
from ..models.vote import Vote
from ..services.golf_api import GolfAPIService

courses = Blueprint('courses', __name__)

# Decorator for checking if user is employee or admin
def employee_required(f):
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_employee():
            return jsonify({
                'success': False,
                'message': 'Employee or admin privileges required'
            }), 403
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@courses.route('/', methods=['GET'])
def get_courses():
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('ITEMS_PER_PAGE', 20)
    sort_by = request.args.get('sort_by', 'votes')  # 'votes', 'newest', 'name'
    
    # Base query for approved courses
    query = Course.query.filter_by(is_approved=True)
    
    # Apply sorting
    if sort_by == 'newest':
        query = query.order_by(desc(Course.created_at))
    elif sort_by == 'name':
        query = query.order_by(Course.name)
    else:  # Default: sort by votes
        # This is a simplified version - would need a subquery for accurate vote sorting
        courses_with_votes = []
        all_courses = query.all()
        for course in all_courses:
            courses_with_votes.append((course, course.vote_score))
        
        # Sort by vote score
        courses_with_votes.sort(key=lambda x: x[1], reverse=True)
        
        # Paginate manually
        start = (page - 1) * per_page
        end = start + per_page
        paginated_courses = courses_with_votes[start:end]
        
        # Format response
        courses_data = []
        for course, vote_score in paginated_courses:
            courses_data.append({
                'id': course.id,
                'name': course.name,
                'location': f"{course.city}, {course.state}" if course.city and course.state else course.country,
                'image_url': course.image_url,
                'par': course.par,
                'length_yards': course.length_yards,
                'course_type': course.course_type,
                'vote_score': vote_score,
                'upvotes': course.upvote_count,
                'downvotes': course.downvote_count
            })
        
        return jsonify({
            'courses': courses_data,
            'page': page,
            'per_page': per_page,
            'total': len(all_courses),
            'pages': (len(all_courses) + per_page - 1) // per_page
        })
    
    # Standard pagination for other sort options
    paginated_courses = query.paginate(page=page, per_page=per_page, error_out=False)
    
    courses_data = []
    for course in paginated_courses.items:
        courses_data.append({
            'id': course.id,
            'name': course.name,
            'location': f"{course.city}, {course.state}" if course.city and course.state else course.country,
            'image_url': course.image_url,
            'par': course.par,
            'length_yards': course.length_yards,
            'course_type': course.course_type,
            'vote_score': course.vote_score,
            'upvotes': course.upvote_count,
            'downvotes': course.downvote_count
        })
    
    return jsonify({
        'courses': courses_data,
        'page': page,
        'per_page': per_page,
        'total': paginated_courses.total,
        'pages': paginated_courses.pages
    })

@courses.route('/<int:course_id>', methods=['GET'])
def get_course(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Check if course is approved
    if not course.is_approved and (not current_user.is_authenticated or not current_user.is_employee()):
        return jsonify({
            'success': False,
            'message': 'Course not found or not approved yet'
        }), 404
    
    # Get user's vote if authenticated
    user_vote = None
    if current_user.is_authenticated:
        vote = Vote.query.filter_by(
            user_id=current_user.id,
            votable_type='course',
            votable_id=course.id
        ).first()
        if vote:
            user_vote = 'up' if vote.vote_type else 'down'
    
    # Get course holes
    holes_data = []
    for hole in course.holes.order_by(CourseHole.hole_number):
        holes_data.append({
            'hole_number': hole.hole_number,
            'par': hole.par,
            'yards': hole.yards,
            'handicap': hole.handicap,
            'description': hole.description,
            'image_url': hole.image_url
        })
    
    return jsonify({
        'id': course.id,
        'name': course.name,
        'description': course.description,
        'address': course.address,
        'city': course.city,
        'state': course.state,
        'country': course.country,
        'postal_code': course.postal_code,
        'full_address': course.full_address,
        'website': course.website,
        'phone': course.phone,
        'email': course.email,
        'year_built': course.year_built,
        'architect': course.architect,
        'course_type': course.course_type,
        'num_holes': course.num_holes,
        'par': course.par,
        'length_yards': course.length_yards,
        'latitude': course.latitude,
        'longitude': course.longitude,
        'image_url': course.image_url,
        'logo_url': course.logo_url,
        'holes': holes_data,
        'vote_score': course.vote_score,
        'upvotes': course.upvote_count,
        'downvotes': course.downvote_count,
        'user_vote': user_vote,
        'created_at': course.created_at,
        'updated_at': course.updated_at,
        'is_approved': course.is_approved,
        'submitted_by': course.submitter.username if course.submitter else None,
    })

# More routes would go here for creating, updating courses, etc.