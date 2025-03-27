# app/workers/time_worker.py
from app.workers.celery_app import app
from database.connection import SessionLocal
from sqlalchemy import text
from app.models.core import Worlds, Settlements
from app.models.seasons import Seasons
from app.workers.shared_worker_utils import process_all_settlements
import logging

logger = logging.getLogger(__name__)


@app.task
def advance_game_day(world_id=None):
    """Advance the game day for one or all worlds and handle seasonal changes"""
    db = SessionLocal()
    try:
        query = db.query(Worlds)
        if world_id:
            query = query.filter(Worlds.world_id == world_id)
        
        worlds = query.all()
        
        for world in worlds:
            # Advance day counter
            world.current_game_day += 1
            
            # Update season tracking
            day_of_season = world.day_of_season + 1 if world.day_of_season is not None else 1
            
            # If we've reached the end of the season, advance to the next season
            if day_of_season > world.days_per_season:
                day_of_season = 1
                
                # Get the next season from the seasons table
                current_season_name = world.current_season if world.current_season else "spring"
                
                # First check if the seasons table exists (in case migration hasn't been run)
                if db.execute(text("SELECT to_regclass('public.seasons')")).scalar():
                    season = db.query(Seasons).filter(Seasons.name == current_season_name).first()
                    
                    if season:
                        # Set to the next season in the cycle
                        world.current_season = season.next_season
                        
                        # Update the year if we've completed a full cycle
                        if season.next_season == "spring" and current_season_name == "winter":
                            world.current_year = (world.current_year or 1) + 1
                        
                        logger.info(f"Season changed in world {world.world_name}: {current_season_name} → {season.next_season} (Year: {world.current_year or 1})")
                    else:
                        # Fallback in case season not found
                        world.current_season = "spring"
                        logger.warning(f"Season {current_season_name} not found in database, reset to spring")
                else:
                    # Simple fallback cycle if seasons table doesn't exist yet
                    next_season = {
                        "spring": "summer",
                        "summer": "autumn",
                        "autumn": "winter",
                        "winter": "spring"
                    }.get(current_season_name, "spring")
                    
                    world.current_season = next_season
                    if next_season == "spring" and current_season_name == "winter":
                        world.current_year = (world.current_year or 1) + 1
                    
                    logger.info(f"Season changed in world {world.world_name} (fallback): {current_season_name} → {next_season}")
            
            # Update day of season
            world.day_of_season = day_of_season
            
            # Log the update with season information
            season_info = f"Season: {world.current_season or 'spring'}, Day: {world.day_of_season or 1}/{world.days_per_season or 30}"
            year_info = f"Year: {world.current_year or 1}"
            logger.info(f"Advanced world {world.world_name} to day {world.current_game_day} ({season_info}, {year_info})")
            
            # Trigger daily processes for this world
            process_all_settlements.delay(str(world.world_id))
            
        db.commit()
        return len(worlds)
    finally:
        db.close()
   