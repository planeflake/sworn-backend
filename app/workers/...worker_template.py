# app/workers/worker_template.py
from app.workers.celery_app import app
from database.connection import SessionLocal
# Replace with your service import
from app.game_state.services.quest_service import ServiceTemplate
import logging
import asyncio
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

@app.task
def process_entity(entity_id: str) -> Dict[str, Any]:
    """
    Process entity-specific task.
    
    Args:
        entity_id: The ID of the entity to process
        
    Returns:
        Dict: Result status and details
    """
    logger.info(f"Processing entity {entity_id}")
    
    db = SessionLocal()
    try:
        # Create service
        service = ServiceTemplate(db)
        
        # Process entity using async function
        result = asyncio.run(service.process_entity(entity_id))
        
        # Log the result
        log_level = logging.ERROR if result.get("status") != "success" else logging.INFO
        logger.log(log_level, f"Entity processing result: {result}")
        
        return result
    
    except Exception as e:
        logger.exception(f"Error processing entity: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@app.task
def perform_specialized_action(entity_id: str, action_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Perform a specialized action on the entity.
    
    Args:
        entity_id: The ID of the entity
        action_params: Optional parameters for the action
        
    Returns:
        Dict: Result status and details
    """
    logger.info(f"Performing specialized action for entity {entity_id} with params: {action_params}")
    
    db = SessionLocal()
    try:
        # Create service
        service = ServiceTemplate(db)
        
        # Perform specialized action using async function
        result = asyncio.run(service.perform_specialized_action(entity_id, action_params or {}))
        
        log_level = logging.ERROR if result.get("status") != "success" else logging.INFO
        logger.log(log_level, f"Specialized action result: {result}")
        
        return result
    
    except Exception as e:
        logger.exception(f"Error performing specialized action: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@app.task
def process_all_entities(world_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Process all entities in a world or all worlds.
    
    Args:
        world_id: Optional ID of the world to process entities for
        
    Returns:
        Dict: Summary of processing results
    """
    logger.info(f"Processing all entities" + (f" in world {world_id}" if world_id else ""))
    
    db = SessionLocal()
    try:
        # Create service
        service = ServiceTemplate(db)
        
        # Process all entities using async function
        result = asyncio.run(service.process_all_entities(world_id))
        
        log_level = logging.ERROR if result.get("status") != "success" else logging.INFO
        logger.log(log_level, f"Process all entities result: {result}")
        
        return result
    
    except Exception as e:
        logger.exception(f"Error processing all entities: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@app.task
def scheduled_task(parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Task to be run on a schedule via Celery Beat.
    
    Args:
        parameters: Optional parameters for the scheduled task
        
    Returns:
        Dict: Summary of task results
    """
    logger.info(f"Running scheduled task with parameters: {parameters}")
    
    db = SessionLocal()
    try:
        # Create service
        service = ServiceTemplate(db)
        
        # Run scheduled task
        result = asyncio.run(service.scheduled_task(parameters or {}))
        
        log_level = logging.ERROR if result.get("status") != "success" else logging.INFO
        logger.log(log_level, f"Scheduled task result: {result}")
        
        return result
    
    except Exception as e:
        logger.exception(f"Error running scheduled task: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

# Example of how to call these tasks from Python code:
"""
from app.workers.worker_template import process_entity, process_all_entities

# Call immediately
result = process_entity.apply_async(args=[entity_id])

# Call with delay
process_entity.apply_async(args=[entity_id], countdown=30)

# Call periodically (this would typically go in a beat schedule)
process_all_entities.apply_async(args=[world_id], countdown=60)
"""