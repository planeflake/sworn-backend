from celery import shared_task
from app.game_state.services.item_service import ItemService
from sqlalchemy.orm import Session
from database.connection import get_db
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

@shared_task(name="animal_worker.update_item_state")
def update_item_state(animal_id: str):
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

@shared_task(name="animal_worker.process_all_items")
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

@shared_task(name="animal_worker.create_items")
def create_items(area_id: str, animal_type: str = None, count: int = 1):
    """
    create new items in a specific area.
    
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

