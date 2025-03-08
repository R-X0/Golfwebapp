from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import desc
from datetime import datetime
import os

from .. import db
from ..models.club import Club, ClubBrand, ClubType
from ..models.user import Role
from ..models.vote import Vote

clubs = Blueprint('clubs', __name__)

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


@clubs.route('/', methods=['GET'])
def get_clubs():
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('ITEMS_PER_PAGE', 20)
    sort_by = request.args.get('sort_by', 'votes')  # 'votes', 'newest', 'name'
    brand_id = request.args.get('brand_id', type=int)
    club_type_id = request.args.get('club_type_id', type=int)
    
    # Base query for approved clubs
    query = Club.query.filter_by(is_approved=True)
    
    # Apply filters
    if brand_id:
        query = query.filter_by(brand_id=brand_id)
    
    if club_type_id:
        query = query.filter_by(club_type_id=club_type_id)
    
    # Apply sorting
    if sort_by == 'newest':
        query = query.order_by(desc(Club.created_at))
    elif sort_by == 'name':
        query = query.order_by(Club.name)
    else:  # Default: sort by votes
        # This is a simplified version - would need a subquery for accurate vote sorting
        # For now, using a simple approach
        clubs_with_votes = []
        all_clubs = query.all()
        for club in all_clubs:
            clubs_with_votes.append((club, club.vote_score))
        
        # Sort by vote score
        clubs_with_votes.sort(key=lambda x: x[1], reverse=True)
        
        # Paginate manually
        start = (page - 1) * per_page
        end = start + per_page
        paginated_clubs = clubs_with_votes[start:end]
        
        # Format response
        clubs_data = []
        for club, vote_score in paginated_clubs:
            clubs_data.append({
                'id': club.id,
                'name': club.name,
                'description': club.description,
                'image_url': club.image_url,
                'purchase_link': club.purchase_link,
                'release_year': club.release_year,
                'price': club.price,
                'brand': club.brand.name if club.brand else None,
                'type': club.club_type.name if club.club_type else None,
                'vote_score': vote_score,
                'upvotes': club.upvote_count,
                'downvotes': club.downvote_count
            })
        
        return jsonify({
            'clubs': clubs_data,
            'page': page,
            'per_page': per_page,
            'total': len(all_clubs),
            'pages': (len(all_clubs) + per_page - 1) // per_page
        })
    
    # Standard pagination for other sort options
    paginated_clubs = query.paginate(page=page, per_page=per_page, error_out=False)
    
    clubs_data = []
    for club in paginated_clubs.items:
        clubs_data.append({
            'id': club.id,
            'name': club.name,
            'description': club.description,
            'image_url': club.image_url,
            'purchase_link': club.purchase_link,
            'release_year': club.release_year,
            'price': club.price,
            'brand': club.brand.name if club.brand else None,
            'type': club.club_type.name if club.club_type else None,
            'vote_score': club.vote_score,
            'upvotes': club.upvote_count,
            'downvotes': club.downvote_count
        })
    
    return jsonify({
        'clubs': clubs_data,
        'page': page,
        'per_page': per_page,
        'total': paginated_clubs.total,
        'pages': paginated_clubs.pages
    })


@clubs.route('/<int:club_id>', methods=['GET'])
def get_club(club_id):
    club = Club.query.get_or_404(club_id)
    
    # Check if club is approved or if current user is an employee
    if not club.is_approved and (not current_user.is_authenticated or not current_user.is_employee()):
        return jsonify({
            'success': False,
            'message': 'Club not found or not approved yet'
        }), 404
    
    # Get user's vote if authenticated
    user_vote = None
    if current_user.is_authenticated:
        vote = Vote.query.filter_by(
            user_id=current_user.id,
            votable_type='club',
            votable_id=club.id
        ).first()
        if vote:
            user_vote = 'up' if vote.vote_type else 'down'
    
    return jsonify({
        'id': club.id,
        'name': club.name,
        'description': club.description,
        'image_url': club.image_url,
        'purchase_link': club.purchase_link,
        'release_year': club.release_year,
        'price': club.price,
        'brand': {
            'id': club.brand.id,
            'name': club.brand.name,
            'logo_url': club.brand.logo_url,
            'website': club.brand.website
        } if club.brand else None,
        'type': {
            'id': club.club_type.id,
            'name': club.club_type.name,
            'description': club.club_type.description
        } if club.club_type else None,
        'vote_score': club.vote_score,
        'upvotes': club.upvote_count,
        'downvotes': club.downvote_count,
        'user_vote': user_vote,
        'created_at': club.created_at,
        'updated_at': club.updated_at,
        'is_approved': club.is_approved,
        'submitted_by': club.submitter.username if club.submitter else None,
    })


