# workers/trader_worker_new.py
from workers.celery_app import app
from database.connection import SessionLocal
import logging
from typing import Optional

# Import the service that contains the actual implementation
from app.game_state.services.trader_service import TraderService

logger = logging.getLogger(__name__)

@app.task
def process_trader_movement(trader_id: str):
    """
    Process trader movement decision and execution with travel through areas.
    
    This task delegates to the TraderService, which contains the actual implementation
    using the new class-based game state architecture.
    
    Args:
        trader_id (str): The ID of the trader to process
        
    Returns:
        dict: Result of the movement processing
    """
    logger.info(f"Processing movement for trader {trader_id}")
    
    # Create database session
    db = SessionLocal()
    try:
        # Create service with the database session
        service = TraderService(db)
        
        # Delegate to service implementation
        result = service.process_trader_movement(trader_id)
        
        # Log the result
        if result["status"] == "success":
            logger.info(f"Successfully processed trader {trader_id}: {result.get('action', 'unknown action')}")
        else:
            logger.warning(f"Failed to process trader {trader_id}: {result.get('message', 'Unknown error')}")
        
        return result
    except Exception as e:
        logger.exception(f"Error in process_trader_movement task: {e}")
        return {"status": "error", "message": f"Task error: {str(e)}"}
    finally:
        db.close()

@app.task
def continue_area_travel(trader_id: str):
    """
    Continue trader journey through areas.
    
    This task delegates to the TraderService, which contains the actual implementation
    using the new class-based game state architecture.
    
    Args:
        trader_id (str): The ID of the trader
        
    Returns:
        dict: Result of the travel progress
    """
    logger.info(f"Continuing area travel for trader {trader_id}")
    
    # Create database session
    db = SessionLocal()
    try:
        # Create service with the database session
        service = TraderService(db)
        
        # Delegate to service implementation
        result = service.continue_area_travel(trader_id)
        
        # Log the result
        if result["status"] == "success":
            logger.info(f"Successfully continued travel for trader {trader_id}: {result.get('action', 'unknown action')}")
        else:
            logger.warning(f"Failed to continue travel for trader {trader_id}: {result.get('message', 'Unknown error')}")
        
        return result
    except Exception as e:
        logger.exception(f"Error in continue_area_travel task: {e}")
        return {"status": "error", "message": f"Task error: {str(e)}"}
    finally:
        db.close()

@app.task
def process_all_traders(world_id: Optional[str] = None):
    """
    Process movement for all traders in a world (or all worlds if none specified).
    
    This task delegates to the TraderService, which contains the actual implementation
    using the new class-based game state architecture.
    
    Args:
        world_id (str, optional): The world ID to process traders for, or None for all worlds
        
    Returns:
        dict: Result of processing all traders
    """
    logger.info(f"Processing all traders" + (f" in world {world_id}" if world_id else ""))
    
    # Create database session
    db = SessionLocal()
    try:
        # Create service with the database session
        service = TraderService(db)
        
        # Delegate to service implementation
        result = service.process_all_traders(world_id)
        
        # Log the result
        if result["status"] == "success":
            logger.info(f"Successfully processed {result.get('processed', 0)}/{result.get('total', 0)} traders")
        else:
            logger.warning(f"Failed to process traders: {result.get('message', 'Unknown error')}")
        
        return result
    except Exception as e:
        logger.exception(f"Error in process_all_traders task: {e}")
        return {"status": "error", "message": f"Task error: {str(e)}"}
    finally:
        db.close()