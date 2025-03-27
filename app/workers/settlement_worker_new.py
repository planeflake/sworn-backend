# workers/settlement_worker_new.py
from app.workers.celery_app import app
from database.connection import SessionLocal, get_db
import logging
from typing import Optional

# Import the service that contains the actual implementation
from app.game_state.services.settlement_service import SettlementService

logger = logging.getLogger(__name__)

@app.task
def process_settlement_growth(settlement_id: str):
    """
    Process the growth and production of a settlement.
    
    This task delegates to the SettlementService, which contains the actual implementation
    using the new class-based game state architecture.
    
    Args:
        settlement_id (str): The ID of the settlement to process
        
    Returns:
        dict: Result of the settlement processing
    """
    logger.info(f"Processing growth for settlement {settlement_id}")
    
    # Create database session
    db = SessionLocal()
    try:
        # Create service with the database session
        service = SettlementService(db)
        
        # Delegate to service implementation
        result = service.process_settlement_growth(settlement_id)
        
        # Log the result
        if result["status"] == "success":
            logger.info(f"Successfully processed settlement {settlement_id}")
            logger.debug(f"Settlement processing details: {result}")
        else:
            logger.warning(f"Failed to process settlement {settlement_id}: {result.get('message', 'Unknown error')}")
        
        return result
    except Exception as e:
        logger.exception(f"Error in process_settlement_growth task: {e}")
        return {"status": "error", "message": f"Task error: {str(e)}"}
    finally:
        db.close()

@app.task
def create_new_settlement(name: str, location_id: str, world_id: str):
    """
    Create a new settlement at the specified location.
    
    Args:
        name (str): The name of the settlement
        location_id (str): The ID of the location (area)
        world_id (str): The ID of the world
        
    Returns:
        dict: Result of settlement creation
    """
    logger.info(f"Creating new settlement {name} at location {location_id}")
    
    # Create database session
    db = SessionLocal()
    try:
        # Create service with the database session
        service = SettlementService(db)
        
        # Delegate to service implementation
        result = service.create_settlement(name, location_id, world_id)
        
        # Log the result
        if result["status"] == "success":
            logger.info(f"Successfully created settlement {name} (ID: {result.get('settlement_id')})")
        else:
            logger.warning(f"Failed to create settlement {name}: {result.get('message', 'Unknown error')}")
        
        return result
    except Exception as e:
        logger.exception(f"Error in create_new_settlement task: {e}")
        return {"status": "error", "message": f"Task error: {str(e)}"}
    finally:
        db.close()

@app.task
def start_building_construction(settlement_id: str, building_type: str):
    """
    Start construction of a new building in a settlement.
    
    Args:
        settlement_id (str): The settlement ID
        building_type (str): The type of building to construct
        
    Returns:
        dict: Result of construction initiation
    """
    logger.info(f"Starting construction of {building_type} in settlement {settlement_id}")
    
    # Create database session
    db = SessionLocal()
    try:
        # Create service with the database session
        service = SettlementService(db)
        
        # Delegate to service implementation
        result = service.start_building_construction(settlement_id, building_type)
        
        # Log the result
        if result["status"] == "success":
            logger.info(f"Successfully started construction of {building_type} in settlement {settlement_id}")
        else:
            logger.warning(f"Failed to start construction in settlement {settlement_id}: {result.get('message', 'Unknown error')}")
        
        return result
    except Exception as e:
        logger.exception(f"Error in start_building_construction task: {e}")
        return {"status": "error", "message": f"Task error: {str(e)}"}
    finally:
        db.close()

@app.task
def start_building_repair(settlement_id: str, building_id: str):
    """
    Start repair of a damaged building.
    
    Args:
        settlement_id (str): The settlement ID
        building_id (str): The building ID
        
    Returns:
        dict: Result of repair initiation
    """
    logger.info(f"Starting repair of building {building_id} in settlement {settlement_id}")
    
    # Create database session
    db = SessionLocal()
    try:
        # Create service with the database session
        service = SettlementService(db)
        
        # Delegate to service implementation
        result = service.start_building_repair(settlement_id, building_id)
        
        # Log the result
        if result["status"] == "success":
            logger.info(f"Successfully started repair of building {building_id} in settlement {settlement_id}")
        else:
            logger.warning(f"Failed to start repair in settlement {settlement_id}: {result.get('message', 'Unknown error')}")
        
        return result
    except Exception as e:
        logger.exception(f"Error in start_building_repair task: {e}")
        return {"status": "error", "message": f"Task error: {str(e)}"}
    finally:
        db.close()

@app.task
def process_all_settlements(world_id: Optional[str] = None):
    """
    Process all settlements in a world (or all worlds if none specified).
    
    This task delegates to the SettlementService, which contains the actual implementation
    using the new class-based game state architecture.
    
    Args:
        world_id (str, optional): The world ID to process settlements for, or None for all worlds
        
    Returns:
        dict: Result of processing all settlements
    """
    logger.info(f"Processing all settlements" + (f" in world {world_id}" if world_id else ""))
    
    # Create database session
    db = SessionLocal()
    try:
        # Create service with the database session
        service = SettlementService(db)
        
        # Delegate to service implementation
        result = service.process_all_settlements(world_id)
        
        # Log the result
        if result["status"] == "success":
            logger.info(f"Successfully processed {result.get('processed', 0)}/{result.get('total', 0)} settlements")
        else:
            logger.warning(f"Failed to process settlements: {result.get('message', 'Unknown error')}")
        
        return result
    except Exception as e:
        logger.exception(f"Error in process_all_settlements task: {e}")
        return {"status": "error", "message": f"Task error: {str(e)}"}
    finally:
        db.close()