# workers/time_worker_new.py
from app.workers.celery_app import app
from database.connection import SessionLocal, get_db
import logging
from typing import Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

@app.task
def advance_world_time(world_id: str, days: int = 1):
    """
    Advance the game time for a world by a specified number of days.
    
    Args:
        world_id (str): The ID of the world
        days (int): Number of days to advance (default: 1)
    """
    logger.info(f"Advancing time for world {world_id} by {days} days")
    
    db = SessionLocal()
    try:
        # Using raw database operations for now until we have a proper TimeService
        from app.models.core import Worlds
        
        # Get the world
        world = db.query(Worlds).filter(Worlds.world_id == world_id).first()
        if not world:
            logger.error(f"World {world_id} not found")
            return {"status": "error", "message": "World not found"}
        
        # Calculate new game day
        current_day = world.current_game_day or 0
        new_day = current_day + days
        
        # Update world
        world.current_game_day = new_day
        world.last_updated = datetime.now()
        
        # Determine if season should change
        days_per_season = 30  # Configurable value
        seasons = ["spring", "summer", "autumn", "winter"]
        
        if current_day // days_per_season != new_day // days_per_season:
            # Season changed
            current_season_index = seasons.index(world.current_season) if world.current_season in seasons else 0
            new_season_index = (current_season_index + 1) % len(seasons)
            new_season = seasons[new_season_index]
            
            world.current_season = new_season
            logger.info(f"Season changed in world {world_id} from {seasons[current_season_index]} to {new_season}")
        
        # Commit changes
        db.commit()
        
        # Determine if year changed
        days_per_year = days_per_season * len(seasons)
        year_changed = current_day // days_per_year != new_day // days_per_year
        
        return {
            "status": "success",
            "world_id": world_id,
            "previous_day": current_day,
            "new_day": new_day,
            "current_season": world.current_season,
            "year_changed": year_changed,
            "days_advanced": days
        }
        
    except Exception as e:
        db.rollback()
        logger.exception(f"Error advancing time for world {world_id}: {e}")
        return {"status": "error", "message": f"Error: {str(e)}"}
    finally:
        db.close()

@app.task
def process_seasonal_events(world_id: str):
    """
    Process season-specific events for a world.
    
    Args:
        world_id (str): The ID of the world
    """
    logger.info(f"Processing seasonal events for world {world_id}")
    
    db = SessionLocal()
    try:
        # Using raw database operations for now until we have a proper TimeService
        from app.models.core import Worlds
        
        # Get the world
        world = db.query(Worlds).filter(Worlds.world_id == world_id).first()
        if not world:
            logger.error(f"World {world_id} not found")
            return {"status": "error", "message": "World not found"}
        
        # Get current season
        current_season = world.current_season
        
        # Process season-specific events
        events = []
        
        if current_season == "spring":
            # Spring events: growth, births, etc.
            events.append("spring_planting")
            events.append("animal_births")
            
        elif current_season == "summer":
            # Summer events: abundance, harvests, etc.
            events.append("summer_harvest")
            events.append("increased_trading")
            
        elif current_season == "autumn":
            # Autumn events: preparations for winter, etc.
            events.append("autumn_harvest")
            events.append("winter_preparations")
            
        elif current_season == "winter":
            # Winter events: scarcity, challenging conditions, etc.
            events.append("winter_storms")
            events.append("resource_scarcity")
        
        # Here you would trigger specific tasks for each event
        # For example, for "spring_planting" you might increase crop growth rates
        
        return {
            "status": "success",
            "world_id": world_id,
            "season": current_season,
            "events_processed": events
        }
        
    except Exception as e:
        logger.exception(f"Error processing seasonal events for world {world_id}: {e}")
        return {"status": "error", "message": f"Error: {str(e)}"}
    finally:
        db.close()

@app.task
def advance_time_for_all_worlds(days: int = 1):
    """
    Advance time for all active worlds.
    
    Args:
        days (int): Number of days to advance (default: 1)
    """
    logger.info(f"Advancing time for all worlds by {days} days")
    
    db = SessionLocal()
    try:
        # Get all active worlds
        from app.models.core import Worlds
        worlds = db.query(Worlds).filter(Worlds.active == True).all()
        
        results = []
        for world in worlds:
            try:
                # Call the task for each world
                result = advance_world_time(str(world.world_id), days)
                results.append({
                    "world_id": str(world.world_id),
                    "status": result["status"]
                })
                
                # If the time advance was successful, process seasonal events
                if result["status"] == "success":
                    process_seasonal_events(str(world.world_id))
                
            except Exception as e:
                logger.exception(f"Error advancing time for world {world.world_id}: {e}")
                results.append({
                    "world_id": str(world.world_id),
                    "status": "error",
                    "message": str(e)
                })
        
        return {
            "status": "success",
            "worlds_processed": len(results),
            "results": results
        }
        
    except Exception as e:
        logger.exception(f"Error advancing time for all worlds: {e}")
        return {"status": "error", "message": f"Error: {str(e)}"}
    finally:
        db.close()

@app.task
def schedule_daily_world_updates():
    """
    Task that schedules all daily world updates.
    This is a master task that should be scheduled to run once per real-world day.
    """
    logger.info("Scheduling daily world updates")
    
    try:
        # Schedule time advancement for all worlds
        advance_time_for_all_worlds.delay(days=1)
        
        # Schedule other daily tasks here
        # For example:
        # - Population growth
        # - Resource regeneration
        # - Economy updates
        # - Character needs (hunger, rest, etc.)
        
        return {
            "status": "success",
            "message": "Daily world updates scheduled"
        }
        
    except Exception as e:
        logger.exception(f"Error scheduling daily world updates: {e}")
        return {"status": "error", "message": f"Error: {str(e)}"}