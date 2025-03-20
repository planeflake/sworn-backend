from workers.celery_app import app
from database.connection import SessionLocal
from models.core import Traders, Settlements, Worlds, Areas, TravelRoutes, AreaEncounters, AreaEncounterTypes
from app.ai.simple_decision import SimpleDecisionEngine
from app.game_state.manager import GameStateManager
from sqlalchemy import String, cast, select, text
import logging
import json
import random
import uuid
from datetime import datetime
from collections import deque
from typing import List, Dict, Set, Optional, Tuple

logger = logging.getLogger(__name__)
decision_engine = SimpleDecisionEngine()

# Configure MCTS parameters
MCTS_SIMULATIONS = 100  # Default number of simulations to run
USE_MCTS = True  # Toggle to switch between MCTS and simple decision engine

@app.task
def process_trader_movement(trader_id):
    """Process trader movement decision and execution with travel through areas"""
    from database.connection import SessionLocal
    db = SessionLocal()
    try:
        trader = db.query(Traders).filter(Traders.trader_id == trader_id).first()
        if not trader:
            logger.error(f"Trader {trader_id} not found")
            return False
        
        trader_name = trader.npc_name if trader.npc_name else f"Trader {trader.trader_id}"
        
        # Check if trader is already traveling through areas
        if trader.current_area_id:
            return continue_area_travel(trader_id)
        
        # If trader has neither a current settlement nor a current area, place them in their home settlement
        if not trader.current_settlement_id and not trader.current_area_id:
            logger.info(f"Trader {trader_id} has no current location, placing at home settlement")
            trader.current_settlement_id = trader.home_settlement_id
            db.commit()
        
        # If trader is in a settlement, decide next settlement to visit
        if trader.current_settlement_id:
            # Get current settlement
            current_settlement = db.query(Settlements).filter(
                Settlements.settlement_id == trader.current_settlement_id
            ).first()
            
            if not current_settlement or not current_settlement.connections:
                logger.error(f"Current settlement or its connections not found for trader {trader_id}")
                return False
            
            # Parse connections JSON if needed
            settlement_connections = []
            if isinstance(current_settlement.connections, str):
                try:
                    settlement_connections = json.loads(current_settlement.connections)
                except (json.JSONDecodeError, TypeError) as e:
                    logger.error(f"Invalid connections JSON for settlement {current_settlement.settlement_id}: {e}")
                    return False
            elif isinstance(current_settlement.connections, list):
                settlement_connections = current_settlement.connections
            else:
                logger.error(f"Unexpected connections type for settlement {current_settlement.settlement_id}: {type(current_settlement.connections)}")
                return False
            
            # Ensure connections is a list of dictionaries with settlement_id and destination_id
            connections = []
            for connection in settlement_connections:
                # Validate each connection
                if not isinstance(connection, dict):
                    logger.warning(f"Skipping invalid connection (not a dict): {connection}")
                    continue
                    
                # Check required fields
                if 'destination_id' not in connection:
                    logger.warning(f"Skipping connection missing destination_id: {connection}")
                    continue
                    
                if 'destination' not in connection:
                    logger.warning(f"Skipping connection missing destination name: {connection}")
                    continue
                
                # Verify destination ID is valid (not placeholder)
                dest_id = connection['destination_id']
                if dest_id.startswith('11111') or dest_id == '00000000-0000-0000-0000-000000000000':
                    logger.warning(f"Skipping connection with placeholder destination ID: {dest_id}")
                    continue
                
                # Add to validated connections
                connections.append({
                    'settlement_id': current_settlement.settlement_id,
                    'destination_id': connection['destination_id'],
                    'destination_name': connection['destination']
                })
            
            # Check if we have any valid connections
            if not connections:
                logger.error(f"No valid connections found for settlement {current_settlement.settlement_id}")
                return False
            
            # Get the current game day from the world
            world = db.query(Worlds).filter(Worlds.world_id == trader.world_id).first()
            if not world:
                logger.error(f"World {trader.world_id} not found")
                return False
            
            # Build trader data for AI
            trader_data = {
                'trader_id': trader.trader_id,
                'current_settlement_id': trader.current_settlement_id,
                'world_day': world.current_game_day,
                'home_settlement_id': trader.home_settlement_id,
                'available_connections': connections,
                'schedule': trader.schedule,
                'biome_preferences': trader.biome_preferences,
                'destination_id': trader.destination_id
            }
            
            # Determine the next move using either MCTS or simple decision engine
            if USE_MCTS:
                # Use MCTS for decision making
                logger.info(f"Using MCTS to determine next move for trader {trader_id}")
                game_state_manager = GameStateManager(db)
                mcts_decision = game_state_manager.get_mcts_trader_decision(trader_id, MCTS_SIMULATIONS)
                
                logger.info(f"MCTS decision result: {mcts_decision}")  # Log the full decision
                
                if mcts_decision["status"] != "success":
                    logger.error(f"MCTS decision failed: {mcts_decision.get('message', 'Unknown error')}")
                    # Fall back to simple decision engine
                    next_move = decision_engine.decide_trader_movement(trader_data)
                    logger.info(f"Falling back to simple decision engine for trader {trader_id}")
                else:
                    # Format MCTS decision to match simple decision engine output
                    next_move = {
                        "next_settlement_id": mcts_decision["next_settlement_id"],
                        "next_settlement_name": mcts_decision["next_settlement_name"]
                    }
                    logger.info(f"Using MCTS decision: {next_move}")
                    
                    # Log MCTS details
                    stats = mcts_decision.get("mcts_stats", {})
                    logger.info(f"MCTS decision details for trader {trader_name}:")
                    logger.info(f"  - Destination: {next_move['next_settlement_name']} ({next_move['next_settlement_id']})")
                    logger.info(f"  - Simulations: {stats.get('simulations', 0)}")
                    logger.info(f"  - Actions evaluated: {stats.get('actions_evaluated', 0)}")
            else:
                # Use the simple decision engine
                next_move = decision_engine.decide_trader_movement(trader_data)
                logger.info(f"Using simple decision engine for trader {trader_id}")
            
            # Find travel route between current and next settlement
            # Safely get the IDs and ensure they're valid
            if not current_settlement or not next_move.get('next_settlement_id'):
                logger.error(f"Invalid settlement IDs for route lookup: current={current_settlement}, next={next_move.get('next_settlement_id')}")
                return False
                
            # Log the exact values for debugging
            logger.info(f"Looking for route from {current_settlement.settlement_id} to {next_move['next_settlement_id']}")
            
            # Check if destination exists before moving there
            dest_settlement = db.query(Settlements).filter(
                Settlements.settlement_id == next_move['next_settlement_id']
            ).first()
            
            if not dest_settlement:
                # Try to find by string ID
                dest_settlement = db.query(Settlements).filter(
                    cast(Settlements.settlement_id, String) == str(next_move['next_settlement_id'])
                ).first()
            
            if not dest_settlement:
                logger.error(f"Cannot move trader - destination settlement {next_move['next_settlement_id']} not found")
                return False
            
            # Try to find a dynamic route through connected areas
            path = find_path_between_settlements(
                db,
                str(current_settlement.settlement_id),
                str(dest_settlement.settlement_id)
            )
            
            if not path:
                logger.warning(f"No path found through areas, checking for predefined route")
                
                # Try to find predefined route as fallback - use a fresh session
                from database.connection import SessionLocal
                route_db = SessionLocal()
                
                try:
                    start_id = str(current_settlement.settlement_id)
                    end_id = str(dest_settlement.settlement_id)
                    
                    # Query for exact match
                    result = route_db.execute(
                        text("""
                        SELECT * FROM travel_routes 
                        WHERE start_settlement_id::text = :start_id 
                        AND end_settlement_id::text = :end_id
                        LIMIT 1
                        """),
                        {"start_id": start_id, "end_id": end_id}
                    )
                    route_row = result.first()
                    
                    # Try reverse direction if not found
                    if not route_row:
                        result = route_db.execute(
                            text("""
                            SELECT * FROM travel_routes 
                            WHERE start_settlement_id::text = :end_id 
                            AND end_settlement_id::text = :start_id
                            LIMIT 1
                            """),
                            {"start_id": start_id, "end_id": end_id}
                        )
                        route_row = result.first()
                except Exception as e:
                    logger.exception(f"Error querying travel routes: {e}")
                    route_row = None
                    route_db.rollback()
                finally:
                    route_db.close()
                
                # Extract path if found
                if route_row and route_row.path:
                    try:
                        path = json.loads(route_row.path)
                        
                        # Check if we found the route in reverse direction
                        if route_row.start_settlement_id == dest_settlement.settlement_id:
                            logger.info(f"Found reverse route, reversing path")
                            path = list(reversed(path))
                    except (ValueError, TypeError) as e:
                        logger.error(f"Invalid path in travel route: {e}")
                        path = []
            
            # If no path found through either method, use direct movement
            if not path:
                # Fall back to direct movement if no route exists but destination is valid
                trader.current_settlement_id = dest_settlement.settlement_id
                trader.destination_id = dest_settlement.settlement_id
                db.commit()
                logger.info(f"Trader {trader_name}({trader_id}) moved directly to {dest_settlement.settlement_name}({dest_settlement.settlement_id})")
                return True
            
            # Start the journey through areas
            trader.current_settlement_id = None  # Leaving settlement
            trader.destination_id = next_move['next_settlement_id']
            trader.destination_settlement_name = next_move['next_settlement_name']
            trader.journey_started = datetime.now()
            trader.journey_progress = 0
            trader.current_area_id = path[0]  # Enter first area
            trader.journey_path = json.dumps(path)
            trader.path_position = 0
            
            # Save updates
            db.commit()
            
            # Generate potential encounter in first area
            first_area = db.query(Areas).filter(Areas.area_id == path[0]).first()
            if first_area:
                area_name = first_area.area_name if first_area.area_name else "an unknown area"
                logger.warning(f"Trader {trader_name}({trader_id}) left {current_settlement.settlement_name} and entered {area_name}")
                
                # Update current_settlement_id to the area_id
                trader.current_settlement_id = path[0]
                
                # Trigger potential encounter with our own implementation
                generate_simple_encounter.delay(trader_id=trader_id, area_id=path[0])
            else:
                logger.error(f"First area in path not found for trader {trader_id}")

            logger.warning(f"Trader {trader_name}({trader_id}) started journey to {next_move['next_settlement_name']}({next_move['next_settlement_id']})")
            db.commit()
            return True
            
        else:
            logger.error(f"Trader {trader_id} has neither current settlement nor current area")
            return False
            
    except Exception as e:
        logger.exception(f"Error processing trader movement: {e}")
        return False
    finally:
        db.close()

