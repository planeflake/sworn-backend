from app.workers.celery_app import app
from database.connection import SessionLocal
from app.models.core import Settlements, Worlds, Areas, TravelRoutes, AreaEncounters, AreaEncounterTypes
from app.models.trader import TraderModel
from app.ai.simple_decision import SimpleDecisionEngine
from app.game_state.manager import GameStateManager
from app.game_state.services.trader_service import TraderService
from app.game_state.services.logging_service import LoggingService
from app.models.tasks import Tasks 
from sqlalchemy import String, cast, select, text
from sqlalchemy.orm import Session
import logging
import json
import random
import uuid
import asyncio
from datetime import datetime
from collections import deque
from typing import List, Dict, Set, Optional, Tuple, Any
from app.game_state.services.logging_service import LoggingService
from database.connection import SessionLocal, get_db

db = SessionLocal()

logger = logging.getLogger(__name__)
decision_engine = SimpleDecisionEngine()
logService = LoggingService(db)

# Configure MCTS parameters
MCTS_SIMULATIONS = 100  # Default number of simulations to run
USE_MCTS = True  # Toggle to switch between MCTS and simple decision engine

def check_trader_active_tasks(db: Session, trader_id: str) -> Optional[str]:
    """
    Check if a trader has any active tasks by querying the Tasks table directly.
    
    Args:
        db: Database session
        trader_id: The ID of the trader to check
        
    Returns:
        Optional[str]: The task_id of an active task if found, None otherwise
    """
    from app.models.tasks import Tasks
    
    # Query for any tasks targeting this trader that are active and not completed/failed
    active_task = db.query(Tasks).filter(
        Tasks.target_id == trader_id,
        Tasks.status.in_(['available', 'accepted', 'in_progress']),
        Tasks.is_active == True
    ).first()
    
    #entity_name = active_task.entity_name if active_task else None

    if active_task:
        logger.info(f"Found active task {active_task.task_id} for trader {trader_id}")
        logService.log_action(
            world_id=str(active_task.world_id),
            action_type="task_check",
            action_subtype="active_task",
            entity_id=trader_id,
            entity_type="trader",
            entity_name=active_task.character_id,
            details={"task_id": str(active_task.task_id)}
        )
        return str(active_task.task_id)
    
    return None

