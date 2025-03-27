# app/workers/trader_worker_new.py
from app.workers.celery_app import app
from database.connection import SessionLocal
from app.game_state.services.trader_service import TraderService
import logging
import asyncio
from typing import Optional

logger = logging.getLogger(__name__)

@app.task
def process_trader_movement(trader_id: str):
    """
    Process trader movement decision and execution.
    This task uses the new TraderService which integrates MCTS for intelligent decision making.
    
    Args:
        trader_id: The ID of the trader to process
        
    Returns:
        Dict: Result status and details
    """
    logger.info(f"Processing movement for trader {trader_id}")
    
    db = SessionLocal()
    try:
        # Create trader service
        trader_service = TraderService(db)
        
        # Process trader movement using async function
        result = asyncio.run(trader_service.process_trader_movement(trader_id))
        
        # Log the result
        log_level = logging.ERROR if result.get("status") != "success" else logging.INFO
        logger.log(log_level, f"Trader movement result: {result}")
        
        return result
    
    except Exception as e:
        logger.exception(f"Error processing trader movement: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@app.task
def continue_area_travel(trader_id: str):
    """
    Continue a trader's journey through areas.
    
    Args:
        trader_id: The ID of the trader
        
    Returns:
        Dict: Result status and details
    """
    logger.info(f"Continuing area travel for trader {trader_id}")
    
    db = SessionLocal()
    try:
        # Create trader service
        trader_service = TraderService(db)
        
        # Continue area travel using async function
        result = asyncio.run(trader_service.continue_area_travel(trader_id))
        
        log_level = logging.ERROR if result.get("status") != "success" else logging.INFO
        logger.log(log_level, f"Area travel result: {result}")
        
        return result
    
    except Exception as e:
        logger.exception(f"Error continuing area travel: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@app.task
def process_all_traders(world_id: Optional[str] = None):
    """
    Process movement for all traders in a world or all worlds.
    
    Args:
        world_id: Optional ID of the world to process traders for
        
    Returns:
        Dict: Summary of processing results
    """
    logger.info(f"Processing all traders" + (f" in world {world_id}" if world_id else ""))
    
    db = SessionLocal()
    try:
        # Create trader service
        trader_service = TraderService(db)
        
        # Process all traders using async function
        result = asyncio.run(trader_service.process_all_traders(world_id))
        
        log_level = logging.ERROR if result.get("status") != "success" else logging.INFO
        logger.log(log_level, f"Process all traders result: {result}")
        
        return result
    
    except Exception as e:
        logger.exception(f"Error processing all traders: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@app.task
def create_random_trader_tasks(world_id: Optional[str] = None, task_count: int = 3):
    """
    Create a specified number of random trader assistance tasks.
    This can be used to simulate traders needing help even when they're not actually moving.
    
    Args:
        world_id: Optional ID of the world to create tasks for
        task_count: Number of tasks to create
        
    Returns:
        Dict: Summary of task creation
    """
    logger.info(f"Creating {task_count} random trader tasks" + (f" in world {world_id}" if world_id else ""))
    
    db = SessionLocal()
    try:
        # Get traders from the database
        from app.models.core import Traders, Areas, Worlds
        import random
        
        # Query for active traders
        traders_query = db.query(Traders)
        if world_id:
            traders_query = traders_query.filter(Traders.world_id == world_id)
        
        # Only select traders that don't already have active tasks
        traders = traders_query.filter(Traders.active_task_id.is_(None)).all()
        
        if not traders:
            return {
                "status": "warning",
                "message": "No available traders found for creating tasks",
                "created_count": 0
            }
        
        # Get some random areas
        areas = db.query(Areas).limit(50).all()
        if not areas:
            return {
                "status": "warning",
                "message": "No areas found for creating tasks",
                "created_count": 0
            }
        
        # Get the world(s)
        worlds = []
        if world_id:
            world = db.query(Worlds).filter(Worlds.world_id == world_id).first()
            if world:
                worlds = [world]
        else:
            worlds = db.query(Worlds).all()
        
        if not worlds:
            return {
                "status": "warning",
                "message": "No worlds found for creating tasks",
                "created_count": 0
            }
        
        # Issue types for trader tasks
        issue_types = [
            "bandit_attack",
            "broken_cart",
            "sick_animals",
            "lost_cargo",
            "food_shortage"
        ]
        
        # Create tasks
        created_tasks = []
        for _ in range(min(task_count, len(traders))):
            # Select a random trader, area, and issue type
            trader = random.choice(traders)
            area = random.choice(areas)
            issue_type = random.choice(issue_types)
            world = random.choice(worlds)
            
            # Remove the selected trader from the list to avoid duplicates
            traders.remove(trader)
            
            # Create the task
            from app.workers.task_worker import create_trader_assistance_task
            result = create_trader_assistance_task(
                trader_id=str(trader.trader_id),
                area_id=str(area.area_id),
                world_id=str(world.world_id),
                issue_type=issue_type
            )
            
            if result.get("status") == "success":
                created_tasks.append({
                    "trader_id": str(trader.trader_id),
                    "area_id": str(area.area_id),
                    "task_id": result.get("task_id"),
                    "issue_type": issue_type
                })
        
        return {
            "status": "success",
            "message": f"Created {len(created_tasks)} trader tasks",
            "created_count": len(created_tasks),
            "tasks": created_tasks
        }
    
    except Exception as e:
        logger.exception(f"Error creating random trader tasks: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()