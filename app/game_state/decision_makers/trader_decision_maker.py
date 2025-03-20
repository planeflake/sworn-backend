# app/ai/decision/trader_decision.py
from app.ai.mcts.core import MCTS
from app.game_state.states.trader_state import TraderState
import logging
import random

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
        # This method would contain all the state creation logic from your current get_trader_decision
        # ...
        
    async def _run_mcts_search(self, state):
        """Run MCTS search to find the best action."""
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
        
    def _format_decision(self, trader, best_action):
        """Format the decision result."""
        if not best_action:
            return {"status": "error", "message": "No valid action found"}
            
        return {
            "status": "success",
            "next_settlement_id": best_action.destination_id,
            "next_settlement_name": best_action.destination_name,
            "path": best_action.area_path,
            "reverse_path": best_action.reverse_path,
            "trader_id": str(trader.trader_id),
            "trader_name": trader.name,
            "mcts_stats": {}  # Add stats if available
        }