from typing import Dict, List, Any, Optional, Tuple
from copy import deepcopy


class StateTemplate:
    """
    Template for creating state objects for game entities.
    States represent the current status of an entity and its available actions.
    """

    def __init__(self, entity: Any, world_info: Optional[Dict[str, Any]] = None):
        """
        Initialize a new state for the given entity.
        
        Args:
            entity: The entity this state represents
            world_info: Optional dictionary containing information about the game world
        """
        self.entity = entity
        self.world_info = world_info or {}
        self._possible_actions = None
    
    def get_possible_actions(self) -> List[Dict[str, Any]]:
        """
        Returns all valid actions for this entity in its current state.
        
        Returns:
            List of action dictionaries, each representing a possible action
        """
        if self._possible_actions is None:
            self._possible_actions = []
            # Add implementation to generate possible actions
            # Example:
            # self._possible_actions.extend(self._get_movement_actions())
            # self._possible_actions.extend(self._get_interaction_actions())
        
        return self._possible_actions
    
    def apply_action(self, action: Dict[str, Any]) -> 'StateTemplate':
        """
        Apply the given action to this state and return a new state.
        
        Args:
            action: The action to apply
            
        Returns:
            A new state object representing the state after the action
        """
        new_state = self.clone()
        
        # Add implementation to apply the action
        # Example:
        # if action['type'] == 'move':
        #     new_state.entity.location = action['destination']
        
        new_state._possible_actions = None  # Reset cached actions
        return new_state
    
    def is_terminal(self) -> bool:
        """
        Determines if this state is terminal (end of decision process).
        
        Returns:
            True if this is a terminal state, False otherwise
        """
        return False
    
    def get_reward(self) -> float:
        """
        Calculate the reward value for this state.
        Used by MCTS to evaluate states.
        
        Returns:
            Numerical reward value
        """
        return 0.0
    
    def clone(self) -> 'StateTemplate':
        """
        Create a deep copy of this state.
        
        Returns:
            A new state object with the same properties
        """
        return deepcopy(self)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert state to dictionary for serialization.
        
        Returns:
            Dictionary representation of state
        """
        return {
            "entity_id": getattr(self.entity, "id", None),
            "entity_type": self.entity.__class__.__name__,
            # Add other important properties to serialize
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], entity_loader, world_info: Optional[Dict[str, Any]] = None) -> 'StateTemplate':
        """
        Create a state from dictionary representation.
        
        Args:
            data: Dictionary data
            entity_loader: Function to load entity by ID
            world_info: Optional world information
            
        Returns:
            New state instance
        """
        entity = entity_loader(data["entity_id"], data["entity_type"])
        state = cls(entity, world_info)
        # Set other important properties from data
        return state