@clubs.route('/', methods=['POST'])
@login_required
def create_club():
    data = request.get_json()
    
    # Required fields
    name = data.get('name')
    if not name:
        return jsonify({
            'success': False,
            'message': 'Club name is required'
        }), 400
    
    # Optional fields
    description = data.get('description')
    purchase_link = data.get('purchase_link')
    image_url = data.get('image_url')
    release_year = data.get('release_year')
    price = data.get('price')
    brand_id = data.get('brand_id')
    club_type_id = data.get('club_type_id')
    
    # Validate brand and club type if provided
    if brand_id and not ClubBrand.query.get(brand_id):
        return jsonify({
            'success': False,
            'message': 'Invalid brand ID'
        }), 400
    
    if club_type_id and not ClubType.query.get(club_type_id):
        return jsonify({
            'success': False,
            'message': 'Invalid club type ID'
        }), 400
    
    # Create new club
    club = Club(
        name=name,
        description=description,
        purchase_link=purchase_link,
        image_url=image_url,
        release_year=release_year,
        price=price,
        brand_id=brand_id,
        club_type_id=club_type_id,
        submitted_by=current_user.id
    )
    
    # If user is employee or admin, auto-approve
    if current_user.is_employee():
        club.is_approved = True
        club.approved_by = current_user.id
    
    db.session.add(club)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Club created successfully',
        'id': club.id,
        'is_approved': club.is_approved
    }), 201


@clubs.route('/<int:club_id>', methods=['PUT'])
@employee_required
def update_club(club_id):
    club = Club.query.get_or_404(club_id)
    data = request.get_json()
    
    # Update fields
    if 'name' in data:
        club.name = data['name']
    if 'description' in data:
        club.description = data['description']
    if 'purchase_link' in data:
        club.purchase_link = data['purchase_link']
    if 'image_url' in data:
        club.image_url = data['image_url']
    if 'release_year' in data:
        club.release_year = data['release_year']
    if 'price' in data:
        club.price = data['price']
    if 'brand_id' in data:
        brand_id = data['brand_id']
        if brand_id and not ClubBrand.query.get(brand_id):
            return jsonify({
                'success': False,
                'message': 'Invalid brand ID'
            }), 400
        club.brand_id = brand_id
    if 'club_type_id' in data:
        club_type_id = data['club_type_id']
        if club_type_id and not ClubType.query.get(club_type_id):
            return jsonify({
                'success': False,
                'message': 'Invalid club type ID'
            }), 400
        club.club_type_id = club_type_id
    if 'is_approved' in data:
        club.is_approved = data['is_approved']
        if data['is_approved']:
            club.approved_by = current_user.id
    
    club.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Club updated successfully',
        'id': club.id
    })


@clubs.route('/<int:club_id>', methods=['DELETE'])
@employee_required
def delete_club(club_id):
    club = Club.query.get_or_404(club_id)
    
    db.session.delete(club)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Club deleted successfully'
    })


