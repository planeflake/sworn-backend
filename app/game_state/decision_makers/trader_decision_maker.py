# app/game_state/decision_makers/trader_decision_maker.py
from app.ai.mcts.core import MCTS
from app.ai.mcts.states.trader_state import TraderState, TraderAction
import logging
import json
import random
from app.models import core as models

logger = logging.getLogger(__name__)

class TraderDecisionMaker:
    def __init__(self, db_session, num_simulations=100):
        self.db = db_session
        self.num_simulations = num_simulations
        
    async def get_trader_decision(self, trader_id):
        """
        Use MCTS to determine the next best move for a trader.
        
        Args:
            trader_id: The ID of the trader
            
        Returns:
            Dictionary containing the decision details and MCTS stats
        """
        # Get the trader manager
        from app.game_state.managers.trader_manager import TraderManager
        trader_manager = TraderManager(self.db)
        
        # Load the trader through the manager
        trader = await trader_manager.load_trader(trader_id)
        if not trader:
            return {"status": "error", "message": "Trader not found"}
            
        # Create the trader state for MCTS
        trader_state = await self._create_trader_state(trader)
        if not trader_state:
            return {"status": "error", "message": "Failed to create trader state"}
            
        # Run MCTS search
        best_action = await self._run_mcts_search(trader_state)
        
        # Format and return the decision
        return self._format_decision(trader, best_action)
        
    async def _create_trader_state(self, trader):
        """Create a trader state object for MCTS."""
        try:
            # Get the trader's world data
            trader_db = self.db.query(models.Traders).filter(models.Traders.trader_id == trader.trader_id).first()
            if not trader_db or not trader_db.world_id:
                logger.error(f"Trader {trader.trader_id} has no associated world")
                return None
            
            # Get current settlement
            current_location_id = trader.get_property("current_location_id")
            if not current_location_id:
                logger.error(f"Trader {trader.trader_id} has no current location")
                return None
                
            # Create world data
            from app.models.core import Settlements
            
            settlement_db = self.db.query(Settlements).filter(
                Settlements.settlement_id == current_location_id
            ).first()
            
            if not settlement_db:
                logger.error(f"Could not find settlement {current_location_id}")
                return None
                
            # Build minimal world data for state creation
            world_data = {
                "world_id": str(trader_db.world_id),
                "settlements": {
                    current_location_id: {
                        "id": current_location_id,
                        "name": settlement_db.settlement_name,
                        "biome": getattr(settlement_db, 'biome', "temperate"),
                        "connections": []
                    }
                },
                "markets": {
                    current_location_id: {
                        "buying": {},
                        "selling": {}
                    }
                }
            }
            
            # Add connections
            if settlement_db.connections:
                try:
                    connections = settlement_db.connections
                    if isinstance(connections, str):
                        connections = json.loads(connections)
                        
                    world_data["settlements"][current_location_id]["connections"] = connections
                    
                    # Add connected settlements to world data
                    for connection in connections:
                        dest_id = connection.get('destination_id')
                        if not dest_id or dest_id.startswith('11111') or dest_id == '00000000-0000-0000-0000-000000000000':
                            continue
                            
                        dest_settlement = self.db.query(Settlements).filter(
                            Settlements.settlement_id == dest_id
                        ).first()
                        
                        if dest_settlement:
                            world_data["settlements"][dest_id] = {
                                "id": dest_id,
                                "name": dest_settlement.settlement_name,
                                "biome": getattr(dest_settlement, 'biome', "temperate"),
                                "connections": []
                            }
                            
                            # Add basic market data
                            world_data["markets"][dest_id] = {
                                "buying": {},
                                "selling": {}
                            }
                except Exception as e:
                    logger.error(f"Error processing settlement connections: {e}")
            
            # Create the state
            return TraderState(trader=trader, world_info=world_data)
            
        except Exception as e:
            logger.exception(f"Error creating trader state: {e}")
            return None
        
    async def _run_mcts_search(self, state):
        """Run MCTS search to find the best action."""
        try:
            mcts = MCTS(exploration_weight=1.0)
            best_action = mcts.search(
                root_state=state,
                get_legal_actions_fn=lambda s: s.get_legal_actions(),
                apply_action_fn=lambda s, a: s.apply_action(a),
                is_terminal_fn=lambda s: s.is_terminal(),
                get_reward_fn=lambda s: s.get_reward(),
                num_simulations=self.num_simulations
            )
            
            return best_action
            
        except Exception as e:
            logger.exception(f"Error running MCTS search: {e}")
            return None
        
    def _format_decision(self, trader, best_action):
        """Format the decision result."""
        if not best_action:
            return {"status": "error", "message": "No valid action found"}
            
        # The best action is either a TraderAction object or a dictionary
        if isinstance(best_action, TraderAction):
            # Use the TraderAction fields
            return {
                "status": "success",
                "action_type": best_action.action_type,
                "next_settlement_id": best_action.destination_id,
                "next_settlement_name": best_action.destination_name,
                "path": best_action.area_path,
                "trader_id": str(trader.trader_id),
                "trader_name": trader.get_property("name", f"Trader {trader.trader_id}"),
                "mcts_stats": {
                    "simulations": self.num_simulations
                }
            }
        elif isinstance(best_action, dict):
            # Use the dictionary format from our action generation
            return {
                "status": "success",
                "action_type": best_action.get("action_type", "unknown"),
                "next_settlement_id": best_action.get("destination_id"),
                "next_settlement_name": best_action.get("destination_name", "Unknown"),
                "path": best_action.get("area_path", []),
                "trader_id": str(trader.trader_id),
                "trader_name": trader.get_property("name", f"Trader {trader.trader_id}"),
                "mcts_stats": {
                    "simulations": self.num_simulations
                }
            }
        else:
            # Unknown format
            return {"status": "error", "message": "Invalid action format"}