from app.game_state.mcts import MCTS
from typing import Dict, List, Any, Optional, Tuple
from copy import deepcopy
import logging as logger

class VillagerState:
    """
    State representation for villager AI decision-making using MCTS.
    This class represents the state of a villager for use in Monte Carlo Tree Search.
    """
    
    def __init__(self, villager, world_info=None, location_graph=None):
        """
        Initialize a villager state for decision-making.
        
        Args:
            villager: The Villager object this state represents
            world_info: Information about the game world (optional)
            location_graph: Graph of location connections (optional)
        """
        self.villager = villager
        self.world_info = world_info or {}
        self.location_graph = location_graph or {}
        
        # Cache of possible actions for this state
        self._possible_actions = None
        
    def get_possible_actions(self):
        """
        Get all possible actions the villager can take in the current state.
        
        Returns:
            list: List of possible action objects
        """
        if self._possible_actions is not None:
            return self._possible_actions
            
        actions = []
        
        # Add movement actions
        movement_actions = self._get_movement_actions()
        actions.extend(movement_actions)
        
        # Add task actions
        task_actions = self._get_task_actions()
        actions.extend(task_actions)
        
        # Add social interaction actions
        social_actions = self._get_social_actions()
        actions.extend(social_actions)
        
        # Add rest action (stay in place)
        actions.append({"type": "rest", "location_id": self.villager.location_id})
        
        self._possible_actions = actions
        return actions
    
    def _get_movement_actions(self):
        """
        Get possible movement actions based on the villager's current location.
        
        Returns:
            list: List of possible movement actions
        """
        actions = []
        
        # If we have a location graph, use it to find connected locations
        current_location = self.villager.location_id
        if current_location in self.location_graph:
            connected_locations = self.location_graph[current_location]
            
            for location_id in connected_locations:
                # Skip unacceptable locations based on biome
                if 'locations' in self.world_info and location_id in self.world_info['locations']:
                    biome = self.world_info['locations'][location_id].get('biome')
                    if biome in self.villager.unacceptable_biomes:
                        continue
                    
                # Create movement action
                action = {
                    "type": "move",
                    "location_id": location_id,
                    "score": self._score_location(location_id)
                }
                actions.append(action)
        
        return actions
    
    def _score_location(self, location_id):
        """
        Score a location based on villager preferences.
        
        Args:
            location_id: The ID of the location to score
            
        Returns:
            float: A score for this location (higher is better)
        """
        score = 1.0  # Base score
        
        # Get location biome if available in world_info
        if 'locations' in self.world_info and location_id in self.world_info['locations']:
            biome = self.world_info['locations'][location_id].get('biome')
            
            # Preferred biome gets a bonus
            if biome == self.villager.preferred_biome:
                score += 2.0
        
        # Previously visited locations are slightly less interesting
        if 'visited_locations' in self.villager.properties and location_id in self.villager.properties['visited_locations']:
            score -= 0.5
        
        return score
    
    def _get_task_actions(self):
        """
        Get possible task-related actions.
        
        Returns:
            list: List of possible task actions
        """
        actions = []
        
        # If the villager has tasks, add actions to work on them
        for task in self.villager.tasks:
            action = {
                "type": "work_on_task",
                "task_id": task,
                "location_id": self.villager.location_id
            }
            actions.append(action)
        
        return actions
    
    def _get_social_actions(self):
        """
        Get possible social interaction actions.
        
        Returns:
            list: List of possible social actions
        """
        actions = []
        
        # If there are other villagers at the current location, add social actions
        if 'villagers_by_location' in self.world_info:
            current_location = self.villager.location_id
            if current_location in self.world_info['villagers_by_location']:
                for other_villager_id in self.world_info['villagers_by_location'][current_location]:
                    # Skip self
                    if other_villager_id == self.villager.villager_id:
                        continue
                    
                    # Add social action
                    action = {
                        "type": "interact",
                        "target_id": other_villager_id,
                        "location_id": current_location
                    }
                    actions.append(action)
        
        return actions
    
    def apply_action(self, action):
        """
        Apply an action to this state and return the new state.
        
        Args:
            action: The action to apply
            
        Returns:
            VillagerState: A new state resulting from the action
        """
        # Create a copy of this state
        new_state = self.clone()
        
        # Apply the action based on its type
        if action["type"] == "move":
            new_state.villager.set_location(action["location_id"])
            
            # Add to visited locations
            if 'visited_locations' not in new_state.villager.properties:
                new_state.villager.properties['visited_locations'] = []
            if action["location_id"] not in new_state.villager.properties['visited_locations']:
                new_state.villager.properties['visited_locations'].append(action["location_id"])
                
        elif action["type"] == "work_on_task":
            # Simulate progress on task (in a real implementation, this would be more complex)
            # For now, just mark it as complete with some probability
            if 'task_progress' not in new_state.villager.properties:
                new_state.villager.properties['task_progress'] = {}
                
            task_id = action["task_id"]
            current_progress = new_state.villager.properties['task_progress'].get(task_id, 0)
            new_progress = min(current_progress + 0.2, 1.0)  # Progress by 20%
            new_state.villager.properties['task_progress'][task_id] = new_progress
            
            # If task is complete, remove it
            if new_progress >= 1.0 and task_id in new_state.villager.tasks:
                new_state.villager.complete_task(task_id)
                
        elif action["type"] == "interact":
            # Simulate social interaction (in a real implementation, this would affect relationships)
            target_id = action["target_id"]
            if target_id not in new_state.villager.relations:
                new_state.villager.relations[target_id] = 0
            
            # Slightly improve relationship
            new_state.villager.relations[target_id] += 0.1
            
        elif action["type"] == "rest":
            # Resting improves energy (if we're tracking that)
            if 'energy' in new_state.villager.properties:
                new_state.villager.properties['energy'] = min(
                    new_state.villager.properties['energy'] + 0.2, 
                    1.0
                )
        
        # Clear cached actions since the state has changed
        new_state._possible_actions = None
        
        return new_state
    
    def is_terminal(self):
        """
        Check if this is a terminal state.
        For villagers, there's no real "terminal" state in normal gameplay.
        
        Returns:
            bool: Always False in this implementation
        """
        return False
    
    def get_reward(self):
        """
        Get the reward value for this state.
        Higher means better state for the villager.
        
        Returns:
            float: The calculated reward value
        """
        reward = 0.0
        
        # Reward for completed tasks
        if 'completed_tasks' in self.villager.properties:
            reward += len(self.villager.properties['completed_tasks']) * 1.0
        
        # Reward for being in preferred biome
        current_location = self.villager.location_id
        if 'locations' in self.world_info and current_location in self.world_info['locations']:
            biome = self.world_info['locations'][current_location].get('biome')
            if biome == self.villager.preferred_biome:
                reward += 2.0
        
        # Reward for social relationships
        for relationship_value in self.villager.relations.values():
            reward += relationship_value * 0.5
        
        # Penalty for lack of energy if we're tracking it
        if 'energy' in self.villager.properties:
            if self.villager.properties['energy'] < 0.3:
                reward -= (0.3 - self.villager.properties['energy']) * 3.0
        
        return reward
    
    def clone(self):
        """
        Create a deep copy of this state.
        
        Returns:
            VillagerState: A new identical state object
        """
        return deepcopy(self)
    
    def __str__(self):
        """String representation of the state"""
        return f"VillagerState({self.villager.name} at {self.villager.location_id})"
    
    def to_dict(self):
        """Convert state to dictionary for storage"""
        return {
            "villager": self.villager.to_dict(),
            "world_info": self.world_info,
            "location_graph": self.location_graph
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create state from dictionary data"""
        from ..entities.villager import Villager  # Avoid circular import
        
        villager = Villager.from_dict(data["villager"])
        return cls(
            villager=villager,
            world_info=data.get("world_info", {}),
            location_graph=data.get("location_graph", {})
        )