# workers/animal_worker.py
from app.workers.celery_app import app
from app.game_state.services.animal_service import AnimalService
from sqlalchemy.orm import Session
from database.connection import get_db
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

@app.task
def update_animal_state(animal_id: str):
    """
    Update an animal's state based on its current state and environment.
    
    Args:
        animal_id (str): The ID of the animal to update
    
    Returns:
        dict: Result of the operation
    """
    logger.info(f"Updating animal state for {animal_id}")
    
    try:
        db = get_db()
        with Session(db) as session:
            # Create service with DB session
            animal_service = AnimalService(session)
            
            # Update animal state
            result = animal_service.update_animal_state(animal_id)
            
            logger.info(f"Animal state updated for {animal_id}: {result}")
            return result
            
    except Exception as e:
        logger.exception(f"Error updating animal state for {animal_id}: {e}")
        return {"status": "error", "message": str(e)}

@app.task
def process_all_animals(world_id: str = None):
    """
    Process all animals in the world, handling movement, hunger, health, etc.
    
    Args:
        world_id (str, optional): Filter by world ID
    
    Returns:
        dict: Result of processing all animals
    """
    logger.info(f"Processing all animals" + (f" in world {world_id}" if world_id else ""))
    
    try:
        db = get_db()
        with Session(db) as session:
            # Create service with DB session
            animal_service = AnimalService(session)
            
            # Process all animals
            result = animal_service.process_all_animals(world_id)
            
            logger.info(f"All animals processed: {result}")
            return result
            
    except Exception as e:
        logger.exception(f"Error processing all animals: {e}")
        return {"status": "error", "message": str(e)}

@app.task
def migrate_animals(world_id: str = None, season: str = None):
    """
    Handle animal migrations based on season changes.
    
    Args:
        world_id (str, optional): Filter by world ID
        season (str, optional): Current season to determine migration patterns
    
    Returns:
        dict: Result of animal migrations
    """
    current_season = season or _get_current_season(world_id)
    logger.info(f"Migrating animals for season {current_season}" + (f" in world {world_id}" if world_id else ""))
    
    try:
        db = get_db()
        with Session(db) as session:
            # Create service with DB session
            animal_service = AnimalService(session)
            
            # Process migrations
            result = animal_service.migrate_animals(world_id, current_season)
            
            logger.info(f"Animal migration completed: {result}")
            return result
            
    except Exception as e:
        logger.exception(f"Error migrating animals: {e}")
        return {"status": "error", "message": str(e)}

@app.task
def spawn_animals(area_id: str, animal_type: str = None, count: int = 1):
    """
    Spawn new animals in a specific area.
    
    Args:
        area_id (str): The ID of the area to spawn animals in
        animal_type (str, optional): Type of animal to spawn
        count (int, optional): Number of animals to spawn
    
    Returns:
        dict: Result of spawning animals
    """
    logger.info(f"Spawning {count} {animal_type or 'random'} animals in area {area_id}")
    
    try:
        db = get_db()
        with Session(db) as session:
            # Create service with DB session
            animal_service = AnimalService(session)
            
            # Spawn animals
            result = animal_service.spawn_animals(area_id, animal_type, count)
            
            logger.info(f"Animals spawned in area {area_id}: {result}")
            return result
            
    except Exception as e:
        logger.exception(f"Error spawning animals in area {area_id}: {e}")
        return {"status": "error", "message": str(e)}

def _get_current_season(world_id: str = None):
    """Helper function to get current season from world settings"""
    try:
        db = get_db()
        with Session(db) as session:
            # In a real implementation, you would get this from the world state
            # For now, just return a placeholder based on the current month
            month = datetime.now().month
            if month in [12, 1, 2]:
                return "winter"
            elif month in [3, 4, 5]:
                return "spring"
            elif month in [6, 7, 8]:
                return "summer"
            else:
                return "fall"
    except Exception:
        # Default to current month-based season if there's an error
        month = datetime.now().month
        if month in [12, 1, 2]:
            return "winter"
        elif month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        else:
            return "fall"