@app.task
def continue_area_travel(trader_id):
    """Continue trader journey through areas"""
    from database.connection import SessionLocal
    db = SessionLocal()
    try:
        trader = db.query(Traders).filter(Traders.trader_id == trader_id).first()
        if not trader:
            logger.error(f"Trader {trader_id} not found")
            return False
        
        trader_name = trader.npc_name if trader.npc_name else f"Trader {trader.trader_id}"
        
        # Check if trader has active encounter that needs resolution
        # Use only columns that exist in the actual database
        from sqlalchemy import select
        
        # Create a manual select statement with only available columns
        select_stmt = select(
            AreaEncounters.encounter_id,
            AreaEncounters.area_id,
            AreaEncounters.encounter_type_id,
            AreaEncounters.is_active,
            AreaEncounters.is_completed,
            AreaEncounters.current_state,
            AreaEncounters.created_at,
            AreaEncounters.resolved_at,
            AreaEncounters.resolved_by,
            AreaEncounters.resolution_outcome_id,
            AreaEncounters.custom_narrative
        ).where(
            AreaEncounters.area_id == trader.current_area_id,
            AreaEncounters.is_active == True,
            AreaEncounters.is_completed == False
        ).limit(1)
        
        result = db.execute(select_stmt)
        active_encounter_row = result.first()
        
        # Create an encounter object if found
        active_encounter = None
        if active_encounter_row:
            active_encounter = AreaEncounters()
            active_encounter.encounter_id = active_encounter_row[0]
            active_encounter.area_id = active_encounter_row[1]
            active_encounter.encounter_type_id = active_encounter_row[2]
            active_encounter.is_active = active_encounter_row[3]
            active_encounter.is_completed = active_encounter_row[4]
            active_encounter.current_state = active_encounter_row[5]
            active_encounter.created_at = active_encounter_row[6]
            active_encounter.resolved_at = active_encounter_row[7]
            active_encounter.resolved_by = active_encounter_row[8]
            active_encounter.resolution_outcome_id = active_encounter_row[9]
            active_encounter.custom_narrative = active_encounter_row[10]
        
        if active_encounter:
            # Resolve encounter automatically
            outcome = resolve_trader_encounter(trader_id, active_encounter.encounter_id)
            logger.info(f"Trader {trader_name} resolved encounter: {outcome}")
        
        # Get journey path
        if not trader.journey_path:
            logger.error(f"Trader {trader_id} has no journey path")
            return False
            
        try:
            path = json.loads(trader.journey_path)
            current_position = trader.path_position
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid journey path for trader {trader_id}: {e}")
            return False
        
        # Update journey progress
        current_position += 1
        
        # Check if reached the end of the path
        if current_position >= len(path):
            # Journey complete, arrive at destination settlement
            trader.current_settlement_id = trader.destination_id
            trader.current_area_id = None
            trader.journey_path = None
            trader.path_position = 0
            trader.journey_progress = 100
            
            destination_settlement = db.query(Settlements).filter(
                Settlements.settlement_id == trader.destination_id
            ).first()
            
            destination_name = trader.destination_settlement_name
            if destination_settlement and destination_settlement.settlement_name:
                destination_name = destination_settlement.settlement_name
            
            logger.warning(f"Trader {trader_name}({trader_id}) arrived at destination: {destination_name}")
            
            db.commit()
            return True
        
        # Move to next area
        logger.warning('MOVING TO NEXT AREA!!!!'), Areas.filter(Areas.area_id == next_area_id).first().area_name
        next_area_id = path[current_position]
        trader.current_area_id = next_area_id
        trader.current_settlement_id = next_area_id  # Update current_settlement_id to the area_id
        trader.path_position = current_position
        
        # Calculate journey progress percentage
        trader.journey_progress = int((current_position / (len(path) - 1)) * 100)
        
        db.commit()
        
        # Get area info for logging
        next_area = db.query(Areas).filter(Areas.area_id == next_area_id).first()
        area_name = next_area.area_name if next_area and next_area.area_name else "an unknown area"
        
        logger.info(f"Trader {trader_name}({trader_id}) moved to area: {area_name} ({trader.journey_progress}% of journey)")
        
        # Generate potential encounter in new area
        generate_simple_encounter.delay(trader_id=trader_id, area_id=next_area_id)
        
        return True
    
    except Exception as e:
        logger.exception(f"Error continuing trader area travel: {e}")
        return False
    finally:
        db.close()

