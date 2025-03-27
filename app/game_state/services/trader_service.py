# app/game_state/services/trader_service.py
import logging
import json
import uuid
import random
from datetime import datetime

from app.game_state.decision_makers.trader_decision_maker import TraderDecisionMaker
from app.game_state.movement_calculator import MovementCalculator
from app.game_state.managers.trader_manager import TraderManager
from app.game_state.entities.trader import Trader
from app.ai.mcts.states.trader_state import TraderState
from app.ai.mcts.core import MCTS
from typing import List, Dict, Optional, Any, Tuple
from sqlalchemy.orm import Session

from app.models.core import Areas, Traders, Settlements, Worlds

logger = logging.getLogger(__name__)

class TraderService:
    """
    Service layer that bridges between Celery tasks and trader-related game state components.
    This service orchestrates operations between different components of the game_state architecture,
    making it easier to use from the Celery worker tasks.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the trader service with a database session.
        
        Args:
            db (Session): SQLAlchemy database session
        """
        self.db = db
        self.trader_manager = TraderManager(db)
        self.decision_maker = TraderDecisionMaker(db)
        self.movement_calculator = MovementCalculator(db)
    
    async def process_trader_movement(self, trader_id: str) -> Dict[str, Any]:
        """
        Process movement decision and execution for a trader.
        This is the main entry point called by the Celery task.
        
        Args:
            trader_id (str): The ID of the trader to process
            
        Returns:
            Dict[str, Any]: Result of the movement processing
        """
        # Load the trader entity
        trader = await self.trader_manager.load_trader(trader_id)
        if not trader:
            logger.error(f"Trader {trader_id} not found")
            return {"status": "error", "message": "Trader not found"}
        
        trader_name = trader.get_property("name") or f"Trader {trader.trader_id}"
        
        # Check if trader has retired
        if trader.get_property("is_retired", False):
            logger.info(f"Trader {trader_name} has retired and is no longer active")
            return {"status": "success", "action": "none", "message": "Trader has retired"}
        
        # Check if trader is blocked by an active task
        if not trader.get_property("can_move", True):
            active_task_id = trader.get_property("active_task_id")
            if active_task_id:
                logger.info(f"Trader {trader_name} is waiting for task {active_task_id} completion")
                return {
                    "status": "success", 
                    "action": "waiting_for_task",
                    "task_id": active_task_id,
                    "message": f"Trader {trader_name} is waiting for player assistance"
                }
            else:
                # If can_move is false but no active task, this is likely an error state
                # Reset the can_move flag to allow movement
                trader.set_property("can_move", True)
                await self.trader_manager.save_trader(trader)
                logger.warning(f"Trader {trader_name} had movement blocked with no active task")
        
        # Update life goals progress
        trader = await self._check_life_goal_progress(trader)
        
        # Check if trader can retire based on completed retirement goals
        if trader.get_property("can_retire", False) and not trader.get_property("is_retired", False):
            # There's a small chance the trader will decide to retire if eligible
            # Higher chance for older traders or those with more completed goals
            completed_goals = sum(1 for goal in trader.get_property("life_goals", []) if goal.get("completed", False))
            days_active = trader.get_property("days_active", 0)
            
            # Base retirement chance increases with completed goals and days active
            retire_chance = 0.01 + (completed_goals * 0.02) + (days_active / 1000)
            
            # Cap retirement chance at 30%
            retire_chance = min(0.3, retire_chance)
            
            if random.random() < retire_chance:
                # Trader decides to retire
                await self._process_trader_retirement(trader)
                return {
                    "status": "success", 
                    "action": "retired",
                    "message": f"Trader {trader_name} has decided to retire!"
                }
        
        # Check if the trader is already traveling through areas
        if self._is_traveling_through_areas(trader):
            logger.info(f"Trader {trader_name} is currently traveling through areas")
            return await self.continue_area_travel(trader_id)
        
        # If trader has no current location, place at home settlement
        if not trader.get_property("current_location_id"):
            logger.info(f"Trader {trader_id} has no current location, placing at home settlement")
            home_settlement_id = trader.get_property("home_settlement_id")
            if not home_settlement_id:
                return {"status": "error", "message": "Trader has no home settlement"}
            
            trader.set_location(home_settlement_id, "current")
            await self.trader_manager.save_trader(trader)
        
        # Make a movement decision using MCTS
        decision_result = await self._make_mcts_decision(trader)
        
        if decision_result["status"] != "success":
            logger.error(f"Movement decision failed: {decision_result.get('message')}")
            return decision_result
        
        # Execute the movement decision
        return await self._execute_movement_decision(trader, decision_result)
    
    def _is_traveling_through_areas(self, trader: Trader) -> bool:
        """
        Check if the trader is currently traveling through areas.
        
        Args:
            trader (Trader): The trader to check
            
        Returns:
            bool: True if the trader is traveling, False otherwise
        """
        # In this implementation, we'll use the trader's database record to check
        # if they are currently in an area rather than a settlement
        trader_db = self.db.query(Traders).filter(Traders.trader_id == trader.trader_id).first()
        if not trader_db:
            return False
        
        return trader_db.current_area_id is not None
    
    async def _make_mcts_decision(self, trader: Trader) -> Dict[str, Any]:
        """
        Use MCTS to determine the next best move for the trader.
        
        Args:
            trader (Trader): The trader to make a decision for
            
        Returns:
            Dict[str, Any]: Decision result with next destination
        """
        logger.info(f"Making MCTS decision for trader {trader.get_property('name')}")
        
        try:
            # Get the trader's world data
            trader_db = self.db.query(Traders).filter(Traders.trader_id == trader.trader_id).first()
            if not trader_db or not trader_db.world_id:
                return {"status": "error", "message": "Trader has no associated world"}
            
            world = self.db.query(Worlds).filter(Worlds.world_id == trader_db.world_id).first()
            if not world:
                return {"status": "error", "message": "Trader's world not found"}
            
            # Get current settlement data
            current_location_id = trader.get_property("current_location_id")
            current_settlement = self.db.query(Settlements).filter(
                Settlements.settlement_id == current_location_id
            ).first()
            
            if not current_settlement:
                return {"status": "error", "message": "Current settlement not found"}
            
            # Get available connections from this settlement
            settlement_connections = []
            if current_settlement.connections:
                if isinstance(current_settlement.connections, str):
                    try:
                        settlement_connections = json.loads(current_settlement.connections)
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.error(f"Invalid connections JSON for settlement {current_settlement.settlement_id}: {e}")
                        return {"status": "error", "message": "Invalid settlement connections data"}
                elif isinstance(current_settlement.connections, list):
                    settlement_connections = current_settlement.connections
            
            # Prepare world data for decision making
            world_data = {
                "world_id": str(world.world_id),
                "current_game_day": world.current_game_day,
                "current_season": getattr(world, 'current_season', "summer"),
                "locations": {},  # Will be populated with location data
                "markets": {},    # Will be populated with market data
                "settlements": {}  # Settlement data for the MCTS format
            }
            
            # Add location data for current settlement
            world_data["locations"][current_location_id] = {
                "id": current_location_id,
                "name": current_settlement.settlement_name,
                "biome": getattr(current_settlement, 'biome', "temperate"),
                "population": getattr(current_settlement, 'population', 100),
                "settlement_type": getattr(current_settlement, 'settlement_type', "village")
            }
            
            # Add settlement data in format expected by MCTS
            world_data["settlements"][current_location_id] = {
                "id": current_location_id,
                "name": current_settlement.settlement_name,
                "biome": getattr(current_settlement, 'biome', "temperate"),
                "connections": settlement_connections,
                "settlement_type": getattr(current_settlement, 'settlement_type', "village")
            }
            
            # Add market data for current settlement
            world_data["markets"][current_location_id] = {
                "buying": {},  # What the settlement buys (trader sells)
                "selling": {}  # What the settlement sells (trader buys)
            }
            
            # For each connected settlement, add basic info to world data
            for connection in settlement_connections:
                dest_id = connection.get('destination_id')
                if not dest_id or dest_id.startswith('11111') or dest_id == '00000000-0000-0000-0000-000000000000':
                    continue
                    
                dest_settlement = self.db.query(Settlements).filter(
                    Settlements.settlement_id == dest_id
                ).first()
                
                if dest_settlement:
                    # Add to locations for backward compatibility
                    world_data["locations"][dest_id] = {
                        "id": dest_id,
                        "name": dest_settlement.settlement_name,
                        "biome": getattr(dest_settlement, 'biome', "temperate"),
                        "population": getattr(dest_settlement, 'population', 100),
                        "settlement_type": getattr(dest_settlement, 'settlement_type', "village")
                    }
                    
                    # Get destination's connections for proper world model
                    dest_connections = []
                    if hasattr(dest_settlement, 'connections') and dest_settlement.connections:
                        if isinstance(dest_settlement.connections, str):
                            try:
                                dest_connections = json.loads(dest_settlement.connections)
                            except:
                                pass
                        elif isinstance(dest_settlement.connections, list):
                            dest_connections = dest_settlement.connections
                    
                    # Add to settlements data for MCTS
                    world_data["settlements"][dest_id] = {
                        "id": dest_id,
                        "name": dest_settlement.settlement_name,
                        "biome": getattr(dest_settlement, 'biome', "temperate"),
                        "connections": dest_connections,
                        "settlement_type": getattr(dest_settlement, 'settlement_type', "village")
                    }
            
            # Create TraderState for MCTS
            trader_state = TraderState(
                trader=trader,
                world_info=world_data
            )
            
            # Run MCTS search
            from app.ai.mcts.core import MCTS
            mcts = MCTS(exploration_weight=1.0)
            num_simulations = 100  # Configure as needed
            
            best_action = mcts.search(
                root_state=trader_state,
                get_legal_actions_fn=lambda s: s.get_possible_actions(),
                apply_action_fn=lambda s, a: s.apply_action(a),
                is_terminal_fn=lambda s: s.is_terminal(),
                get_reward_fn=lambda s: s.get_reward(),
                num_simulations=num_simulations
            )
            
            # Check if we got a valid action
            if not best_action or best_action.get("action_type") != "move":
                # If no valid movement action, return an error
                return {"status": "error", "message": "No valid movement action found"}
            
            # Get destination settlement info
            destination_id = best_action["destination_id"]
            destination_name = best_action.get("destination_name", "Unknown")
            
            if not destination_name or destination_name == "Unknown":
                destination_settlement = self.db.query(Settlements).filter(
                    Settlements.settlement_id == destination_id
                ).first()
                if destination_settlement:
                    destination_name = destination_settlement.settlement_name
            
            # Format and return the decision
            return {
                "status": "success",
                "action": "move",
                "next_settlement_id": destination_id,
                "next_settlement_name": destination_name,
                "mcts_stats": {
                    "simulations": num_simulations,
                    "actions_evaluated": len(trader_state.get_possible_actions())
                }
            }
            
        except Exception as e:
            logger.exception(f"Error making MCTS decision: {e}")
            return {"status": "error", "message": f"Error making decision: {str(e)}"}
    
    async def _execute_movement_decision(self, trader: Trader, decision: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a movement decision for a trader.
        
        Args:
            trader (Trader): The trader to move
            decision (Dict[str, Any]): The decision to execute
            
        Returns:
            Dict[str, Any]: Result of the movement execution
        """
        logger.info(f"Executing movement decision for trader {trader.get_property('name')}")
        
        try:
            # Get current and destination settlements
            current_location_id = trader.get_property("current_location_id")
            destination_id = decision["next_settlement_id"]
            
            # Find path between settlements
            path = await self._find_path_between_settlements(current_location_id, destination_id)
            
            if not path:
                logger.warning(f"No path found between settlements, using direct movement")
                # Simply update the trader's location directly
                trader.set_location(destination_id, "current")
                await self.trader_manager.save_trader(trader)
                return {
                    "status": "success",
                    "message": f"Trader moved directly to {decision['next_settlement_name']}"
                }
            
            # Start the journey through areas
            trader_db = self.db.query(Traders).filter(Traders.trader_id == trader.trader_id).first()
            if not trader_db:
                return {"status": "error", "message": "Trader database record not found"}
            
            # Update trader record to indicate they are now traveling
            trader_db.current_settlement_id = None  # Leaving settlement
            trader_db.destination_id = destination_id
            trader_db.destination_settlement_name = decision["next_settlement_name"]
            trader_db.journey_started = datetime.now()
            trader_db.journey_progress = 0
            trader_db.current_area_id = path[0]  # Enter first area
            trader_db.journey_path = json.dumps(path)
            trader_db.path_position = 0
            
            # Commit changes to database
            self.db.commit()
            
            # Update our entity object as well
            trader.set_location(None, "current")
            trader.set_property("current_area_id", path[0])
            trader.set_location(destination_id, "destination")
            await self.trader_manager.save_trader(trader)
            
            # Log the journey start
            first_area = self.db.query(Areas).filter(Areas.area_id == path[0]).first()
            area_name = first_area.area_name if first_area and hasattr(first_area, 'area_name') else "unknown area"
            
            logger.info(f"Trader {trader.get_property('name')} started journey to {decision['next_settlement_name']} via {area_name}")
            
            # Return success
            return {
                "status": "success",
                "action": "journey_started",
                "destination": decision["next_settlement_name"],
                "first_area": area_name,
                "path_length": len(path)
            }
            
        except Exception as e:
            logger.exception(f"Error executing movement decision: {e}")
            return {"status": "error", "message": f"Error executing movement: {str(e)}"}
    
    async def continue_area_travel(self, trader_id: str) -> Dict[str, Any]:
        """
        Continue a trader's journey through areas.
        
        Args:
            trader_id (str): The ID of the trader
            
        Returns:
            Dict[str, Any]: Result of the travel progress
        """
        logger.info(f"Continuing area travel for trader {trader_id}")
        
        try:
            # Get the trader's database record
            trader_db = self.db.query(Traders).filter(Traders.trader_id == trader_id).first()
            if not trader_db:
                return {"status": "error", "message": "Trader not found"}
            
            trader_name = trader_db.npc_name if trader_db.npc_name else f"Trader {trader_id}"
            
            # Check if the trader has any active encounters that need resolution
            encounter_result = await self._check_and_resolve_encounters(trader_id, trader_db.current_area_id)
            if encounter_result["status"] == "encounter_resolved":
                logger.info(f"Trader {trader_name} resolved an encounter: {encounter_result['outcome']}")
            
            # Get journey path
            if not trader_db.journey_path:
                return {"status": "error", "message": "Trader has no journey path"}
            
            try:
                path = json.loads(trader_db.journey_path)
                current_position = trader_db.path_position
            except (ValueError, TypeError) as e:
                logger.error(f"Invalid journey path for trader {trader_id}: {e}")
                return {"status": "error", "message": "Invalid journey path"}
            
            # Update journey progress
            current_position += 1
            
            # Check if reached the end of the path
            if current_position >= len(path):
                # Journey complete, arrive at destination settlement
                trader_db.current_settlement_id = trader_db.destination_id
                trader_db.current_area_id = None
                trader_db.journey_path = None
                trader_db.path_position = 0
                trader_db.journey_progress = 100
                
                destination_settlement = self.db.query(Settlements).filter(
                    Settlements.settlement_id == trader_db.destination_id
                ).first()
                
                destination_name = trader_db.destination_settlement_name
                if destination_settlement and hasattr(destination_settlement, 'settlement_name'):
                    destination_name = destination_settlement.settlement_name
                
                # Commit changes to database
                self.db.commit()
                
                # Also update our entity model
                trader = await self.trader_manager.load_trader(trader_id)
                if trader:
                    trader.set_location(trader_db.destination_id, "current")
                    trader.set_location(None, "destination")
                    trader.set_property("current_area_id", None)
                    await self.trader_manager.save_trader(trader)
                
                logger.info(f"Trader {trader_name} arrived at destination: {destination_name}")
                
                return {
                    "status": "success",
                    "action": "journey_completed",
                    "destination": destination_name
                }
            
            # Move to next area
            next_area_id = path[current_position]
            trader_db.current_area_id = next_area_id
            trader_db.path_position = current_position
            
            # Calculate journey progress percentage
            trader_db.journey_progress = int((current_position / (len(path) - 1)) * 100)
            
            # Commit changes to database
            self.db.commit()
            
            # Get area info for logging
            next_area = self.db.query(Areas).filter(Areas.area_id == next_area_id).first()
            area_name = next_area.area_name if next_area and hasattr(next_area, 'area_name') else "unknown area"
            
            logger.info(f"Trader {trader_name} moved to area: {area_name} ({trader_db.journey_progress}% of journey)")
            
            # Generate potential encounter in new area
            await self._generate_encounter(trader_id, next_area_id)
            
            # Update trader entity model
            trader = await self.trader_manager.load_trader(trader_id)
            if trader:
                trader.set_property("current_area_id", next_area_id)
                await self.trader_manager.save_trader(trader)
            
            return {
                "status": "success",
                "action": "area_moved",
                "area": area_name,
                "progress": trader_db.journey_progress
            }
            
        except Exception as e:
            logger.exception(f"Error continuing area travel: {e}")
            return {"status": "error", "message": f"Error continuing travel: {str(e)}"}
    
    async def _find_path_between_settlements(self, start_id: str, end_id: str) -> List[str]:
        """
        Find a path of areas between two settlements.
        
        Args:
            start_id (str): Starting settlement ID
            end_id (str): Destination settlement ID
            
        Returns:
            List[str]: List of area IDs forming a path, or empty list if no path
        """
        # This is where you would implement pathfinding logic
        # For now, we'll return a placeholder implementation
        # In a full implementation, this would use a graph search algorithm
        
        logger.info(f"Finding path between settlements {start_id} and {end_id}")
        
        try:
            # Get areas connected to start settlement
            start_areas = await self._get_settlement_connected_areas(start_id)
            if not start_areas:
                logger.warning(f"No connected areas found for settlement {start_id}")
                return []
            
            # Get areas connected to destination settlement
            end_areas = await self._get_settlement_connected_areas(end_id)
            if not end_areas:
                logger.warning(f"No connected areas found for settlement {end_id}")
                return []
            
            # Check if settlements share a common area (direct connection)
            common_areas = set(start_areas).intersection(set(end_areas))
            if common_areas:
                common_area = list(common_areas)[0]
                logger.info(f"Settlements share common area {common_area}")
                return [common_area]
            
            # For now, we'll implement a simple breadth-first search
            # In a real implementation, you'd want to use A* with proper distance heuristics
            from collections import deque
            
            queue = deque([(area_id, [area_id]) for area_id in start_areas])
            visited = set(start_areas)
            
            while queue:
                current_area, path = queue.popleft()
                
                # Get connected areas
                neighbors = await self._get_area_connected_areas(current_area)
                
                for neighbor in neighbors:
                    if neighbor in end_areas:
                        # Found a path to destination
                        final_path = path + [neighbor]
                        logger.info(f"Found path through {len(final_path)} areas")
                        return final_path
                    
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append((neighbor, path + [neighbor]))
            
            # If we get here, no path was found - return a simple direct path as fallback
            if start_areas and end_areas:
                logger.info(f"No path found, returning simple path with first areas from each end")
                return [start_areas[0], end_areas[0]]
            
            return []
            
        except Exception as e:
            logger.exception(f"Error finding path between settlements: {e}")
            return []
    
    async def _get_settlement_connected_areas(self, settlement_id: str) -> List[str]:
        """
        Get all areas directly connected to a settlement.
        
        Args:
            settlement_id (str): The settlement ID
            
        Returns:
            List[str]: List of connected area IDs
        """
        try:
            # Query the areas table for connections to this settlement
            # This is a simplified implementation and would need to be adapted to your schema
            areas = self.db.query(Areas).all()
            
            connected_areas = []
            for area in areas:
                # Check if this area has connected_settlements attribute
                if not hasattr(area, 'connected_settlements'):
                    continue
                
                # Parse the connected_settlements JSON if it exists
                if area.connected_settlements:
                    try:
                        settlement_ids = json.loads(area.connected_settlements)
                        if settlement_id in settlement_ids:
                            connected_areas.append(area.area_id)
                    except (json.JSONDecodeError, TypeError):
                        continue
            
            return connected_areas
            
        except Exception as e:
            logger.exception(f"Error getting connected areas for settlement {settlement_id}: {e}")
            return []
    
    async def _get_area_connected_areas(self, area_id: str) -> List[str]:
        """
        Get all areas directly connected to another area.
        
        Args:
            area_id (str): The area ID
            
        Returns:
            List[str]: List of connected area IDs
        """
        try:
            area = self.db.query(Areas).filter(Areas.area_id == area_id).first()
            if not area or not hasattr(area, 'connected_areas'):
                return []
            
            # Parse connected_areas JSON if it exists
            if area.connected_areas:
                try:
                    return json.loads(area.connected_areas)
                except (json.JSONDecodeError, TypeError):
                    logger.warning(f"Invalid connected_areas JSON for area {area_id}")
            
            return []
            
        except Exception as e:
            logger.exception(f"Error getting connected areas for area {area_id}: {e}")
            return []
    
    async def _check_and_resolve_encounters(self, trader_id: str, area_id: str) -> Dict[str, Any]:
        """
        Check if the trader has any active encounters and resolve them.
        May create player tasks for certain encounters.
        
        Args:
            trader_id (str): The trader ID
            area_id (str): The current area ID
            
        Returns:
            Dict[str, Any]: Result of encounter resolution
        """
        from sqlalchemy import select, text
        from app.models.core import AreaEncounters, AreaEncounterTypes, Areas, Traders
        
        logger.info(f"Checking encounters for trader {trader_id} in area {area_id}")
        
        try:
            # Create a manual select statement with only available columns
            select_stmt = select(
                AreaEncounters.encounter_id,
                AreaEncounters.area_id,
                AreaEncounters.encounter_type_id,
                AreaEncounters.is_active,
                AreaEncounters.is_completed
            ).where(
                AreaEncounters.area_id == area_id,
                AreaEncounters.is_active == True,
                AreaEncounters.is_completed == False
            ).limit(1)
            
            result = self.db.execute(select_stmt)
            active_encounter_row = result.first()
            
            if not active_encounter_row:
                return {
                    "status": "no_encounters",
                    "message": "No active encounters found"
                }
            
            # Get encounter details
            encounter_id = active_encounter_row[0]
            encounter_type_id = active_encounter_row[2]
            
            # Get trader and area information for task creation
            trader_db = self.db.query(Traders).filter(Traders.trader_id == trader_id).first()
            area = self.db.query(Areas).filter(Areas.area_id == area_id).first()
            
            if not trader_db or not area:
                logger.warning(f"Failed to retrieve trader or area data for encounter")
                return {
                    "status": "error",
                    "message": "Missing trader or area data"
                }
            
            trader_name = trader_db.npc_name if trader_db.npc_name else f"Trader {trader_id}"
            area_name = area.area_name if hasattr(area, 'area_name') else "unknown area"
            
            # Get encounter type information
            encounter_type = self.db.query(AreaEncounterTypes).filter(
                AreaEncounterTypes.encounter_type_id == encounter_type_id
            ).first()
            
            encounter_name = "unknown encounter"
            if encounter_type and hasattr(encounter_type, 'encounter_name'):
                encounter_name = encounter_type.encounter_name
            
            # Determine if this encounter should create a player task
            # 70% chance for player assistance requirement
            if random.random() < 0.7:
                # Create a player task for this encounter
                try:
                    from app.game_state.services.task_service import TaskService
                    task_service = TaskService(self.db)
                    
                    # Get world ID from trader
                    world_id = trader_db.world_id
                    if not world_id:
                        logger.error(f"Trader {trader_id} has no world_id")
                        # Fall back to auto-resolution
                        return await self._auto_resolve_encounter(trader_id, encounter_id, trader_db)
                    
                    # Generate a meaningful task description based on encounter type
                    task_description = f"Trader {trader_name} needs help with {encounter_name} in {area_name}."
                    task_description += " Find the trader and assist them to continue their journey."
                    
                    # Random rewards based on encounter difficulty
                    if hasattr(encounter_type, 'difficulty'):
                        difficulty = encounter_type.difficulty or 1
                    else:
                        difficulty = 1
                        
                    gold_reward = random.randint(10 * difficulty, 25 * difficulty)
                    reputation_reward = random.randint(1, 3)
                    
                    # Create the task
                    task_result = await task_service.create_task(
                        task_type="TRADER_ASSISTANCE",
                        title=f"Help trader in {area_name}",
                        description=task_description,
                        world_id=str(world_id),
                        location_id=area_id,
                        target_id=trader_id,
                        requirements={},
                        rewards={
                            "gold": gold_reward, 
                            "reputation": reputation_reward,
                            "items": []  # Could add item rewards based on encounter
                        }
                    )
                    
                    if task_result["status"] != "success":
                        logger.error(f"Failed to create task: {task_result.get('message')}")
                        # Fall back to auto-resolution
                        return await self._auto_resolve_encounter(trader_id, encounter_id, trader_db)
                    
                    task_id = task_result["task_id"]
                    
                    # Mark encounter as requiring assistance
                    self.db.execute(
                        text("""
                            UPDATE area_encounters 
                            SET requires_assistance = true,
                                task_id = :task_id
                            WHERE encounter_id = :encounter_id
                        """),
                        {
                            "task_id": task_id,
                            "encounter_id": encounter_id
                        }
                    )
                    
                    # Update trader to be blocked by this task
                    trader_db.can_move = False
                    trader_db.active_task_id = task_id
                    self.db.commit()
                    
                    # Also update the entity model
                    trader_entity = await self.trader_manager.load_trader(trader_id)
                    if trader_entity:
                        trader_entity.set_property("can_move", False)
                        trader_entity.set_property("active_task_id", task_id)
                        await self.trader_manager.save_trader(trader_entity)
                    
                    logger.info(f"Created player task {task_id} for trader {trader_name} in encounter {encounter_id}")
                    
                    return {
                        "status": "player_task_created",
                        "task_id": task_id,
                        "encounter_id": encounter_id,
                        "trader_blocked": True,
                        "message": f"Trader awaiting player assistance in {area_name}"
                    }
                    
                except Exception as e:
                    logger.exception(f"Error creating player task: {e}")
                    # Fall back to auto-resolution
                    return await self._auto_resolve_encounter(trader_id, encounter_id, trader_db)
            
            # If we didn't create a task, auto-resolve the encounter
            return await self._auto_resolve_encounter(trader_id, encounter_id, trader_db)
            
        except Exception as e:
            logger.exception(f"Error checking/resolving encounters: {e}")
            return {
                "status": "error",
                "message": f"Error with encounters: {str(e)}"
            }
    
    async def _auto_resolve_encounter(self, trader_id: str, encounter_id: str, trader_db) -> Dict[str, Any]:
        """
        Automatically resolve an encounter without player assistance.
        
        Args:
            trader_id: The trader ID
            encounter_id: The encounter ID
            trader_db: Trader database record
            
        Returns:
            Dict with encounter resolution result
        """
        from sqlalchemy import text
        
        logger.info(f"Auto-resolving encounter {encounter_id} for trader {trader_id}")
        
        try:
            # Mark the encounter as completed
            self.db.execute(
                text("""
                    UPDATE area_encounters 
                    SET is_completed = true, 
                        is_active = false,
                        resolved_at = CURRENT_TIMESTAMP,
                        resolved_by = :trader_id,
                        requires_assistance = false
                    WHERE encounter_id = :encounter_id
                """),
                {
                    "trader_id": trader_id,
                    "encounter_id": encounter_id
                }
            )
            
            # Simple outcome generation
            effect_types = ["none", "good", "bad", "mixed"]
            effect = random.choice(effect_types)
            
            outcome_name = f"Encounter {effect}"
            
            if effect == "good":
                # Good outcome - gain some gold
                gold_gain = random.randint(10, 50)
                trader_db.gold = trader_db.gold + gold_gain
                outcome_name = f"Found {gold_gain} gold"
            elif effect == "bad":
                # Bad outcome - lose some cart health
                cart_damage = random.randint(5, 15)
                trader_db.cart_health = max(0, trader_db.cart_health - cart_damage)
                outcome_name = f"Cart damaged by {cart_damage}%"
            elif effect == "mixed":
                # Mixed outcome - lose some guards but gain gold
                if trader_db.hired_guards > 0:
                    guards_lost = random.randint(1, min(trader_db.hired_guards, 2))
                    trader_db.hired_guards = max(0, trader_db.hired_guards - guards_lost)
                    gold_gain = random.randint(30, 80)
                    trader_db.gold = trader_db.gold + gold_gain
                    outcome_name = f"Lost {guards_lost} guard(s) but found {gold_gain} gold"
            
            # Commit changes
            self.db.commit()
            
            # Also update entity model
            trader = await self.trader_manager.load_trader(trader_id)
            if trader and effect == "good":
                trader.add_resource("gold", gold_gain)
                await self.trader_manager.save_trader(trader)
            
            return {
                "status": "encounter_resolved",
                "encounter_id": encounter_id,
                "outcome": outcome_name
            }
            
        except Exception as e:
            logger.exception(f"Error auto-resolving encounter: {e}")
            return {
                "status": "error",
                "message": f"Error resolving encounter: {str(e)}"
            }
    
    async def _generate_encounter(self, trader_id: str, area_id: str) -> Dict[str, Any]:
        """
        Generate a potential encounter for a trader in an area.
        
        Args:
            trader_id (str): The trader ID
            area_id (str): The area ID
            
        Returns:
            Dict[str, Any]: Result of encounter generation
        """
        from app.models.core import AreaEncounterTypes
        
        logger.info(f"Generating potential encounter for trader {trader_id} in area {area_id}")
        
        try:
            # Get the area
            area = self.db.query(Areas).filter(Areas.area_id == area_id).first()
            if not area:
                return {"status": "error", "error": f"Area {area_id} not found"}
            
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
            encounter_types = self.db.query(AreaEncounterTypes).limit(10).all()
            if not encounter_types:
                logger.warning("No encounter types found in database")
                return {"status": "success", "result": "no_encounter"}
            
            selected_encounter = random.choice(encounter_types)
            
            # Create the encounter with only the fields that exist in our database
            encounter_id = str(uuid.uuid4())
            
            # Use SQL directly to avoid using fields that don't exist in the database
            from sqlalchemy import text
            self.db.execute(
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
                    "narrative": f"Trader encountered {selected_encounter.encounter_name} in {area.area_name}"
                }
            )
            
            self.db.commit()
            
            logger.info(f"Generated {selected_encounter.encounter_name} encounter for trader {trader_id} in {area.area_name}")
            
            return {
                "status": "success", 
                "result": "encounter_created",
                "encounter_id": encounter_id,
                "encounter_name": selected_encounter.encounter_name
            }
            
        except Exception as e:
            logger.exception(f"Error generating encounter: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _check_life_goal_progress(self, trader: Trader) -> Trader:
        """
        Check and update progress toward life goals based on trader's current state.
        
        Args:
            trader: The trader entity to update
            
        Returns:
            The updated trader entity with goal progress
        """
        goals = trader.get_property("life_goals", [])
        if not goals:
            return trader  # No goals to check
            
        # Increment days active
        days_active = trader.get_property("days_active", 0)
        trader.set_property("days_active", days_active + 1)
        
        for goal in goals:
            if goal["completed"]:
                continue
                
            goal_type = goal["type"]
            params = goal["params"]
            
            # Calculate progress based on goal type
            if goal_type == "WEALTH":
                current_gold = trader.get_property("gold", 0)
                target_gold = params.get("target_gold", 1000)
                goal["progress"] = min(100, int((current_gold / target_gold) * 100))
                if current_gold >= target_gold:
                    goal["completed"] = True
                    logger.info(f"Trader {trader.get_property('name')} completed WEALTH goal!")
                    
            elif goal_type == "VISIT_SETTLEMENTS":
                visited = trader.get_property("visited_settlements", [])
                target_count = params.get("target_count", 10)
                goal["progress"] = min(100, int((len(visited) / target_count) * 100))
                if len(visited) >= target_count:
                    goal["completed"] = True
                    logger.info(f"Trader {trader.get_property('name')} completed VISIT_SETTLEMENTS goal!")
                    
            elif goal_type == "COLLECT_ITEMS":
                inventory = trader.get_property("inventory", {})
                collected_items = sum(1 for item, count in inventory.items() 
                                  if any(t in item for t in params.get("item_types", [])))
                target_count = params.get("target_count", 5)
                goal["progress"] = min(100, int((collected_items / target_count) * 100))
                if collected_items >= target_count:
                    goal["completed"] = True
                    logger.info(f"Trader {trader.get_property('name')} completed COLLECT_ITEMS goal!")
                    
            elif goal_type == "TRADING_VOLUME":
                trade_count = trader.get_property("total_trades", 0)
                target_volume = params.get("target_volume", 100)
                goal["progress"] = min(100, int((trade_count / target_volume) * 100))
                if trade_count >= target_volume:
                    goal["completed"] = True
                    logger.info(f"Trader {trader.get_property('name')} completed TRADING_VOLUME goal!")
                    
            elif goal_type == "SPECIFIC_SETTLEMENT":
                visited = trader.get_property("visited_settlements", [])
                target_settlement = params.get("target_settlement_id")
                if target_settlement in visited:
                    goal["progress"] = 100
                    goal["completed"] = True
                    logger.info(f"Trader {trader.get_property('name')} completed SPECIFIC_SETTLEMENT goal!")
                else:
                    goal["progress"] = 0
                    
            elif goal_type == "OPEN_SHOP":
                current_gold = trader.get_property("gold", 0)
                target_gold = params.get("target_gold", 5000)
                goal["progress"] = min(100, int((current_gold / target_gold) * 100))
                if current_gold >= target_gold:
                    goal["completed"] = True
                    trader.set_property("can_retire", True)
                    logger.info(f"Trader {trader.get_property('name')} completed OPEN_SHOP goal and can now retire!")
                    
            elif goal_type == "RETIRE_WEALTHY":
                current_gold = trader.get_property("gold", 0)
                target_gold = params.get("target_gold", 20000)
                goal["progress"] = min(100, int((current_gold / target_gold) * 100))
                if current_gold >= target_gold:
                    goal["completed"] = True
                    trader.set_property("can_retire", True)
                    logger.info(f"Trader {trader.get_property('name')} completed RETIRE_WEALTHY goal and can now retire!")
                    
            elif goal_type == "FOUND_SETTLEMENT":
                # Check gold and resources
                current_gold = trader.get_property("gold", 0)
                inventory = trader.get_property("inventory", {})
                target_gold = params.get("target_gold", 50000)
                required_resources = params.get("required_resources", {})
                
                gold_progress = min(100, int((current_gold / target_gold) * 100))
                resource_progress = []
                
                for resource, amount in required_resources.items():
                    current = inventory.get(resource, 0)
                    resource_progress.append(min(100, int((current / amount) * 100)))
                
                # Overall progress is average of gold and resources
                if resource_progress:
                    goal["progress"] = int((gold_progress + sum(resource_progress) / len(resource_progress)) / 2)
                else:
                    goal["progress"] = gold_progress
                
                # Check if completed
                gold_ready = current_gold >= target_gold
                resources_ready = all(inventory.get(r, 0) >= a for r, a in required_resources.items())
                
                if gold_ready and resources_ready:
                    goal["completed"] = True
                    trader.set_property("can_retire", True)
                    logger.info(f"Trader {trader.get_property('name')} completed FOUND_SETTLEMENT goal and can now retire!")
                    
            elif goal_type == "FIND_ARTIFACT":
                # Check if trader has the artifact
                inventory = trader.get_property("inventory", {})
                artifact_found = any(item.startswith("artifact_") for item in inventory.keys())
                
                if artifact_found:
                    goal["progress"] = 100
                    goal["completed"] = True
                    trader.set_property("can_retire", True)
                    logger.info(f"Trader {trader.get_property('name')} completed FIND_ARTIFACT goal and can now retire!")
                else:
                    goal["progress"] = 0
        
        # Update trader's life goals
        trader.set_property("life_goals", goals)
        return trader
    
    async def _process_trader_retirement(self, trader: Trader) -> None:
        """
        Process a trader's retirement based on their completed retirement goals.
        
        Args:
            trader: The trader entity that is retiring
        """
        # Find which retirement goal was completed
        retirement_goal = None
        for goal in trader.get_property("life_goals", []):
            if goal.get("is_retirement_goal", False) and goal.get("completed", False):
                retirement_goal = goal
                break
        
        if not retirement_goal:
            logger.warning(f"Trader {trader.get_property('name')} retiring without a completed retirement goal")
            trader.set_property("is_retired", True)
            await self.trader_manager.save_trader(trader)
            return
        
        # Process retirement based on goal type
        goal_type = retirement_goal["type"]
        trader_name = trader.get_property("name") or f"Trader {trader.trader_id}"
        current_location = trader.get_property("current_location_id")
        
        if goal_type == "OPEN_SHOP":
            # Determine shop location - either current location or a preferred one
            shop_location = current_location
            preferred_types = retirement_goal["params"].get("preferred_settlement_types", [])
            
            if not current_location or not self._is_settlement_type(current_location, preferred_types):
                # Try to find a preferred settlement from visited settlements
                for settlement_id in trader.get_property("visited_settlements", []):
                    if self._is_settlement_type(settlement_id, preferred_types):
                        shop_location = settlement_id
                        break
            
            if shop_location:
                # Open shop in the selected location
                shop_name = f"{trader_name}'s Trading Post"
                trader.open_shop(shop_location, shop_name)
                logger.info(f"Trader {trader_name} retired and opened shop '{shop_name}' in settlement {shop_location}")
            else:
                # Just retire without opening shop if no suitable location
                trader.retire()
                logger.info(f"Trader {trader_name} retired but couldn't open a shop")
        
        elif goal_type == "RETIRE_WEALTHY":
            # Settle in current location or home settlement
            settle_location = current_location or trader.get_property("home_settlement_id")
            if settle_location:
                trader.settle_down(settle_location)
                logger.info(f"Trader {trader_name} retired wealthy in settlement {settle_location}")
            else:
                trader.retire()
                logger.info(f"Trader {trader_name} retired wealthy")
        
        elif goal_type == "FOUND_SETTLEMENT":
            # Implementation would involve creating a new settlement
            # For now, just mark as retired
            trader.retire()
            logger.info(f"Trader {trader_name} retired after gathering resources to found a settlement")
            
            # In a real implementation, you would create a new settlement here
            # settlement_id = await self._create_new_settlement(trader)
            # trader.settle_down(settlement_id)
        
        elif goal_type == "FIND_ARTIFACT":
            # Retire in fame with artifact
            trader.retire()
            logger.info(f"Trader {trader_name} retired in fame after finding a legendary artifact")
        
        else:
            # Generic retirement
            trader.retire()
            logger.info(f"Trader {trader_name} retired")
        
        # Save the updated trader
        await self.trader_manager.save_trader(trader)
    
    def _is_settlement_type(self, settlement_id: str, preferred_types: List[str]) -> bool:
        """Check if a settlement is of a preferred type"""
        try:
            settlement = self.db.query(Settlements).filter(Settlements.settlement_id == settlement_id).first()
            if not settlement:
                return False
                
            settlement_type = getattr(settlement, 'settlement_type', None)
            return settlement_type in preferred_types
        except Exception as e:
            logger.error(f"Error checking settlement type: {e}")
            return False

    async def complete_trader_task(self, task_id: str, character_id: str) -> Dict[str, Any]:
        """
        Process trader task completion by a player.
        This unblocks the trader and processes the task rewards.
        
        Args:
            task_id: ID of the task being completed
            character_id: ID of the character completing the task
            
        Returns:
            Dict with the result of task completion
        """
        from app.game_state.services.task_service import TaskService
        
        logger.info(f"Processing trader task completion. Task: {task_id}, Character: {character_id}")
        
        try:
            task_service = TaskService(self.db)
            task = await task_service.get_task(task_id)
            
            if not task:
                return {"status": "error", "message": "Task not found"}
            
            if task.get("status") in ["completed", "failed"]:
                return {"status": "error", "message": "Task already completed or failed"}
            
            # Get the trader
            trader_id = task.get("target_id")
            if not trader_id:
                return {"status": "error", "message": "No trader associated with task"}
            
            trader_db = self.db.query(Traders).filter(Traders.trader_id == trader_id).first()
            if not trader_db:
                return {"status": "error", "message": "Trader not found"}
            
            # Process task completion
            reward_result = await task_service.complete_task(task_id, character_id)
            
            # Unblock the trader
            trader_db.can_move = True
            trader_db.active_task_id = None
            self.db.commit()
            
            # Also update entity model
            trader = await self.trader_manager.load_trader(trader_id)
            if trader:
                trader.set_property("can_move", True)
                trader.set_property("active_task_id", None)
                
                # As a thank you, the trader might give an additional bonus
                # For example, additional gold or discounted prices in the future
                trader.set_relation(character_id, "assisted_by", True)
                await self.trader_manager.save_trader(trader)
            
            # Find and complete the encounter if it still exists
            from sqlalchemy import text
            self.db.execute(
                text("""
                    UPDATE area_encounters 
                    SET is_completed = true, 
                        is_active = false,
                        resolved_at = CURRENT_TIMESTAMP,
                        resolved_by = :character_id,
                        requires_assistance = false
                    WHERE task_id = :task_id
                """),
                {
                    "character_id": character_id,
                    "task_id": task_id
                }
            )
            self.db.commit()
            
            logger.info(f"Player {character_id} completed task {task_id} for trader {trader_id}")
            
            return {
                "status": "success",
                "message": "Task completed and trader unblocked",
                "trader_id": trader_id,
                "task_id": task_id,
                "rewards": reward_result.get("rewards", {})
            }
            
        except Exception as e:
            logger.exception(f"Error completing trader task: {e}")
            return {
                "status": "error", 
                "message": f"Error completing trader task: {str(e)}"
            }
    
    async def process_all_traders(self, world_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process movement for all traders in a world.
        
        Args:
            world_id (Optional[str]): The world ID, or None for all worlds
            
        Returns:
            Dict[str, Any]: Result of processing all traders
        """
        logger.info(f"Processing all traders" + (f" in world {world_id}" if world_id else ""))
        
        try:
            # Query all traders in the world
            query = self.db.query(Traders)
            if world_id:
                query = query.filter(Traders.world_id == world_id)
            
            traders = query.all()
            processed_count = 0
            retired_count = 0
            waiting_for_task_count = 0
            
            # Process each trader
            for trader in traders:
                try:
                    # Process this trader
                    result = await self.process_trader_movement(str(trader.trader_id))
                    
                    if result["status"] == "success":
                        processed_count += 1
                        if result.get("action") == "retired":
                            retired_count += 1
                        elif result.get("action") == "waiting_for_task":
                            waiting_for_task_count += 1
                    else:
                        logger.warning(f"Failed to process trader {trader.trader_id}: {result.get('message')}")
                        
                except Exception as e:
                    logger.exception(f"Error processing trader {trader.trader_id}: {e}")
            
            return {
                "status": "success",
                "total": len(traders),
                "processed": processed_count,
                "retired": retired_count,
                "waiting_for_task": waiting_for_task_count
            }
            
        except Exception as e:
            logger.exception(f"Error processing all traders: {e}")
            return {"status": "error", "message": f"Error processing traders: {str(e)}"}