@app.task
def process_trader_movement(trader_id: str):
    """
    Process trader movement decision and execution.
    This task uses TraderService which integrates MCTS for intelligent decision making.
    
    Args:
        trader_id: The ID of the trader to process
        
    Returns:
        Dict: Result status and details
    """
    logger.info(f"Processing movement for trader {trader_id}")
    
    db = SessionLocal()
    try:
        # Get the trader
        trader = db.query(TraderModel).filter(TraderModel.trader_id == trader_id).first()
        if not trader:
            logger.error(f"Trader {trader_id} not found")
            return {"status": "error", "message": f"Trader {trader_id} not found"}
        
        # Check if trader has an active task using a more robust method
        # This checks the Tasks table directly rather than relying on the active_task_id field
        active_task_id = check_trader_active_tasks(db, trader_id)
        
        if active_task_id:
            # Update the trader's active_task_id field to ensure it stays in sync
            if trader.active_task_id != active_task_id:
                trader.active_task_id = active_task_id
                db.commit()
                logger.info(f"Updated trader {trader_id} active_task_id to {active_task_id}")
                logService.log_action(
                    db=db,
                    action_type="task_check",
                    action_subtype="active_task",
                    entity_id=trader_id,
                    entity_type="trader",
                    details={"task_id": active_task_id}
                )
            
            logger.info(f"Trader {trader_id} has active task {active_task_id}, cannot move")
            return {
                "status": "success",
                "message": f"Trader {trader_id} waiting for task {active_task_id}",
                "action": "waiting_for_task"
            }
        elif trader.active_task_id:
            # If trader has active_task_id but no actual active tasks, clear it
            logger.info(f"Trader {trader_id} has active_task_id {trader.active_task_id} but no actual active tasks, clearing it")
            trader.active_task_id = None
            db.commit()
        
        # Process based on current location
        if trader.current_area_id:
            # Trader is traveling - continue journey
            return continue_area_travel(trader_id)
            
        elif trader.current_settlement_id:
            # Trader is in a settlement - decide where to go next
            
            # Check if trader has a destination settlement
            if trader.destination_id and trader.destination_id != trader.current_settlement_id:
                logger.info(f"Trader {trader_id} ready to travel to destination {trader.destination_id}")
                
                # Find path to destination
                from app.workers.area_worker import find_path_between_settlements
                path = find_path_between_settlements(
                    start_id=trader.current_settlement_id,
                    end_id=trader.destination_id,
                    db=db
                )
                
                if path:
                    # Start journey
                    dest_settlement = db.query(Settlements).filter(
                        Settlements.settlement_id == trader.destination_id
                    ).first()
                    
                    destination_name = dest_settlement.settlement_name if dest_settlement else "Unknown"
                    
                    trader.current_settlement_id = None
                    trader.journey_started = datetime.now()
                    trader.journey_progress = 0
                    trader.current_area_id = path[0]
                    trader.journey_path = json.dumps(path)
                    trader.path_position = 0
                    trader.destination_settlement_name = destination_name
                    
                    db.commit()
                    
                    logger.info(f"Trader {trader_id} started journey to {destination_name}")
                    
                    # Log the trader movement in the action log
                    try:
                        logging_service = LoggingService()
                        logging_service.log_trader_movement(
                            trader_id=str(trader_id),
                            trader_name=trader.npc_name or f"Trader {trader_id}",
                            world_id=str(trader.world_id),
                            from_location_id=str(trader.current_settlement_id),
                            from_location_type="settlement",
                            from_location_name=current_settlement.settlement_name if current_settlement else "Unknown",
                            to_location_id=str(trader.destination_id),
                            to_location_type="settlement",
                            to_location_name=destination_name,
                            details={
                                "action": "journey_started",
                                "path_length": len(path),
                                "first_area": path[0] if path else None
                            }
                        )
                    except Exception as e:
                        logger.warning(f"Failed to log trader movement: {e}")
                    
                    return {
                        "status": "success",
                        "message": f"Trader {trader_id} started journey to {destination_name}",
                        "action": "journey_started",
                        "destination": destination_name,
                        "path_length": len(path)
                    }
                else:
                    logger.warning(f"Could not find path from {trader.current_settlement_id} to {trader.destination_id}")
                    return {
                        "status": "error",
                        "message": f"Could not find path to destination",
                        "action": "no_path"
                    }
            else:
                # Trader doesn't have a destination yet - 30% chance to pick a new one
                if random.random() < 0.3:
                    # Get the current settlement
                    current_settlement = db.query(Settlements).filter(
                        Settlements.settlement_id == trader.current_settlement_id
                    ).first()
                    
                    if current_settlement and current_settlement.connections:
                        # Parse connections
                        connections = []
                        if isinstance(current_settlement.connections, str):
                            try:
                                connections = json.loads(current_settlement.connections)
                            except:
                                pass
                        elif isinstance(current_settlement.connections, list):
                            connections = current_settlement.connections
                        
                        # Filter valid connections
                        valid_connections = []
                        for conn in connections:
                            dest_id = conn.get('destination_id')
                            if dest_id and not dest_id.startswith('11111') and dest_id != '00000000-0000-0000-0000-000000000000':
                                valid_connections.append(conn)
                        
                        # Select a random destination
                        if valid_connections:
                            chosen_conn = random.choice(valid_connections)
                            destination_id = chosen_conn.get('destination_id')
                            
                            # Get destination name
                            dest_settlement = db.query(Settlements).filter(
                                Settlements.settlement_id == destination_id
                            ).first()
                            
                            if dest_settlement:
                                trader.destination_id = destination_id
                                db.commit()
                                
                                logger.info(f"Trader {trader_id} selected destination: {dest_settlement.settlement_name}")
                                
                                return {
                                    "status": "success",
                                    "message": f"Trader {trader_id} selected destination {dest_settlement.settlement_name}",
                                    "action": "destination_selected",
                                    "destination": dest_settlement.settlement_name
                                }
                
                # No movement this time
                logger.info(f"Trader {trader_id} remains at settlement {trader.current_settlement_id}")
                return {
                    "status": "success",
                    "message": f"Trader {trader_id} remains at current settlement",
                    "action": "no_movement"
                }
        else:
            # Trader is not in a settlement or area - this is an error state
            logger.error(f"Trader {trader_id} has no current location (neither settlement nor area)")
            
            # Try to fix this by putting them in their home settlement or a random settlement
            home_settlement_id = trader.home_settlement_id
            if home_settlement_id:
                trader.current_settlement_id = home_settlement_id
                trader.current_area_id = None
                db.commit()
                
                logger.info(f"Fixed trader {trader_id} location by setting to home settlement {home_settlement_id}")
                
                return {
                    "status": "warning",
                    "message": f"Trader {trader_id} location fixed to home settlement",
                    "action": "location_fixed"
                }
            else:
                # Get a random settlement
                settlement = db.query(Settlements).first()
                if settlement:
                    trader.current_settlement_id = settlement.settlement_id
                    trader.current_area_id = None
                    db.commit()
                    
                    logger.info(f"Fixed trader {trader_id} location by setting to settlement {settlement.settlement_id}")
                    
                    return {
                        "status": "warning",
                        "message": f"Trader {trader_id} location fixed to random settlement",
                        "action": "location_fixed"
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"Trader {trader_id} has no location and no settlements available",
                        "action": "error_state"
                    }
    
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
        # Get the trader
        trader = db.query(TraderModel).filter(TraderModel.trader_id == trader_id).first()
        if not trader:
            logger.error(f"Trader {trader_id} not found")
            return {"status": "error", "message": f"Trader {trader_id} not found"}
        
        # Check if trader has an active task using a more robust method
        active_task_id = check_trader_active_tasks(db, trader_id)
        
        if active_task_id:
            # Update the trader's active_task_id field to ensure it stays in sync
            if trader.active_task_id != active_task_id:
                trader.active_task_id = active_task_id
                db.commit()
                logger.info(f"Updated trader {trader_id} active_task_id to {active_task_id}")
            
            logger.info(f"Trader {trader_id} has active task {active_task_id}, cannot move")
            return {
                "status": "success", 
                "message": f"Trader {trader_id} waiting for task {active_task_id}",
                "action": "waiting_for_task"
            }
        elif trader.active_task_id:
            # If trader has active_task_id but no actual active tasks, clear it
            logger.info(f"Trader {trader_id} has active_task_id {trader.active_task_id} but no actual active tasks, clearing it")
            trader.active_task_id = None
            db.commit()
        
        # Check if trader is in an area
        if not trader.current_area_id:
            logger.error(f"Trader {trader_id} is not in an area, cannot continue area travel")
            return {"status": "error", "message": "Trader is not in an area", "action": "not_in_area"}
        
        # Check if trader has a journey path
        if not trader.journey_path:
            logger.error(f"Trader {trader_id} has no journey path")
            return {"status": "error", "message": "Trader has no journey path", "action": "no_path"}
        
        try:
            # Parse the journey path
            path = json.loads(trader.journey_path)
            current_position = trader.path_position if trader.path_position is not None else 0
            
            # Update position
            current_position += 1
            
            # Check if reached destination
            if current_position >= len(path):
                # Journey complete, arrive at destination
                trader.current_settlement_id = trader.destination_id
                trader.current_area_id = None
                trader.journey_path = None
                trader.path_position = None
                trader.journey_progress = 100
                
                # Get destination name for logging
                settlement = db.query(Settlements).filter(
                    Settlements.settlement_id == trader.destination_id
                ).first()
                
                settlement_name = settlement.settlement_name if settlement else "Unknown"
                
                logger.info(f"Trader {trader_id} arrived at destination: {settlement_name}")
                
                # Update trader in database
                db.commit()
                
                # Log the trader arrival in the action log
                try:
                    logging_service = LoggingService(db)
                    logging_service.log_trader_movement(
                        trader_id=str(trader_id),
                        trader_name=trader.npc_name or f"Trader {trader_id}",
                        world_id=str(trader.world_id),
                        to_location_id=str(trader.destination_id),
                        to_location_type="settlement",
                        to_location_name=settlement_name,
                        details={
                            "action": "journey_completed",
                            "journey_duration": (datetime.now() - trader.journey_started).total_seconds() if trader.journey_started else None,
                            "final_progress": 100
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to log trader arrival: {e}")
                
                return {
                    "status": "success",
                    "message": f"Trader {trader_id} arrived at destination",
                    "action": "journey_completed",
                    "destination": settlement_name
                }
            else:
                # Move to next area
                next_area_id = path[current_position]
                
                # Get area details for logging
                area = db.query(Areas).filter(Areas.area_id == next_area_id).first()
                area_name = area.area_name if area else "Unknown Area"
                
                trader.current_area_id = next_area_id
                trader.path_position = current_position
                
                # Calculate journey progress percentage
                journey_progress = int((current_position / (len(path) - 1)) * 100)
                trader.journey_progress = journey_progress
                
                # Check for events - 20% chance to generate an encounter
                event_triggered = False
                event_type = None
                
                if random.random() < 0.2:
                    # Select a random issue type
                    issue_types = [
                        "bandit_attack",
                        "broken_cart",
                        "sick_animals",
                        "lost_cargo",
                        "food_shortage"
                    ]
                    issue_type = random.choice(issue_types)
                    event_type = issue_type
                    
                    # Create a task for the trader
                    from app.workers.task_worker import create_trader_assistance_task
                    task_result = create_trader_assistance_task(
                        trader_id=trader_id,
                        area_id=next_area_id,
                        world_id=str(trader.world_id),
                        issue_type=issue_type
                    )
                    
                    if task_result.get("status") == "success":
                        event_triggered = True
                        logger.info(f"Created event '{issue_type}' for trader {trader_id} in area {area_name}")
                    else:
                        logger.error(f"Failed to create task for trader {trader_id}: {task_result.get('message')}")
                
                # Update trader in database
                db.commit()
                
                # Return result
                if event_triggered:
                    return {
                        "status": "success",
                        "message": f"Trader {trader_id} encountered {event_type} in {area_name}",
                        "action": "event_triggered",
                        "area": area_name,
                        "progress": journey_progress,
                        "event_type": event_type
                    }
                else:
                    logger.info(f"Trader {trader_id} moved to area: {area_name} ({journey_progress}% of journey)")
                    
                    # Log the trader area movement
                    try:
                        logging_service = LoggingService(db)
                        from_area = db.query(Areas).filter(Areas.area_id == trader.current_area_id).first()
                        from_area_name = from_area.area_name if from_area else "Unknown Area"
                        
                        logging_service.log_trader_movement(
                            trader_id=str(trader_id),
                            trader_name=trader.npc_name or f"Trader {trader_id}",
                            world_id=str(trader.world_id),
                            from_location_id=str(trader.current_area_id),
                            from_location_type="area",
                            from_location_name=from_area_name,
                            to_location_id=str(next_area_id),
                            to_location_type="area",
                            to_location_name=area_name,
                            details={
                                "action": "area_moved",
                                "progress": journey_progress,
                                "path_position": current_position,
                                "destination_id": str(trader.destination_id),
                                "destination_name": trader.destination_settlement_name
                            }
                        )
                    except Exception as e:
                        logger.warning(f"Failed to log trader area movement: {e}")
                    
                    return {
                        "status": "success",
                        "message": f"Trader {trader_id} moved to area {area_name}",
                        "action": "area_moved",
                        "area": area_name,
                        "progress": journey_progress
                    }
                
        except (json.JSONDecodeError, IndexError) as e:
            logger.exception(f"Error parsing journey path for trader {trader_id}: {e}")
            
            # Reset the trader's journey due to error
            trader.journey_path = None
            trader.path_position = None
            
            # If they have a destination, put them there
            if trader.destination_id:
                trader.current_settlement_id = trader.destination_id
                trader.current_area_id = None
                db.commit()
                
                logger.info(f"Reset trader {trader_id} to destination due to path error")
                
                return {
                    "status": "warning",
                    "message": "Journey path was invalid, trader moved to destination",
                    "action": "path_error_reset"
                }
            else:
                # Find a random settlement
                settlement = db.query(Settlements).first()
                if settlement:
                    trader.current_settlement_id = settlement.settlement_id
                    trader.current_area_id = None
                    db.commit()
                    
                    logger.info(f"Reset trader {trader_id} to random settlement due to path error")
                    
                    return {
                        "status": "warning",
                        "message": "Journey path was invalid, trader moved to random settlement",
                        "action": "path_error_reset"
                    }
                else:
                    return {
                        "status": "error",
                        "message": "Journey path was invalid and no settlements available",
                        "action": "path_error"
                    }
    
    except Exception as e:
        logger.exception(f"Error continuing area travel for trader {trader_id}: {e}")
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
        # Get all traders
        query = db.query(TraderModel)
        if world_id:
            query = query.filter(TraderModel.world_id == world_id)
        
        all_traders = query.all()
        
        # Filter out traders with active tasks by checking the Tasks table directly
        traders_without_tasks = []
        traders_with_tasks = []
        
        for trader in all_traders:
            active_task_id = check_trader_active_tasks(db, str(trader.trader_id))
            
            if active_task_id:
                # Update the trader's active_task_id field to ensure it stays in sync
                if trader.active_task_id != active_task_id:
                    trader.active_task_id = active_task_id
                    db.commit()
                    logger.info(f"Updated trader {trader.trader_id} active_task_id to {active_task_id}")
                traders_with_tasks.append(trader)
            else:
                # If trader has active_task_id but no actual active tasks, clear it
                if trader.active_task_id:
                    logger.info(f"Trader {trader.trader_id} has active_task_id {trader.active_task_id} but no actual active tasks, clearing it")
                    trader.active_task_id = None
                    db.commit()
                traders_without_tasks.append(trader)
        
        # Process only traders without active tasks
        traders = traders_without_tasks
        total_traders = len(all_traders)
        available_traders = len(traders)
        waiting_traders = len(traders_with_tasks)
        
        logger.info(f"Found {total_traders} total traders, {available_traders} available for processing, {waiting_traders} waiting for tasks")
        
        # Process each trader
        processed_count = 0
        waiting_for_task_count = 0
        
        for trader in traders:
            try:
                # Check if trader should move or generate an event
                trader_id = str(trader.trader_id)
                logger.info(f"Processing trader {trader_id}")
                
                # First check if trader is in an area (traveling)
                if trader.current_area_id:
                    # Process area travel - chance for events
                    
                    # Calculate journey progress percentage
                    if trader.journey_path and trader.path_position is not None:
                        path = json.loads(trader.journey_path)
                        current_position = trader.path_position
                        
                        # Update position
                        current_position += 1
                        
                        # Check if reached destination
                        if current_position >= len(path):
                            # Journey complete, arrive at destination
                            trader.current_settlement_id = trader.destination_id
                            trader.current_area_id = None
                            trader.journey_path = None
                            trader.path_position = 0
                            trader.journey_progress = 100
                            
                            logger.info(f"Trader {trader_id} arrived at destination: {trader.destination_settlement_name}")
                            
                        else:
                            # Move to next area
                            next_area_id = path[current_position]
                            trader.current_area_id = next_area_id
                            trader.path_position = current_position
                            
                            # Calculate journey progress percentage
                            trader.journey_progress = int((current_position / (len(path) - 1)) * 100)
                            
                            # 20% chance to generate an encounter in the area
                            if random.random() < 0.2:
                                # Call a function similar to the updated create_trader_assistance_task
                                # but without using asyncio
                                from app.workers.task_worker import create_trader_assistance_task
                                
                                # Select a random issue type
                                issue_types = [
                                    "bandit_attack",
                                    "broken_cart",
                                    "sick_animals",
                                    "lost_cargo",
                                    "food_shortage"
                                ]
                                issue_type = random.choice(issue_types)
                                
                                # Create a task for the trader
                                result = create_trader_assistance_task(
                                    trader_id=trader_id,
                                    area_id=next_area_id,
                                    world_id=str(trader.world_id),
                                    issue_type=issue_type
                                )
                                
                                if result.get("status") == "success":
                                    waiting_for_task_count += 1
                                    logger.info(f"Created event '{issue_type}' for trader {trader_id} in area {next_area_id}")
                            else:
                                logger.info(f"Trader {trader_id} moved to area: {next_area_id} ({trader.journey_progress}% of journey)")
                        
                        # Commit changes
                        db.commit()
                        processed_count += 1
                
                # Otherwise trader is in a settlement and might start a new journey
                elif trader.current_settlement_id and not trader.active_task_id:
                    # Trader is in a settlement - decide on next destination
                    # Simplified logic - just find a random connected settlement
                    current_settlement = db.query(Settlements).filter(
                        Settlements.settlement_id == trader.current_settlement_id
                    ).first()
                    
                    if current_settlement and current_settlement.connections:
                        # Parse connections
                        connections = []
                        if isinstance(current_settlement.connections, str):
                            try:
                                connections = json.loads(current_settlement.connections)
                            except:
                                pass
                        elif isinstance(current_settlement.connections, list):
                            connections = current_settlement.connections
                        
                        # Filter valid connections
                        valid_connections = []
                        for conn in connections:
                            dest_id = conn.get('destination_id')
                            if dest_id and not dest_id.startswith('11111') and dest_id != '00000000-0000-0000-0000-000000000000':
                                valid_connections.append(conn)
                        
                        # Select a random destination
                        if valid_connections:
                            # 30% chance to start journey
                            if random.random() < 0.3:
                                # Choose random destination
                                chosen_conn = random.choice(valid_connections)
                                destination_id = chosen_conn.get('destination_id')
                                
                                # Get destination name
                                dest_settlement = db.query(Settlements).filter(
                                    Settlements.settlement_id == destination_id
                                ).first()
                                
                                destination_name = dest_settlement.settlement_name if dest_settlement else "Unknown"
                                
                                # Try to find a path between settlements
                                from app.workers.area_worker import find_path_between_settlements
                                path = find_path_between_settlements(
                                    start_id=trader.current_settlement_id,
                                    end_id=destination_id,
                                    db=db
                                )
                                
                                if path:
                                    # Start journey
                                    trader.current_settlement_id = None
                                    trader.destination_id = destination_id
                                    trader.destination_settlement_name = destination_name
                                    trader.journey_started = datetime.now()
                                    trader.journey_progress = 0
                                    trader.current_area_id = path[0]
                                    trader.journey_path = json.dumps(path)
                                    trader.path_position = 0
                                    
                                    logger.info(f"Trader {trader_id} started journey to {destination_name}")
                                    
                                    # Commit changes
                                    db.commit()
                                    processed_count += 1
                            else:
                                logger.info(f"Trader {trader_id} remains at {current_settlement.settlement_name}")
            except Exception as e:
                logger.exception(f"Error processing trader {trader.trader_id}: {e}")
                # Continue with next trader
                continue
        
        # Summary of results
        result = {
            "status": "success",
            "total": total_traders,
            "available": available_traders,
            "waiting_for_task": waiting_traders,
            "processed": processed_count,
            "new_tasks_created": waiting_for_task_count,
            "message": f"Successfully processed {processed_count} of {available_traders} available traders, {waiting_traders} waiting for tasks, created {waiting_for_task_count} new tasks"
        }
        
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
        from app.models.core import Areas, Worlds
        import random
        
        # Query for active traders
        traders_query = db.query(TraderModel)
        if world_id:
            traders_query = traders_query.filter(TraderModel.world_id == world_id)
        
        # Get all traders first
        all_traders = traders_query.all()
        
        # Filter out traders with active tasks by checking the Tasks table directly
        traders = []
        for trader in all_traders:
            active_task_id = check_trader_active_tasks(db, str(trader.trader_id))
            if not active_task_id:
                traders.append(trader)
        
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

# Legacy functions to support backwards compatibility
def generate_simple_encounter(trader_id=None, area_id=None):
    """Simplified version of encounter generation that works with our actual database schema"""
    if not area_id or not trader_id:
        return {"status": "error", "error": "Must provide area_id and trader_id"}
    

    from database.connection import SessionLocal
    db = SessionLocal()
    try:
        # Get the area
        area = db.query(Areas).filter(Areas.area_id == area_id).first()
        if not area:
            return {"status": "error", "error": f"Area {area_id} not found"}
        
        # Get the trader
        trader = db.query(TraderModel).filter(TraderModel.trader_id == trader_id).first()
        if not trader:
            return {"status": "error", "error": f"Trader {trader_id} not found"}
        
        # Determine if an encounter happens (based on area danger level)
        # Default to danger level 1 if not specified
        danger_level = getattr(area, 'danger_level', 1) or 1
        encounter_chance = 0.1 + (danger_level * 0.05)  # 10% base chance + 5% per danger level
        
        # Roll for encounter
        encounter_roll = random.random()
        if encounter_roll > encounter_chance:
            # No encounter this time
            logger.info(f"No encounter generated for trader {trader_id} in area {area.area_name}")
            return {"status": "success", "result": "no_encounter"}
        
        # Get a random encounter type
        encounter_types = db.query(AreaEncounterTypes).limit(10).all()
        if not encounter_types:
            logger.warning("No encounter types found in database")
            return {"status": "success", "result": "no_encounter"}
        
        selected_encounter = random.choice(encounter_types)
        
        # Create the encounter with only the fields that exist in our database
        encounter_id = str(uuid.uuid4())
        
        # Use SQL directly to avoid using fields that don't exist in the database
        db.execute(
            text("""
            INSERT INTO area_encounters
                (encounter_id, area_id, encounter_type_id, is_active, is_completed, 
                current_state, created_at, resolved_at, resolved_by, resolution_outcome_id, custom_narrative)
            VALUES
                (:encounter_id, :area_id, :encounter_type_id, true, false, 
                'initial', CURRENT_TIMESTAMP, NULL, NULL, NULL, :narrative)
            """),
            {
                "encounter_id": encounter_id,
                "area_id": area_id,
                "encounter_type_id": selected_encounter.encounter_type_id,
                "narrative": f"Trader {trader.npc_name} encountered {selected_encounter.encounter_name} in {area.area_name}"
            }
        )
        
        db.commit()
        
        logger.info(f"Generated {selected_encounter.encounter_name} encounter for trader {trader_id} in {area.area_name}")
        
        return {
            "status": "success", 
            "result": "encounter_created",
            "encounter_id": encounter_id,
            "encounter_name": selected_encounter.encounter_name,
            "description": selected_encounter.description if hasattr(selected_encounter, 'description') else "No description"
        }
        
    except Exception as e:
        db.rollback()
        logger.exception(f"Error generating encounter: {e}")
        return {"status": "error", "error": str(e)}
    finally:
        db.close()