def find_path_between_settlements(db, start_settlement_id: str, end_settlement_id: str) -> List[str]:
    """
    Dynamically find a path of connected areas between two settlements.
    Uses breadth-first search to find the shortest path.
    
    Args:
        db: Database session
        start_settlement_id: ID of the starting settlement
        end_settlement_id: ID of the destination settlement
        
    Returns:
        List of area IDs that form a path between the settlements, or empty list if no path found
    """
    try:
        # Get connected areas for start settlement
        start_areas = get_settlement_connected_areas(db, start_settlement_id)
        if not start_areas:
            logger.warning(f"No connected areas found for settlement {start_settlement_id}")
            return []
        
        # Get connected areas for destination settlement
        end_areas = get_settlement_connected_areas(db, end_settlement_id)
        if not end_areas:
            logger.warning(f"No connected areas found for settlement {end_settlement_id}")
            return []
        
        logger.info(f"Finding path from settlement {start_settlement_id} (connected to {len(start_areas)} areas) "
                    f"to settlement {end_settlement_id} (connected to {len(end_areas)} areas)")
        
        # Special case: check if settlements share a common area
        common_areas = set(start_areas).intersection(set(end_areas))
        if common_areas:
            common_area = list(common_areas)[0]
            logger.info(f"Settlements share common area {common_area}")
            return [common_area]
        
        # BFS to find path between areas
        queue = deque([(area_id, [area_id]) for area_id in start_areas])
        visited = set(start_areas)
        
        while queue:
            current_area, path = queue.popleft()
            
            # Get connected areas
            neighbors = get_area_connected_areas(db, current_area)
            
            for neighbor in neighbors:
                if neighbor in end_areas:
                    # Found a path to destination
                    final_path = path + [neighbor]
                    logger.info(f"Found path through {len(final_path)} areas: {final_path}")
                    return final_path
                
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        
        logger.warning(f"No path found between settlements {start_settlement_id} and {end_settlement_id}")
        return []
        
    except Exception as e:
        logger.exception(f"Error finding path between settlements: {e}")
        return []

