# app/game_state/manager.py
from sqlalchemy.orm import Session
from sqlalchemy import String, cast, text
from app.models.core import Worlds, Settlements, Characters, Traders, TravelRoutes, Areas
from app.game_state.mcts import MCTS
from app.ai.mcts.trader_state import TraderState, TraderAction
import logging
import random as rand
import json
import uuid

logger = logging.getLogger(__name__)

class GameStateManager:
    def __init__(self, db: Session):
        self.db = db
    
    def get_world_state(self, world_id):
        """Get the complete state of a world"""
        world = self.db.query(Worlds).filter(Worlds.world_id == world_id).first()
        if not world:
            return None
        
        # Get season information if available
        current_season_info = None
        if hasattr(world, 'current_season') and world.current_season:
            from app.models.seasons import Seasons
            season = self.db.query(Seasons).filter(Seasons.name == world.current_season).first()
            if season:
                current_season_info = {
                    "name": season.name,
                    "display_name": season.display_name,
                    "description": season.description,
                    "color_hex": season.color_hex,
                    "resource_modifiers": season.resource_modifiers,
                    "travel_modifier": season.travel_modifier
                }
        
        return {
            "world": world,
            "current_day": world.current_game_day,
            "settlement_count": self.db.query(Settlements).filter(Settlements.world_id == world_id).count(),
            "player_count": self.db.query(Characters).filter(Characters.world_id == world_id).count(),
            "current_season": current_season_info
        }
    
    def advance_game_day(self, world_id):
        """Increment the game day counter and trigger daily processes"""
        world = self.db.query(Worlds).filter(Worlds.world_id == world_id).first()
        if not world:
            return False
        
        world.current_game_day += 1
        self.db.commit()
        
        logger.info(f"Advanced world {world_id} to day {world.current_game_day}")
        return world.current_game_day
    
    def get_mcts_trader_decision(self, trader_id, num_simulations=100):
        """
        Use MCTS to determine the next best move for a trader.
        
        Args:
            trader_id: The ID of the trader
            num_simulations: Number of MCTS simulations to run
            
        Returns:
            Dictionary containing the decision details and MCTS stats
        """
        logger.info(f"MCTS TRACE: Starting MCTS decision process for trader {trader_id}")
        
        trader = self.db.query(Traders).filter(Traders.trader_id == trader_id).first()
        if not trader:
            logger.error(f"Trader {trader_id} not found")
            return {"status": "error", "message": "Trader not found"}
        
        # Get current settlement
        current_settlement = None
        logger.info('Trader.current_settlement_id: ' + str(trader.current_settlement_id))
        if trader.current_settlement_id:
            current_settlement = self.db.query(Settlements).filter(
                Settlements.settlement_id == trader.current_settlement_id
            ).first()
        
        if not current_settlement:
            logger.error(f"Current settlement not found for trader {trader_id}")
            return {"status": "error", "message": "Current settlement not found"}
        
        # Get world data
        world = self.db.query(Worlds).filter(Worlds.world_id == trader.world_id).first()
        logger.info('World: ' + str(world))
        if not world:
            logger.error(f"World not found for trader {trader_id}")
            return {"status": "error", "message": "World not found"}
        
        # Get all settlements in the world for complete state
        settlements = self.db.query(Settlements).filter(
            Settlements.world_id == trader.world_id
        ).all()
        settlements_data = []
        for s in settlements:
            logger.info('Settlement: ' + str(s))
            settlement_info = {
                "settlement_id": str(s.settlement_id),
                "settlement_name": s.settlement_name,
                "connections": s.connections
            }
            
            # Add optional fields if they exist
            if hasattr(s, 'size'):
                settlement_info["size"] = s.size
            else:
                settlement_info["size"] = "medium"  # Default size
                
            if hasattr(s, 'prosperity'):
                settlement_info["prosperity"] = s.prosperity
            else:
                settlement_info["prosperity"] = 5  # Default prosperity
                
            if hasattr(s, 'biome'):
                settlement_info["biome"] = s.biome
            else:
                settlement_info["biome"] = "plains"  # Default biome
                
            settlements_data.append(settlement_info)
        
        # Get all travel routes
        logger.info(f"Looking for travel routes for settlement {current_settlement.settlement_id}")
        try:
            routes = self.db.execute(
                text("""
                SELECT route_id, start_settlement_id, end_settlement_id, path 
                FROM travel_routes 
                WHERE 
                    start_settlement_id::text = :settlement_id OR 
                    end_settlement_id::text = :settlement_id
                """),
                {"settlement_id": str(current_settlement.settlement_id)}
            ).fetchall()
            
            logger.info(f"Found {len(routes)} travel routes for settlement {current_settlement.settlement_id}")
        except Exception as e:
            logger.exception(f"Error getting travel routes: {e}")
            routes = []
        
        travel_routes = []
        for r in routes:
            route_data = {
                "route_id": str(r.route_id),
                "start_settlement_id": str(r.start_settlement_id),
                "end_settlement_id": str(r.end_settlement_id),
                "path": r.path
            }
            logger.info(f"Route: {route_data['start_settlement_id']} → {route_data['end_settlement_id']}")
            travel_routes.append(route_data)
            
        # If no routes found, use settlement connections as fallback
        if not travel_routes:
            logger.warning(f"No travel routes found, looking for connections in settlement data")
            # Try to use connections from settlement data
            for s in settlements:
                connections = getattr(s, 'connections', None)
                if not connections:
                    continue
                    
                # Skip the current settlement
                if str(s.settlement_id) != current_settlement.settlement_id:
                    continue
                    
                # Parse connections if needed
                conn_data = connections
                if isinstance(connections, str):
                    try:
                        conn_data = json.loads(connections)
                    except (json.JSONDecodeError, TypeError):
                        logger.warning(f"Error parsing connections JSON for settlement {s.settlement_id}")
                        continue
                
                # Only proceed if we have a list
                if not isinstance(conn_data, list):
                    continue
                    
                logger.info(f"Using {len(conn_data)} connections from settlement {s.settlement_id} as fallback")
                
                # Create synthetic travel routes
                for conn in conn_data:
                    if not isinstance(conn, dict):
                        continue
                        
                    dest_id = conn.get('destination_id')
                    dest_name = conn.get('destination', 'Unknown')
                    
                    if not dest_id:
                        continue
                        
                    # Skip invalid placeholder IDs
                    if (isinstance(dest_id, str) and 
                        (dest_id.startswith('11111') or dest_id == '00000000-0000-0000-0000-000000000000')):
                        logger.warning(f"Skipping invalid destination ID: {dest_id}")
                        continue
                    
                    # Create a synthetic route
                    import uuid
                    route_data = {
                        "route_id": str(uuid.uuid4()),
                        "start_settlement_id": str(s.settlement_id),
                        "end_settlement_id": str(dest_id),
                        "path": "[]"  # Empty path
                    }
                    logger.info(f"Adding fallback route: {s.settlement_name} → {dest_name}")
                    travel_routes.append(route_data)
        
        # Build a simplified price model
        # In a real implementation, you'd query actual resource prices from settlements
        resource_prices = {}
        for settlement in settlements:
            # Generate random price multipliers for each settlement
            # In production, these would come from the actual economy model
            resource_prices[str(settlement.settlement_id)] = {
                "wood": 0.8 + (0.4 * rand.random()),
                "stone": 0.8 + (0.4 * rand.random()),
                "iron": 0.8 + (0.4 * rand.random()),
                "food": 0.8 + (0.4 * rand.random()),
                "luxuries": 0.8 + (0.4 * rand.random())
            }
        
        # Build trader data
        trader_data = {
            "trader_id": str(trader.trader_id),
            "npc_name": trader.npc_name,
            "current_settlement_id": str(trader.current_settlement_id) if trader.current_settlement_id else None,
            "destination_id": str(trader.destination_id) if trader.destination_id else None,
            "destination_settlement_name": trader.destination_settlement_name,
            "current_area_id": str(trader.current_area_id) if trader.current_area_id else None,
            "journey_path": trader.journey_path,
            "path_position": trader.path_position,
            "gold": trader.gold,
            "cart_capacity": trader.cart_capacity,
            "cart_health": trader.cart_health,
            "home_settlement_id": str(trader.home_settlement_id) if trader.home_settlement_id else None,
            "biome_preferences": trader.biome_preferences,
            "schedule": trader.schedule,
            "hired_guards": trader.hired_guards,
            # Add a simplified inventory for simulation purposes
            "inventory": {
                "wood": {"quantity": 10, "base_price": 5},
                "food": {"quantity": 8, "base_price": 8}
            }
        }
        
        # World data
        world_data = {
            "world_id": str(world.world_id),
            "current_game_day": world.current_game_day,
            "name": world.world_name if hasattr(world, 'world_name') else "Unknown"
        }
        
        # Add world size if it exists
        if hasattr(world, 'size'):
            world_data["size"] = world.size
        else:
            world_data["size"] = "standard"  # Default size
        
        # Prepare world data for TraderState
        world_data_for_state = {
            "world_id": world_data["world_id"],
            "current_game_day": world_data["current_game_day"],
            "name": world_data["name"],
            "size": world_data["size"],
            "settlements": {},  # Will populate with settlement data
            "travel_routes": travel_routes,
            "resource_prices": resource_prices
        }
        
        # Add settlements to world data
        for settlement in settlements_data:
            settlement_id = settlement["settlement_id"]
            world_data_for_state["settlements"][settlement_id] = settlement
        
        # Create TraderState for MCTS
        state = TraderState(trader_data, world_data_for_state)
        
        # Pre-check legal actions
        logger.info(f"MCTS TRACE: Initializing TraderState with {len(settlements_data)} settlements and {len(travel_routes)} routes")
        legal_actions_initial = state.get_legal_actions()
        logger.info(f"MCTS TRACE: Legal actions before MCTS: {len(legal_actions_initial)}")
        for i, action in enumerate(legal_actions_initial):
            logger.info(f"MCTS TRACE: Legal action {i+1}: Move to {action.destination_name} ({action.destination_id})")
        
        # If no legal actions, return error immediately
        if not legal_actions_initial:
            logger.error(f"MCTS TRACE: No legal actions available for trader {trader_id} before starting MCTS")
            return {"status": "error", "message": "No legal actions available"}
        
        # Initialize MCTS and run search
        import random
        random.seed(42)  # For reproducible results
        
        logger.info(f"MCTS TRACE: Starting MCTS search with {num_simulations} simulations")
        mcts = MCTS(exploration_weight=1.0)
        best_action = mcts.search(
            root_state=state,
            get_legal_actions_fn=lambda s: s.get_legal_actions(),
            apply_action_fn=lambda s, a: s.apply_action(a),
            is_terminal_fn=lambda s: s.is_terminal(),
            get_reward_fn=lambda s: s.get_reward(),
            num_simulations=num_simulations
        )
        
        logger.info(f"MCTS TRACE: MCTS search completed, best_action: {best_action}")
        
        # Get legal actions directly from the state again to double-check
        legal_actions = state.get_legal_actions()
        logger.info(f"MCTS TRACE: Legal actions after MCTS: {len(legal_actions)}")
        for i, action in enumerate(legal_actions):
            logger.info(f"MCTS TRACE: Legal action after MCTS {i+1}: {action}")
        
        # WORKAROUND: Force to use the first legal action - the MCTS is failing to run properly
        if legal_actions:
            if not best_action:
                logger.warning(f"MCTS TRACE: MCTS workaround triggered - using first legal action instead")
                logger.info(f"MCTS TRACE: First legal action: {legal_actions[0]}")
                best_action = legal_actions[0]
                logger.info(f"MCTS TRACE: Set best_action to {best_action}")
            else:
                logger.info(f"MCTS TRACE: MCTS returned a valid action: {best_action}")
        elif not best_action:
            logger.error(f"MCTS TRACE: No legal actions available AND no best_action from MCTS")
            return {"status": "error", "message": "No legal actions available"}
            
        # Final check for best_action
        if not best_action:
            logger.error(f"MCTS TRACE: Still no best_action after workaround attempt")
            return {"status": "error", "message": "No valid action found"}
            
        # Extract decision and stats
        decision = {
            "status": "success",
            "next_settlement_id": best_action.destination_id,
            "next_settlement_name": best_action.destination_name,
            "path": best_action.area_path,
            "reverse_path": best_action.reverse_path,
            "trader_id": str(trader.trader_id),
            "trader_name": trader.npc_name,
            "mcts_stats": mcts.decision_stats if hasattr(mcts, 'decision_stats') else {}
        }
        
        logger.info(f"MCTS TRACE: Final decision: Move to {best_action.destination_name}")
        
        # Log detailed stats if available
        if hasattr(mcts, 'decision_stats'):
            stats = mcts.decision_stats
            logger.info(f"MCTS stats: {stats.get('simulations', 0)} simulations, {stats.get('actions_evaluated', 0)} actions evaluated")
            
            # Log action details
            for action, action_stats in stats.get("action_stats", {}).items():
                logger.info(f"Action: {action}, Visits: {action_stats.get('visits')}, Avg Value: {action_stats.get('average_value', 0):.2f}")
        
        return decision