# app/workers/world_worker.py
import logging
from typing import Dict, Any, Optional

from app.workers.celery_app import app
from database.connection import SessionLocal
from app.game_state.services.world_service import WorldService

logger = logging.getLogger(__name__)

@app.task
def advance_game_day(world_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Advance the game day for a specific world or all worlds.
    This task handles time progression, seasons, weather, and related systems.
    
    Args:
        world_id (Optional[str]): ID of the world to advance, or None for all worlds
        
    Returns:
        Dict[str, Any]: Result of the advancement process
    """
    logger.info(f"Advancing game day for" + (f" world {world_id}" if world_id else " all worlds"))
    
    db = SessionLocal()
    try:
        service = WorldService(db)
        
        if world_id:
            # Advance a single world
            result = service.advance_world_day(world_id)
        else:
            # Advance all worlds
            result = service.process_all_worlds()
            
        return result
        
    except Exception as e:
        logger.exception(f"Error advancing game day: {e}")
        return {"status": "error", "message": f"Error advancing game day: {str(e)}"}
    finally:
        db.close()

@app.task
def trigger_world_event(world_id: str, event_type: str, 
                     location_x: float, location_y: float, 
                     radius: float, duration: int, 
                     name: Optional[str] = None,
                     description: Optional[str] = None) -> Dict[str, Any]:
    """
    Trigger a new world event for a specific world.
    
    Args:
        world_id (str): ID of the world where the event occurs
        event_type (str): Type of event (natural_disaster, war, festival, etc.)
        location_x (float): X coordinate of event center
        location_y (float): Y coordinate of event center
        radius (float): Area of effect radius
        duration (int): Duration in game days
        name (Optional[str]): Name of the event
        description (Optional[str]): Description of the event
        
    Returns:
        Dict[str, Any]: Result of the event creation
    """
    logger.info(f"Triggering {event_type} event for world {world_id}")
    
    db = SessionLocal()
    try:
        service = WorldService(db)
        result = service.trigger_world_event(
            world_id=world_id,
            event_type=event_type,
            location=(location_x, location_y),
            radius=radius,
            duration=duration,
            name=name,
            description=description
        )
        
        return result
        
    except Exception as e:
        logger.exception(f"Error triggering world event: {e}")
        return {"status": "error", "message": f"Error triggering world event: {str(e)}"}
    finally:
        db.close()

@app.task
def update_faction_relation(world_id: str, faction_id: str,
                        other_faction_id: str, relation_value: float) -> Dict[str, Any]:
    """
    Update the relation between two factions in a world.
    
    Args:
        world_id (str): ID of the world
        faction_id (str): ID of the first faction
        other_faction_id (str): ID of the second faction
        relation_value (float): New relation value (-1.0 to 1.0)
        
    Returns:
        Dict[str, Any]: Result of the relation update
    """
    logger.info(f"Updating faction relation in world {world_id}: {faction_id} -> {other_faction_id} = {relation_value}")
    
    db = SessionLocal()
    try:
        service = WorldService(db)
        result = service.update_faction_relation(
            world_id=world_id,
            faction_id=faction_id,
            other_faction_id=other_faction_id,
            relation_value=relation_value
        )
        
        return result
        
    except Exception as e:
        logger.exception(f"Error updating faction relation: {e}")
        return {"status": "error", "message": f"Error updating faction relation: {str(e)}"}
    finally:
        db.close()