def get_settlement_connected_areas(db, settlement_id: str) -> List[str]:
    """Get all areas directly connected to a settlement"""
    # Use separate database session to avoid transaction issues
    from database.connection import SessionLocal
    session = SessionLocal()
    
    try:
        # Skip the connected_areas column check since it doesn't exist
        # Go directly to querying areas table for references to this settlement
        areas = session.query(Areas).filter(
            text("connected_settlements::text LIKE :pattern")
        ).params(
            pattern=f'%{settlement_id}%'
        ).all()
        
        connected = []
        for area in areas:
            if area.connected_settlements:
                try:
                    settlement_ids = json.loads(area.connected_settlements)
                    if settlement_id in settlement_ids:
                        connected.append(area.area_id)
                except (json.JSONDecodeError, TypeError):
                    continue
        
        return connected
    
    except Exception as e:
        logger.exception(f"Error getting connected areas for settlement {settlement_id}: {e}")
        session.rollback()  # Ensure transaction is rolled back on error
        return []
    
    finally:
        session.close()  # Always close the session

def get_area_connected_areas(db, area_id: str) -> List[str]:
    """Get all areas directly connected to another area"""
    # Use separate database session to avoid transaction issues
    from database.connection import SessionLocal
    session = SessionLocal()
    
    try:
        # Query the area
        result = session.execute(
            text("""
            SELECT connected_areas 
            FROM areas 
            WHERE area_id::text = :area_id
            LIMIT 1
            """),
            {"area_id": area_id}
        ).first()
        
        if result and result[0]:
            # Parse JSON array
            try:
                return json.loads(result[0])
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Invalid connected_areas JSON for area {area_id}")
                return []
        
        return []
    
    except Exception as e:
        logger.exception(f"Error getting connected areas for area {area_id}: {e}")
        session.rollback()  # Ensure transaction is rolled back on error
        return []
        
    finally:
        session.close()  # Always close the session

