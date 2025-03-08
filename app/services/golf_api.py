import requests
from flask import current_app
import json
import logging
from datetime import datetime

from .. import db
from ..models.course import Course, CourseHole

# Configure logging
logger = logging.getLogger(__name__)

class GolfAPIService:
    """Service to interact with GolfAPI.io"""
    
    def __init__(self, api_key=None, base_url=None):
        self.api_key = api_key or current_app.config.get('GOLF_API_KEY')
        self.base_url = base_url or current_app.config.get('GOLF_API_BASE_URL')
        
        if not self.api_key:
            logger.warning("GolfAPI key not configured")
        
        if not self.base_url:
            logger.warning("GolfAPI base URL not configured")
    
    def _make_request(self, endpoint, params=None):
        """Make a request to the Golf API"""
        if not self.api_key or not self.base_url:
            logger.error("GolfAPI not properly configured")
            return None
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Accept': 'application/json'
        }
        
        try:
            response = requests.get(
                f"{self.base_url}/{endpoint}",
                headers=headers,
                params=params
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making request to GolfAPI: {str(e)}")
            return None
    
    def search_courses(self, query=None, latitude=None, longitude=None, radius=None, limit=20, offset=0):
        """Search for golf courses"""
        params = {
            'limit': limit,
            'offset': offset
        }
        
        if query:
            params['q'] = query
        
        if latitude and longitude and radius:
            params['lat'] = latitude
            params['lng'] = longitude
            params['radius'] = radius
        
        return self._make_request('courses', params)
    
    def get_course_details(self, course_id):
        """Get detailed information about a specific course"""
        return self._make_request(f'courses/{course_id}')
    
    def get_course_holes(self, course_id):
        """Get information about holes for a specific course"""
        return self._make_request(f'courses/{course_id}/holes')
    
    def import_course(self, course_id, user_id=None):
        """Import a course from the Golf API into the database"""
        # Get course details
        course_data = self.get_course_details(course_id)
        if not course_data:
            logger.error(f"Failed to get course data for ID: {course_id}")
            return None
        
        # Check if course already exists
        existing_course = Course.query.filter_by(golf_api_id=str(course_id)).first()
        if existing_course:
            logger.info(f"Course already exists: {course_id}")
            return existing_course
        
        # Create new course
        try:
            course = Course(
                name=course_data.get('name'),
                description=course_data.get('description'),
                address=course_data.get('address', {}).get('line1'),
                city=course_data.get('address', {}).get('city'),
                state=course_data.get('address', {}).get('state'),
                country=course_data.get('address', {}).get('country'),
                postal_code=course_data.get('address', {}).get('zip'),
                website=course_data.get('website'),
                phone=course_data.get('phone'),
                email=course_data.get('email'),
                year_built=course_data.get('year_built'),
                architect=course_data.get('architect'),
                course_type=course_data.get('type'),
                num_holes=course_data.get('num_holes', 18),
                par=course_data.get('par'),
                length_yards=course_data.get('length_yards'),
                latitude=course_data.get('location', {}).get('lat'),
                longitude=course_data.get('location', {}).get('lng'),
                image_url=course_data.get('image_url'),
                logo_url=course_data.get('logo_url'),
                golf_api_id=str(course_id),
                is_approved=True,  # Auto-approve courses from the API
                submitted_by=user_id,
                approved_by=user_id
            )
            
            db.session.add(course)
            db.session.commit()
            
            # Import hole data
            holes_data = self.get_course_holes(course_id)
            if holes_data:
                for hole_data in holes_data:
                    hole = CourseHole(
                        course_id=course.id,
                        hole_number=hole_data.get('number'),
                        par=hole_data.get('par'),
                        yards=hole_data.get('yards'),
                        handicap=hole_data.get('handicap'),
                        description=hole_data.get('description'),
                        image_url=hole_data.get('image_url')
                    )
                    db.session.add(hole)
                
                db.session.commit()
            
            logger.info(f"Successfully imported course: {course.name} (ID: {course.id})")
            return course
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error importing course: {str(e)}")
            return None
    
    def bulk_import_courses(self, query=None, latitude=None, longitude=None, radius=None, limit=100, user_id=None):
        """Import multiple courses matching search criteria"""
        courses = []
        
        # Get courses matching search criteria
        search_results = self.search_courses(
            query=query,
            latitude=latitude,
            longitude=longitude,
            radius=radius,
            limit=limit
        )
        
        if not search_results or 'courses' not in search_results:
            logger.error("No courses found or error in search results")
            return []
        
        # Import each course
        for course_data in search_results['courses']:
            course_id = course_data.get('id')
            course = self.import_course(course_id, user_id)
            if course:
                courses.append(course)
        
        return courses