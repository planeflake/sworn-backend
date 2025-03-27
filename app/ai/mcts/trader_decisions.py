"""
Decision maker for trader entities using MCTS.

This module provides a specialized MCTS-based decision maker for trader entities,
allowing them to make intelligent decisions about movement, trading, and other actions.
"""

from typing import Dict, Any, Optional, List, Tuple
import logging
import json

from app.ai.mcts.core import MCTS
from app.ai.mcts.trader_state import TraderState, TraderAction

logger = logging.getLogger(__name__)

class TraderDecisionMaker:
    """
    Makes decisions for trader entities using Monte Carlo Tree Search.
    
    This class orchestrates the process of:
    1. Creating a state representation from trader data
    2. Running MCTS to find optimal actions
    3. Formatting decisions for use in the game
    """
    
    def __init__(self, exploration_weight: float = 1.0, num_simulations: int = 100):
        """
        Initialize the decision maker.
        
        Args:
            exploration_weight: Controls exploration vs exploitation in MCTS
            num_simulations: Number of MCTS simulations to run
        """
        self.exploration_weight = exploration_weight
        self.num_simulations = num_simulations
        self.world_data = {}  # Will be updated with each decision call
        
    def make_decision(self, trader, settlement_data=None) -> Dict[str, Any]:
        """
        Make a decision for a trader entity.
        
        Args:
            trader: Trader entity object
            settlement_data: Optional settlement data to use
            
        Returns:
            Dictionary with decision details and metadata
        """
        # Create trader data dictionary from entity
        trader_data = self._prepare_trader_data(trader)
        
        # Prepare world data
        world_data = self._prepare_world_data(trader.world_id, settlement_data)
        
        # Create initial state
        initial_state = TraderState(trader_data, world_data)
        
        # Run MCTS
        mcts = MCTS(exploration_weight=self.exploration_weight)
        best_action = mcts.search(
            root_state=initial_state,
            get_legal_actions_fn=lambda s: s.get_legal_actions(),
            apply_action_fn=lambda s, a: s.apply_action(a),
            is_terminal_fn=lambda s: s.is_terminal(),
            get_reward_fn=lambda s: s.get_reward(),
            num_simulations=self.num_simulations
        )
        
        # Format and return the decision
        return self._format_decision(trader, best_action, mcts.decision_stats)
    
    def _prepare_trader_data(self, trader) -> Dict[str, Any]:
        """
        Extract relevant data from trader entity.
        
        Args:
            trader: Trader entity
            
        Returns:
            Dictionary of trader properties
        """
        # Get trader properties from the entity
        trader_data = {
            "trader_id": trader.trader_id,
            "name": trader.name,
            "current_location_id": trader.get_property("current_location_id"),
            "destination_id": trader.get_property("destination_id"),
            "home_settlement_id": trader.get_property("home_settlement_id"),
            "resources": trader.get_property("resources", {}),
            "inventory": trader.get_property("inventory", {}),
            "preferred_settlements": trader.get_property("preferred_settlements", []),
            "preferred_biomes": trader.get_property("preferred_biomes", []),
            "visited_settlements": trader.get_property("visited_settlements", []),
            "faction_id": trader.get_property("faction_id"),
            "trade_priorities": trader.get_property("trade_priorities", {})
        }
        
        return trader_data
    
    def _prepare_world_data(self, world_id, settlement_data) -> Dict[str, Any]:
        """
        Prepare world data for decision making.
        
        Args:
            world_id: ID of the current world
            settlement_data: Optional settlement data
            
        Returns:
            Dictionary with world data
        """
        # Start with current world data
        world_data = self.world_data.copy()
        
        # Add world ID
        world_data["world_id"] = world_id
        
        # Add settlement data if provided
        if settlement_data:
            if "settlements" not in world_data:
                world_data["settlements"] = {}
                
            for settlement in settlement_data:
                settlement_id = settlement.get("settlement_id")
                if settlement_id:
                    world_data["settlements"][settlement_id] = settlement
        
        return world_data
    
    def _format_decision(self, trader, action: TraderAction, 
                       stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format the decision result.
        
        Args:
            trader: Trader entity
            action: The selected action
            stats: MCTS statistics
            
        Returns:
            Formatted decision result
        """
        if not action:
            return {
                "status": "error",
                "message": "No valid action found",
                "action_type": "none"
            }
        
        # Basic result with MCTS stats
        result = {
            "status": "success",
            "action_type": action.action_type,
            "trader_id": trader.trader_id,
            "trader_name": trader.name,
            "mcts_stats": {
                "simulations": self.num_simulations,
                "exploration_weight": self.exploration_weight,
                "total_visits": stats.get("visits", 0),
                "children_evaluated": stats.get("children", 0)
            }
        }
        
        # Add action-specific details
        if action.action_type == "move":
            result.update({
                "next_settlement_id": action.destination_id,
                "next_settlement_name": action.destination_name,
                "path": action.area_path,
            })
        elif action.action_type == "buy":
            result.update({
                "item_id": action.item_id,
                "price": action.price
            })
        elif action.action_type == "sell":
            result.update({
                "item_id": action.item_id,
                "price": action.price
            })
        
        return result
    
    def update_world_data(self, key: str, data: Any) -> None:
        """
        Update a specific part of the world data.
        
        Args:
            key: Data key (settlements, markets, items, etc.)
            data: The data to store
        """
        self.world_data[key] = data