@clubs.route('/<int:club_id>/vote', methods=['POST'])
@login_required
def vote_club(club_id):
    club = Club.query.get_or_404(club_id)
    
    # Check if club is approved
    if not club.is_approved:
        return jsonify({
            'success': False,
            'message': 'Cannot vote on unapproved club'
        }), 400
    
    data = request.get_json()
    vote_type = data.get('vote_type')
    
    if vote_type not in ['up', 'down', None]:
        return jsonify({
            'success': False,
            'message': 'Invalid vote type. Must be "up", "down", or null to remove vote'
        }), 400
    
    # Check if user has already voted
    existing_vote = Vote.query.filter_by(
        user_id=current_user.id,
        votable_type='club',
        votable_id=club.id
    ).first()
    
    if vote_type is None:
        # Remove vote if it exists
        if existing_vote:
            db.session.delete(existing_vote)
            db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Vote removed',
            'vote_score': club.vote_score,
            'upvotes': club.upvote_count,
            'downvotes': club.downvote_count
        })
    
    vote_value = vote_type == 'up'
    
    if existing_vote:
        # Update existing vote
        existing_vote.vote_type = vote_value
    else:
        # Create new vote
        vote = Vote(
            user_id=current_user.id,
            votable_type='club',
            votable_id=club.id,
            vote_type=vote_value
        )
        db.session.add(vote)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Vote {"up" if vote_value else "down"} recorded',
        'vote_score': club.vote_score,
        'upvotes': club.upvote_count,
        'downvotes': club.downvote_count
    })


@clubs.route('/brands', methods=['GET'])
def get_brands():
    brands = ClubBrand.query.all()
    
    brands_data = []
    for brand in brands:
        brands_data.append({
            'id': brand.id,
            'name': brand.name,
            'logo_url': brand.logo_url,
            'website': brand.website
        })
    
    return jsonify({
        'brands': brands_data
    })


@clubs.route('/types', methods=['GET'])
def get_club_types():
    club_types = ClubType.query.all()
    
    types_data = []
    for club_type in club_types:
        types_data.append({
            'id': club_type.id,
            'name': club_type.name,
            'description': club_type.description
        })
    
    return jsonify({
        'club_types': types_data
    })


@clubs.route('/brands', methods=['POST'])
@employee_required
def create_brand():
    data = request.get_json()
    
    name = data.get('name')
    if not name:
        return jsonify({
            'success': False,
            'message': 'Brand name is required'
        }), 400
    
    logo_url = data.get('logo_url')
    website = data.get('website')
    
    # Check if brand already exists
    if ClubBrand.query.filter_by(name=name).first():
        return jsonify({
            'success': False,
            'message': 'Brand with this name already exists'
        }), 400
    
    brand = ClubBrand(
        name=name,
        logo_url=logo_url,
        website=website
    )
    
    db.session.add(brand)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Brand created successfully',
        'id': brand.id
    }), 201


@clubs.route('/types', methods=['POST'])
@employee_required
def create_club_type():
    data = request.get_json()
    
    name = data.get('name')
    if not name:
        return jsonify({
            'success': False,
            'message': 'Club type name is required'
        }), 400
    
    description = data.get('description')
    
    # Check if club type already exists
    if ClubType.query.filter_by(name=name).first():
        return jsonify({
            'success': False,
            'message': 'Club type with this name already exists'
        }), 400
    
    club_type = ClubType(
        name=name,
        description=description
    )
    
    db.session.add(club_type)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Club type created successfully',
        'id': club_type.id
    }), 201


@clubs.route('/approval-queue', methods=['GET'])
@employee_required
def get_approval_queue():
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('ITEMS_PER_PAGE', 20)
    
    # Get unapproved clubs
    unapproved_clubs = Club.query.filter_by(is_approved=False).order_by(
        Club.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    clubs_data = []
    for club in unapproved_clubs.items:
        clubs_data.append({
            'id': club.id,
            'name': club.name,
            'description': club.description,
            'image_url': club.image_url,
            'purchase_link': club.purchase_link,
            'release_year': club.release_year,
            'price': club.price,
            'brand': club.brand.name if club.brand else None,
            'type': club.club_type.name if club.club_type else None,
            'submitted_by': club.submitter.username if club.submitter else None,
            'created_at': club.created_at
        })
    
    return jsonify({
        'clubs': clubs_data,
        'page': page,
        'per_page': per_page,
        'total': unapproved_clubs.total,
        'pages': unapproved_clubs.pages
    })


@clubs.route('/<int:club_id>/approve', methods=['POST'])
@employee_required
def approve_club(club_id):
    club = Club.query.get_or_404(club_id)
    
    if club.is_approved:
        return jsonify({
            'success': False,
            'message': 'Club is already approved'
        }), 400
    
    club.is_approved = True
    club.approved_by = current_user.id
    club.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Club approved successfully'
    })