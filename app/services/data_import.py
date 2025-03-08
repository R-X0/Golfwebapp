import csv
import io
import pandas as pd
import logging
from datetime import datetime
from werkzeug.utils import secure_filename
import os

from .. import db
from ..models.club import Club, ClubBrand, ClubType
from ..models.player import Player, PlayerAchievement
from ..models.course import Course, CourseHole

# Configure logging
logger = logging.getLogger(__name__)

class DataImportService:
    """Service for importing data from CSV files"""
    
    @staticmethod
    def import_clubs_from_csv(file_stream, user_id=None):
        """Import golf clubs from a CSV file"""
        try:
            # Read CSV
            csv_data = pd.read_csv(file_stream, encoding='utf-8')
            
            # Ensure required columns exist
            required_columns = ['name', 'brand']
            for col in required_columns:
                if col not in csv_data.columns:
                    logger.error(f"CSV is missing required column: {col}")
                    return {
                        'success': False,
                        'message': f"CSV is missing required column: {col}",
                        'imported': 0,
                        'errors': 0
                    }
            
            imported_count = 0
            error_count = 0
            error_details = []
            
            # Process each row
            for _, row in csv_data.iterrows():
                try:
                    # Get or create brand
                    brand_name = row.get('brand')
                    if pd.notna(brand_name):
                        brand = ClubBrand.query.filter_by(name=brand_name).first()
                        if not brand:
                            brand = ClubBrand(name=brand_name)
                            db.session.add(brand)
                            db.session.commit()
                    else:
                        brand = None
                    
                    # Get or create club type
                    club_type_name = row.get('type')
                    if pd.notna(club_type_name):
                        club_type = ClubType.query.filter_by(name=club_type_name).first()
                        if not club_type:
                            club_type = ClubType(name=club_type_name)
                            db.session.add(club_type)
                            db.session.commit()
                    else:
                        club_type = None
                    
                    # Create club
                    club = Club(
                        name=row.get('name'),
                        description=row.get('description') if pd.notna(row.get('description')) else None,
                        purchase_link=row.get('purchase_link') if pd.notna(row.get('purchase_link')) else None,
                        image_url=row.get('image_url') if pd.notna(row.get('image_url')) else None,
                        release_year=int(row.get('release_year')) if pd.notna(row.get('release_year')) else None,
                        price=float(row.get('price')) if pd.notna(row.get('price')) else None,
                        brand_id=brand.id if brand else None,
                        club_type_id=club_type.id if club_type else None,
                        is_approved=True,  # Auto-approve imported clubs
                        submitted_by=user_id,
                        approved_by=user_id
                    )
                    
                    db.session.add(club)
                    imported_count += 1
                
                except Exception as e:
                    error_count += 1
                    error_details.append({
                        'row': dict(row),
                        'error': str(e)
                    })
                    logger.error(f"Error importing club row: {str(e)}")
                    continue
            
            db.session.commit()
            
            logger.info(f"Imported {imported_count} clubs with {error_count} errors")
            return {
                'success': True,
                'message': f"Imported {imported_count} clubs with {error_count} errors",
                'imported': imported_count,
                'errors': error_count,
                'error_details': error_details
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error importing clubs from CSV: {str(e)}")
            return {
                'success': False,
                'message': f"Error importing clubs: {str(e)}",
                'imported': 0,
                'errors': 1
            }
    
    @staticmethod
    def import_players_from_csv(file_stream, user_id=None):
        """Import golf players from a CSV file"""
        try:
            # Read CSV
            csv_data = pd.read_csv(file_stream, encoding='utf-8')
            
            # Ensure required columns exist
            required_columns = ['name']
            for col in required_columns:
                if col not in csv_data.columns:
                    logger.error(f"CSV is missing required column: {col}")
                    return {
                        'success': False,
                        'message': f"CSV is missing required column: {col}",
                        'imported': 0,
                        'errors': 0
                    }
            
            imported_count = 0
            error_count = 0
            error_details = []
            
            # Process each row
            for _, row in csv_data.iterrows():
                try:
                    # Check if player already exists
                    player_name = row.get('name')
                    existing_player = Player.query.filter_by(name=player_name).first()
                    
                    if existing_player:
                        # Update existing player
                        if pd.notna(row.get('country')):
                            existing_player.country = row.get('country')
                        if pd.notna(row.get('birthdate')):
                            existing_player.birthdate = pd.to_datetime(row.get('birthdate')).date()
                        if pd.notna(row.get('turned_pro')):
                            existing_player.turned_pro = int(row.get('turned_pro'))
                        if pd.notna(row.get('bio')):
                            existing_player.bio = row.get('bio')
                        if pd.notna(row.get('website')):
                            existing_player.website = row.get('website')
                        if pd.notna(row.get('twitter_handle')):
                            existing_player.twitter_handle = row.get('twitter_handle')
                        if pd.notna(row.get('instagram_handle')):
                            existing_player.instagram_handle = row.get('instagram_handle')
                        if pd.notna(row.get('world_ranking')):
                            existing_player.world_ranking = int(row.get('world_ranking'))
                        if pd.notna(row.get('profile_picture')):
                            existing_player.profile_picture = row.get('profile_picture')
                        
                        existing_player.updated_at = datetime.utcnow()
                    else:
                        # Create new player
                        player = Player(
                            name=player_name,
                            country=row.get('country') if pd.notna(row.get('country')) else None,
                            birthdate=pd.to_datetime(row.get('birthdate')).date() if pd.notna(row.get('birthdate')) else None,
                            turned_pro=int(row.get('turned_pro')) if pd.notna(row.get('turned_pro')) else None,
                            bio=row.get('bio') if pd.notna(row.get('bio')) else None,
                            website=row.get('website') if pd.notna(row.get('website')) else None,
                            twitter_handle=row.get('twitter_handle') if pd.notna(row.get('twitter_handle')) else None,
                            instagram_handle=row.get('instagram_handle') if pd.notna(row.get('instagram_handle')) else None,
                            world_ranking=int(row.get('world_ranking')) if pd.notna(row.get('world_ranking')) else None,
                            profile_picture=row.get('profile_picture') if pd.notna(row.get('profile_picture')) else None,
                            is_approved=True,  # Auto-approve imported players
                            submitted_by=user_id,
                            approved_by=user_id
                        )
                        db.session.add(player)
                    
                    imported_count += 1
                
                except Exception as e:
                    error_count += 1
                    error_details.append({
                        'row': dict(row),
                        'error': str(e)
                    })
                    logger.error(f"Error importing player row: {str(e)}")
                    continue
            
            db.session.commit()
            
            logger.info(f"Imported {imported_count} players with {error_count} errors")
            return {
                'success': True,
                'message': f"Imported {imported_count} players with {error_count} errors",
                'imported': imported_count,
                'errors': error_count,
                'error_details': error_details
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error importing players from CSV: {str(e)}")
            return {
                'success': False,
                'message': f"Error importing players: {str(e)}",
                'imported': 0,
                'errors': 1
            }
    
    @staticmethod
    def import_kaggle_players_dataset(file_stream, user_id=None):
        """Import golf player data from the Kaggle Top 1000 Golf Players dataset"""
        try:
            # Read CSV
            csv_data = pd.read_csv(file_stream, encoding='utf-8')
            
            # Map dataset columns to our model fields
            # Adapt this to match the actual Kaggle dataset structure
            imported_count = 0
            error_count = 0
            error_details = []
            
            # Process each row
            for _, row in csv_data.iterrows():
                try:
                    # Adapt the following to match the Kaggle dataset structure
                    player_name = row.get('Name')
                    if not player_name or pd.isna(player_name):
                        continue
                    
                    # Check if player already exists
                    existing_player = Player.query.filter_by(name=player_name).first()
                    
                    if existing_player:
                        # Update existing player
                        if 'Country' in row and pd.notna(row.get('Country')):
                            existing_player.country = row.get('Country')
                        if 'BirthDate' in row and pd.notna(row.get('BirthDate')):
                            existing_player.birthdate = pd.to_datetime(row.get('BirthDate')).date()
                        if 'TurnedPro' in row and pd.notna(row.get('TurnedPro')):
                            existing_player.turned_pro = int(row.get('TurnedPro'))
                        if 'Bio' in row and pd.notna(row.get('Bio')):
                            existing_player.bio = row.get('Bio')
                        if 'WorldRanking' in row and pd.notna(row.get('WorldRanking')):
                            existing_player.world_ranking = int(row.get('WorldRanking'))
                        
                        existing_player.updated_at = datetime.utcnow()
                    else:
                        # Create new player
                        player = Player(
                            name=player_name,
                            country=row.get('Country') if 'Country' in row and pd.notna(row.get('Country')) else None,
                            birthdate=pd.to_datetime(row.get('BirthDate')).date() if 'BirthDate' in row and pd.notna(row.get('BirthDate')) else None,
                            turned_pro=int(row.get('TurnedPro')) if 'TurnedPro' in row and pd.notna(row.get('TurnedPro')) else None,
                            bio=row.get('Bio') if 'Bio' in row and pd.notna(row.get('Bio')) else None,
                            world_ranking=int(row.get('WorldRanking')) if 'WorldRanking' in row and pd.notna(row.get('WorldRanking')) else None,
                            is_approved=True,  # Auto-approve imported players
                            submitted_by=user_id,
                            approved_by=user_id
                        )
                        db.session.add(player)
                    
                    # Import achievements if present in the dataset
                    if 'MajorWins' in row and pd.notna(row.get('MajorWins')) and row.get('MajorWins') > 0:
                        # Example of how to handle achievements
                        achievement = PlayerAchievement(
                            player_id=existing_player.id if existing_player else player.id,
                            title="Major Tournament Wins",
                            year=datetime.now().year,  # Use current year as default
                            description=f"Player has won {int(row.get('MajorWins'))} major tournaments"
                        )
                        db.session.add(achievement)
                    
                    imported_count += 1
                
                except Exception as e:
                    error_count += 1
                    error_details.append({
                        'player': player_name,
                        'error': str(e)
                    })
                    logger.error(f"Error importing Kaggle player data: {str(e)}")
                    continue
            
            db.session.commit()
            
            logger.info(f"Imported {imported_count} players from Kaggle dataset with {error_count} errors")
            return {
                'success': True,
                'message': f"Imported {imported_count} players from Kaggle dataset with {error_count} errors",
                'imported': imported_count,
                'errors': error_count,
                'error_details': error_details
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error importing Kaggle players dataset: {str(e)}")
            return {
                'success': False,
                'message': f"Error importing Kaggle players dataset: {str(e)}",
                'imported': 0,
                'errors': 1
            }