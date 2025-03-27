from app.ai.mcts.core import MCTS
from app.ai.mcts.states.animal_state import AnimalState
import logging
import random

logger = logging.getLogger(__name__)

class AnimalDecisionMaker:
    def __init__(self, db_session, num_simulations=100):
        self.db = db_session
        self.num_simulations = num_simulations

    async def get_animal_decision(self, animal_id):
        """
        Use MCTS to determine the next best move for an animal.

        Args:
            animal_id: The ID of the animal

        Returns:
            Dictionary containing the decision details and MCTS stats
        """
        # Get the animal manager
        from app.game_state.managers.animal_manager import AnimalManager
        animal_manager = AnimalManager(self.db)

        # Load the animal through the manager
        animal = await animal_manager.load_animal(animal_id)
        if not animal:
            return {"status": "error", "message": "Animal not found"}

        # Create the animal state for MCTS
        animal_state = await self._create_animal_state(animal)
        if not animal_state:
            return {"status": "error", "message": "Failed to create animal state"}

        # Run MCTS search
        best_action = await self._run_mcts_search(animal_state)

        # Format and return the decision
        return self._format_decision(animal, best_action)