# app/workers/area_worker.py
import logging
import random
from typing import Dict, Any, Optional, Tuple

from app.workers.celery_app import app
from database.connection import SessionLocal
from app.game_state.services.area_service import AreaService

logger = logging.getLogger(__name__)

@app.task
def generate_encounter(area_id: str, entity_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate a random encounter in an area.
    
    Args:
        area_id (str): ID of the area
        entity_id (Optional[str]): ID of the entity encountering (player, trader, etc.)
        
    Returns:
        Dict[str, Any]: Result of encounter generation
    """
    logger.info(f"Generating encounter in area {area_id}" + 
               (f" for entity {entity_id}" if entity_id else ""))
    
    db = SessionLocal()
    try:
        service = AreaService(db)
        result = service.generate_encounter(area_id, entity_id)
        
        return result
        
    except Exception as e:
        logger.exception(f"Error generating encounter: {e}")
        return {"status": "error", "message": f"Error generating encounter: {str(e)}"}
    finally:
        db.close()

@app.task
def resolve_encounter(encounter_id: str, entity_id: str, 
                   resolution_type: str = "default") -> Dict[str, Any]:
    """
    Resolve an area encounter.
    
    Args:
        encounter_id (str): ID of the encounter to resolve
        entity_id (str): ID of the entity resolving the encounter
        resolution_type (str): Type of resolution (flee, fight, negotiate, etc.)
        
    Returns:
        Dict[str, Any]: Result of the resolution
    """
    logger.info(f"Resolving encounter {encounter_id} by entity {entity_id} using {resolution_type}")
    
    db = SessionLocal()
    try:
        service = AreaService(db)
        result = service.resolve_encounter(encounter_id, entity_id, resolution_type)
        
        return result
        
    except Exception as e:
        logger.exception(f"Error resolving encounter: {e}")
        return {"status": "error", "message": f"Error resolving encounter: {str(e)}"}
    finally:
        db.close()

@app.task
def connect_areas(area_id: str, connected_area_id: str) -> Dict[str, Any]:
    """
    Connect two areas together for travel purposes.
    
    Args:
        area_id (str): ID of the first area
        connected_area_id (str): ID of the area to connect to
        
    Returns:
        Dict[str, Any]: Result of the connection
    """
    logger.info(f"Connecting areas {area_id} and {connected_area_id}")
    
    db = SessionLocal()
    try:
        service = AreaService(db)
        success = service.connect_areas(area_id, connected_area_id)
        
        return {
            "status": "success" if success else "error",
            "message": "Areas connected successfully" if success else "Failed to connect areas"
        }
        
    except Exception as e:
        logger.exception(f"Error connecting areas: {e}")
        return {"status": "error", "message": f"Error connecting areas: {str(e)}"}
    finally:
        db.close()

@app.task
def connect_area_to_settlement(area_id: str, settlement_id: str) -> Dict[str, Any]:
    """
    Connect an area to a settlement for travel purposes.
    
    Args:
        area_id (str): ID of the area
        settlement_id (str): ID of the settlement
        
    Returns:
        Dict[str, Any]: Result of the connection
    """
    logger.info(f"Connecting area {area_id} to settlement {settlement_id}")
    
    db = SessionLocal()
    try:
        service = AreaService(db)
        success = service.connect_area_to_settlement(area_id, settlement_id)
        
        return {
            "status": "success" if success else "error",
            "message": "Area connected to settlement successfully" if success else "Failed to connect area to settlement"
        }
        
    except Exception as e:
        logger.exception(f"Error connecting area to settlement: {e}")
        return {"status": "error", "message": f"Error connecting area to settlement: {str(e)}"}
    finally:
        db.close()

@app.task
def process_all_areas(world_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Process all areas, updating state and generating ambient events.
    
    Args:
        world_id (Optional[str]): ID of the world to process areas for, or None for all worlds
        
    Returns:
        Dict[str, Any]: Result of processing all areas
    """
    logger.info(f"Processing all areas" + (f" in world {world_id}" if world_id else ""))
    
    db = SessionLocal()
    try:
        service = AreaService(db)
        result = service.process_all_areas(world_id)
        
        return result
        
    except Exception as e:
        logger.exception(f"Error processing all areas: {e}")
        return {"status": "error", "message": f"Error processing all areas: {str(e)}"}
    finally:
        db.close()

@app.task
def update_danger_level(area_id: str, new_danger_level: int) -> Dict[str, Any]:
    """
    Update the danger level of an area.
    
    Args:
        area_id (str): ID of the area
        new_danger_level (int): New danger level (1-5)
        
    Returns:
        Dict[str, Any]: Result of the update
    """
    logger.info(f"Updating danger level for area {area_id} to {new_danger_level}")
    
    db = SessionLocal()
    try:
        service = AreaService(db)
        result = service.update_danger_level(area_id, new_danger_level)
        
        return result
        
    except Exception as e:
        logger.exception(f"Error updating danger level: {e}")
        return {"status": "error", "message": f"Error updating danger level: {str(e)}"}
    finally:
        db.close()

@app.task
def create_area(name: str, area_type: str, world_id: str, 
               location_x: float, location_y: float, radius: float = 10.0, 
               danger_level: int = 1, description: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a new area entity.
    
    Args:
        name (str): Name of the area
        area_type (str): Type of area (forest, mountains, plains, etc.)
        world_id (str): ID of the world this area belongs to
        location_x (float): X coordinate
        location_y (float): Y coordinate
        radius (float): Size/radius of the area
        danger_level (int): 1-5 rating of area danger
        description (Optional[str]): Description of the area
        
    Returns:
        Dict[str, Any]: Result of area creation
    """
    logger.info(f"Creating new area {name} in world {world_id}")
    
    db = SessionLocal()
    try:
        service = AreaService(db)
        area = service.create_area(
            name=name,
            area_type=area_type,
            world_id=world_id,
            location=(location_x, location_y),
            radius=radius,
            danger_level=danger_level,
            description=description
        )
        
        if area:
            return {
                "status": "success",
                "area_id": area.entity_id,
                "name": area.name,
                "message": f"Area {name} created successfully"
            }
        else:
            return {"status": "error", "message": "Failed to create area"}
        
    except Exception as e:
        logger.exception(f"Error creating area: {e}")
        return {"status": "error", "message": f"Error creating area: {str(e)}"}
    finally:
        db.close()