def resolve_trader_encounter(trader_id, encounter_id):
    """Resolve an encounter for a trader automatically"""
    from database.connection import SessionLocal
    db = SessionLocal()
    try:
        # Get the encounter using available columns
        select_stmt = select(
            AreaEncounters.encounter_id,
            AreaEncounters.area_id,
            AreaEncounters.encounter_type_id,
            AreaEncounters.is_active,
            AreaEncounters.is_completed,
            AreaEncounters.current_state,
            AreaEncounters.created_at,
            AreaEncounters.resolved_at,
            AreaEncounters.resolved_by,
            AreaEncounters.resolution_outcome_id,
            AreaEncounters.custom_narrative
        ).where(
            AreaEncounters.encounter_id == encounter_id,
            AreaEncounters.is_completed == False
        ).limit(1)
        
        result = db.execute(select_stmt)
        encounter_row = result.first()
        
        if not encounter_row:
            return "encounter_not_found"
        
        # Simple outcome generation (this is a simplified version of what area_worker.resolve_encounter does)
        # Mark the encounter as completed
        db.execute(
            text("""
                UPDATE area_encounters 
                SET is_completed = true, 
                    is_active = false, 
                    current_state = 'resolved',
                    resolved_at = CURRENT_TIMESTAMP,
                    resolved_by = :trader_id
                WHERE encounter_id = :encounter_id
            """),
            {
                "trader_id": trader_id,
                "encounter_id": encounter_id
            }
        )
        
        # Generate random outcome effects
        effect_types = ["none", "good", "bad", "mixed"]
        effect = random.choice(effect_types)
        
        outcome_name = f"Encounter {effect}"
        trader = db.query(Traders).filter(Traders.trader_id == trader_id).first()
        
        if not trader:
            db.rollback()
            return "trader_not_found"
        
        # Apply random effects based on encounter outcome
        if effect == "good":
            # Good outcome - gain some gold
            gold_gain = random.randint(10, 50)
            trader.gold += gold_gain
            outcome_name = f"Found {gold_gain} gold"
        elif effect == "bad":
            # Bad outcome - lose some cart health
            cart_damage = random.randint(5, 15)
            trader.cart_health = max(0, trader.cart_health - cart_damage)
            outcome_name = f"Cart damaged by {cart_damage}%"
        elif effect == "mixed":
            # Mixed outcome - lose some guards but gain gold
            if trader.hired_guards > 0:
                guards_lost = random.randint(1, min(trader.hired_guards, 2))
                trader.hired_guards = max(0, trader.hired_guards - guards_lost)
                gold_gain = random.randint(30, 80)
                trader.gold += gold_gain
                outcome_name = f"Lost {guards_lost} guard(s) but found {gold_gain} gold"
        
        db.commit()
        return outcome_name
    
    except Exception as e:
        db.rollback()
        logger.exception(f"Error resolving trader encounter: {e}")
        return "error"
    finally:
        db.close()

@app.task
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
        trader = db.query(Traders).filter(Traders.trader_id == trader_id).first()
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

@app.task
def process_all_traders(world_id=None):
    """Process movement for all traders in a world (or all worlds if none specified)"""
    from database.connection import SessionLocal
    db = SessionLocal()
    try:
        query = db.query(Traders)
        if world_id:
            query = query.filter(Traders.world_id == world_id)
        
        traders = query.all()
        for trader in traders:
            process_trader_movement.delay(str(trader.trader_id))
        return {"status": "success", "count": len(traders)}
    finally:
        db.close()