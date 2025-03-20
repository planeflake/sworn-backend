# app/game_state/services/trader_service.py
from sqlalchemy.orm import Session
import logging
import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any

from app.game_state.managers.trader_manager import TraderManager
from app.game_state.decision_makers.trader_decision_maker import TraderDecisionMaker
from app.game_state.entities.trader import Trader
from app.game_state.movement_calculator import MovementCalculator
from models.core import Areas, Traders, Settlements, Worlds

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
        self.trader_manager = TraderManager()
        self.decision_maker = TraderDecisionMaker()
        self.movement_calculator = MovementCalculator(db)
    
    def process_trader_movement(self, trader_id: str) -> Dict[str, Any]:
        """
        Process movement decision and execution for a trader.
        This is the main entry point called by the Celery task.
        
        Args:
            trader_id (str): The ID of the trader to process
            
        Returns:
            Dict[str, Any]: Result of the movement processing
        """
        # Load the trader entity
        trader = self.trader_manager.load_trader(trader_id)
        if not trader:
            logger.error(f"Trader {trader_id} not found")
            return {"status": "error", "message": "Trader not found"}
        
        trader_name = trader.name if trader.name else f"Trader {trader.trader_id}"
        
        # Check if the trader is already traveling through areas
        if self._is_traveling_through_areas(trader):
            logger.info(f"Trader {trader_name} is currently traveling through areas")
            return self.continue_area_travel(trader_id)
        
        # If trader has no current location, place at home settlement
        if not trader.current_location_id:
            logger.info(f"Trader {trader_id} has no current location, placing at home settlement")
            # Logic to place at home settlement would go here
            # For now, we'll just return an error
            return {"status": "error", "message": "Trader has no current location"}
        
        # Make a movement decision
        decision_result = self._make_movement_decision(trader)
        
        if decision_result["status"] != "success":
            logger.error(f"Movement decision failed: {decision_result.get('message')}")
            return decision_result
        
        # Execute the movement decision
        return self._execute_movement_decision(trader, decision_result)
    
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
    
    def _make_movement_decision(self, trader: Trader) -> Dict[str, Any]:
        """
        Use the decision maker to determine the next destination for the trader.
        
        Args:
            trader (Trader): The trader to make a decision for
            
        Returns:
            Dict[str, Any]: Decision result with next destination
        """
        logger.info(f"Making movement decision for trader {trader.name}")
        
        # Load world data
        try:
            # Get the trader's world
            trader_db = self.db.query(Traders).filter(Traders.trader_id == trader.trader_id).first()
            if not trader_db or not trader_db.world_id:
                return {"status": "error", "message": "Trader has no associated world"}
            
            world = self.db.query(Worlds).filter(Worlds.world_id == trader_db.world_id).first()
            if not world:
                return {"status": "error", "message": "Trader's world not found"}
            
            # Get settlement data
            current_settlement = self.db.query(Settlements).filter(
                Settlements.settlement_id == trader.current_location_id
            ).first()
            
            if not current_settlement:
                return {"status": "error", "message": "Current settlement not found"}
            
            # Prepare world data for decision maker
            world_data = {
                "world_id": str(world.world_id),
                "current_game_day": world.current_game_day,
                "name": world.world_name if hasattr(world, 'world_name') else "Unknown",
                "current_season": world.current_season if hasattr(world, 'current_season') else "summer"
            }
            
            # Update decision maker with world data
            self.decision_maker.world_data = world_data
            
            # Use decision maker to make the decision
            action = self.decision_maker.make_decision(trader)
            
            # Return decision result
            if action and action["type"] == "move":
                # Get destination settlement name
                destination_settlement = self.db.query(Settlements).filter(
                    Settlements.settlement_id == action["location_id"]
                ).first()
                
                destination_name = "Unknown"
                if destination_settlement:
                    destination_name = destination_settlement.settlement_name
                
                return {
                    "status": "success",
                    "action": "move",
                    "next_settlement_id": action["location_id"],
                    "next_settlement_name": destination_name
                }
            else:
                return {"status": "error", "message": "No valid movement action returned"}
            
        except Exception as e:
            logger.exception(f"Error making movement decision: {e}")
            return {"status": "error", "message": f"Error making decision: {str(e)}"}
    
    def _execute_movement_decision(self, trader: Trader, decision: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a movement decision for a trader.
        
        Args:
            trader (Trader): The trader to move
            decision (Dict[str, Any]): The decision to execute
            
        Returns:
            Dict[str, Any]: Result of the movement execution
        """
        logger.info(f"Executing movement decision for trader {trader.name}")
        
        try:
            # Get current and destination settlements
            current_settlement_id = trader.current_location_id
            destination_id = decision["next_settlement_id"]
            
            # Find path between settlements
            path = self._find_path_between_settlements(current_settlement_id, destination_id)
            
            if not path:
                logger.warning(f"No path found between settlements, using direct movement")
                # Simply update the trader's location directly
                trader.set_location(destination_id, "current")
                self.trader_manager.save_trader(trader)
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
            trader.set_location(destination_id, "destination")
            self.trader_manager.save_trader(trader)
            
            # Log the journey start
            first_area = self.db.query(Areas).filter(Areas.area_id == path[0]).first()
            area_name = first_area.area_name if first_area and hasattr(first_area, 'area_name') else "unknown area"
            
            logger.info(f"Trader {trader.name} started journey to {decision['next_settlement_name']} via {area_name}")
            
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
    
    def continue_area_travel(self, trader_id: str) -> Dict[str, Any]:
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
            encounter_result = self._check_and_resolve_encounters(trader_id, trader_db.current_area_id)
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
                trader = self.trader_manager.load_trader(trader_id)
                if trader:
                    trader.set_location(trader_db.destination_id, "current")
                    trader.set_location(None, "destination")
                    self.trader_manager.save_trader(trader)
                
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
            self._generate_encounter(trader_id, next_area_id)
            
            return {
                "status": "success",
                "action": "area_moved",
                "area": area_name,
                "progress": trader_db.journey_progress
            }
            
        except Exception as e:
            logger.exception(f"Error continuing area travel: {e}")
            return {"status": "error", "message": f"Error continuing travel: {str(e)}"}
    
    def _find_path_between_settlements(self, start_id: str, end_id: str) -> List[str]:
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
            start_areas = self._get_settlement_connected_areas(start_id)
            if not start_areas:
                logger.warning(f"No connected areas found for settlement {start_id}")
                return []
            
            # Get areas connected to destination settlement
            end_areas = self._get_settlement_connected_areas(end_id)
            if not end_areas:
                logger.warning(f"No connected areas found for settlement {end_id}")
                return []
            
            # Check if settlements share a common area (direct connection)
            common_areas = set(start_areas).intersection(set(end_areas))
            if common_areas:
                common_area = list(common_areas)[0]
                logger.info(f"Settlements share common area {common_area}")
                return [common_area]
            
            # For a more complex implementation, you would implement a full pathfinding algorithm here
            # For now, we'll just return a direct path if possible
            if start_areas and end_areas:
                logger.info(f"Returning simple path with first areas from each end")
                return [start_areas[0], end_areas[0]]
            
            return []
            
        except Exception as e:
            logger.exception(f"Error finding path between settlements: {e}")
            return []
    
    def _get_settlement_connected_areas(self, settlement_id: str) -> List[str]:
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
    
    def _check_and_resolve_encounters(self, trader_id: str, area_id: str) -> Dict[str, Any]:
        """
        Check if the trader has any active encounters and resolve them.
        
        Args:
            trader_id (str): The trader ID
            area_id (str): The current area ID
            
        Returns:
            Dict[str, Any]: Result of encounter resolution
        """
        # This would be where you check for and resolve encounters
        # For now, we'll return a placeholder implementation
        
        logger.info(f"Checking encounters for trader {trader_id} in area {area_id}")
        
        # Normally, you would query for active encounters here
        # For now, we'll just return no encounters
        
        return {
            "status": "no_encounters",
            "message": "No active encounters found"
        }
    
    def _generate_encounter(self, trader_id: str, area_id: str) -> Dict[str, Any]:
        """
        Generate a potential encounter for a trader in an area.
        
        Args:
            trader_id (str): The trader ID
            area_id (str): The area ID
            
        Returns:
            Dict[str, Any]: Result of encounter generation
        """
        # This would be where you generate new encounters
        # For now, we'll return a placeholder implementation
        
        logger.info(f"Generating potential encounter for trader {trader_id} in area {area_id}")
        
        # In a real implementation, you would:
        # 1. Get the area's danger level
        # 2. Roll for an encounter based on danger level
        # 3. If an encounter happens, generate it and save to database
        
        # For now, just return that no encounter was generated
        return {
            "status": "success",
            "result": "no_encounter"
        }
    
    def process_all_traders(self, world_id: Optional[str] = None) -> Dict[str, Any]:
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
            
            # Process each trader
            for trader in traders:
                try:
                    # Process this trader
                    result = self.process_trader_movement(str(trader.trader_id))
                    
                    if result["status"] == "success":
                        processed_count += 1
                    else:
                        logger.warning(f"Failed to process trader {trader.trader_id}: {result.get('message')}")
                        
                except Exception as e:
                    logger.exception(f"Error processing trader {trader.trader_id}: {e}")
            
            return {
                "status": "success",
                "total": len(traders),
                "processed": processed_count
            }
            
        except Exception as e:
            logger.exception(f"Error processing all traders: {e}")
            return {"status": "error", "message": f"Error processing traders: {str(e)}"}