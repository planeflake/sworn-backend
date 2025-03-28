"""MCTS state representation for animal decision making.

This module provides a state representation for animals that is compatible
with the Monte Carlo Tree Search algorithm. It includes action generation,
state transition, and reward calculation for animal decision making.
"""

from typing import List, Dict, Any, Optional, Set, Tuple
import random
import logging
import copy

logger = logging.getLogger(__name__)

class AnimalAction:
    """Represents an action an animal can take."""
    
    def __init__(self, 
                 action_type: str, 
                 location_id: Optional[str] = None,
                 prey_id: Optional[str] = None,
                 difficulty: Optional[float] = None):
        """
        Initialize an animal action.
        
        Args:
            action_type: Type of action (move, hunt, rest, etc.)
            location_id: ID of the location (for move/rest actions)
            prey_id: ID of the prey (for hunt actions)
            difficulty: Difficulty of the action (for hunt actions)
        """
        self.action_type = action_type
        self.location_id = location_id
        self.prey_id = prey_id
        self.difficulty = difficulty
        
        # Optional data for specialized actions
        self.risk_level = 0.0  # Higher means more dangerous
        self.energy_cost = 1.0  # Energy cost of this action
        self.score = 1.0  # Base score for action selection
        
    def __str__(self) -> str:
        """String representation of the action."""
        if self.action_type == "move":
            return f"Move to {self.location_id}"
        elif self.action_type == "hunt":
            return f"Hunt prey {self.prey_id}"
        elif self.action_type == "rest":
            return "Rest in current location"
        elif self.action_type == "hide":
            return f"Hide in {self.location_id}"
        elif self.action_type == "group":
            return f"Group at {self.location_id}"
        else:
            return f"{self.action_type} action"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert action to dictionary."""
        return {
            "action_type": self.action_type,
            "location_id": self.location_id,
            "prey_id": self.prey_id,
            "difficulty": self.difficulty,
            "risk_level": self.risk_level,
            "energy_cost": self.energy_cost,
            "score": self.score
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AnimalAction':
        """Create action from dictionary."""
        action = cls(
            action_type=data.get("action_type", "unknown"),
            location_id=data.get("location_id"),
            prey_id=data.get("prey_id"),
            difficulty=data.get("difficulty")
        )
        action.risk_level = data.get("risk_level", 0.0)
        action.energy_cost = data.get("energy_cost", 1.0)
        action.score = data.get("score", 1.0)
        return action

class AnimalState:
    """
    State representation for animal AI decision-making using MCTS.
    
    This class represents the state of an animal for use in Monte Carlo Tree Search,
    including information about the animal, the world, and available actions.
    """
    
    def __init__(self, animal_data: Dict[str, Any] = None, world_data: Optional[Dict[str, Any]] = None):
        """
        Initialize animal state.
        
        Args:
            animal_data: Dictionary with animal entity properties
            world_data: Dictionary with world state information
        """
        self.animal_data = animal_data or {}
        self.world_data = world_data or {}
        self._legal_actions = None
        
        # Cache frequently used values for performance
        self.area_id = self.animal_data.get("area_id")
        self.territory = self.animal_data.get("territory", [])
        self.resources = self.animal_data.get("resources", {})
        self.diet = self.animal_data.get("diet", [])
        self.behaviors = self.animal_data.get("behaviors", [])
        self.energy = self.animal_data.get("energy", 100)
        self.health = self.animal_data.get("health", 100)
        
    def get_legal_actions(self) -> List[AnimalAction]:
        """
        Get all legal actions in the current state.
        
        Returns:
            List of AnimalAction objects representing possible actions
        """
        # Use cached actions if available
        if self._legal_actions is not None:
            return self._legal_actions
        
        actions = []
        
        # Add movement actions
        movement_actions = self._get_movement_actions()
        actions.extend(movement_actions)
        
        # Add hunting actions
        hunting_actions = self._get_hunting_actions()
        actions.extend(hunting_actions)
        
        # Add rest action (stay in place)
        rest_action = AnimalAction(action_type="rest", location_id=self.area_id)
        rest_action.energy_cost = 0.5  # Resting costs less energy
        actions.append(rest_action)
        
        # Add hiding actions if animal is skittish
        if "skittish" in self.behaviors:
            hiding_actions = self._get_hiding_actions()
            actions.extend(hiding_actions)
        
        # Add grouping actions if animal is social
        if "social" in self.behaviors:
            grouping_actions = self._get_grouping_actions()
            actions.extend(grouping_actions)
        
        # Calculate action scores based on animal state
        self._calculate_action_scores(actions)
        
        # Cache actions
        self._legal_actions = actions
        return actions
    
    def _get_movement_actions(self) -> List[AnimalAction]:
        """
        Get possible movement actions based on the animal's current location.
        
        Returns:
            List of movement actions
        """
        actions = []
        
        # Get connected locations from the location graph
        location_graph = self.world_data.get("location_graph", {})
        current_location = self.area_id
        
        if current_location in location_graph:
            connected_locations = location_graph[current_location]
            
            for location_id in connected_locations:
                action = AnimalAction(
                    action_type="move",
                    location_id=location_id
                )
                actions.append(action)
        
        return actions
    
    def _get_hunting_actions(self) -> List[AnimalAction]:
        """
        Get possible hunting actions at the current location.
        
        Returns:
            List of hunting actions
        """
        actions = []
        
        # Check if there are prey opportunities at the current location
        prey_data = self.world_data.get("prey_data", {})
        current_location = self.area_id
        
        if current_location in prey_data:
            prey_list = prey_data[current_location]
            
            for prey in prey_list:
                # Only hunt prey if diet matches
                if not self.diet or prey.get("type") in self.diet:
                    action = AnimalAction(
                        action_type="hunt",
                        location_id=current_location,
                        prey_id=prey.get("id"),
                        difficulty=prey.get("difficulty", 1.0)
                    )
                    # Higher difficulty means more energy cost
                    action.energy_cost = 1.0 + (action.difficulty * 0.5)
                    actions.append(action)
        
        return actions
    
    def _get_hiding_actions(self) -> List[AnimalAction]:
        """
        Get possible actions for hiding from danger.
        
        Returns:
            List of hiding actions
        """
        actions = []
        
        # Get connected locations from the location graph
        location_graph = self.world_data.get("location_graph", {})
        current_location = self.area_id
        
        if current_location in location_graph:
            connected_locations = location_graph[current_location]
            
            for location_id in connected_locations:
                action = AnimalAction(
                    action_type="hide",
                    location_id=location_id
                )
                # Hiding costs less energy than moving
                action.energy_cost = 0.7
                actions.append(action)
        
        return actions
    
    def _get_grouping_actions(self) -> List[AnimalAction]:
        """
        Get possible actions for grouping with other animals of the same species.
        
        Returns:
            List of grouping actions
        """
        actions = []
        
        # Get connected locations from the location graph
        location_graph = self.world_data.get("location_graph", {})
        current_location = self.area_id
        
        if current_location in location_graph:
            connected_locations = location_graph[current_location]
            
            for location_id in connected_locations:
                # Check if there are animals of the same species
                animal_data = self.world_data.get("animal_data", {})
                species = self.animal_data.get("species")
                
                if location_id in animal_data and any(animal.get("species") == species for animal in animal_data[location_id]):
                    action = AnimalAction(
                        action_type="group",
                        location_id=location_id
                    )
                    # Grouping has normal energy cost
                    action.energy_cost = 1.0
                    actions.append(action)
        
        return actions
    
    def _calculate_action_scores(self, actions: List[AnimalAction]) -> None:
        """
        Calculate scores for each action based on animal state and preferences.
        
        Args:
            actions: List of actions to score
        """
        for action in actions:
            score = 1.0  # Base score
            
            if action.action_type == "move":
                # Prefer territory
                if action.location_id in self.territory:
                    score += 1.0
                
                # Prefer locations with food
                if self._has_food_at_location(action.location_id):
                    score += 1.5
                
                # Prefer safe locations if health is low
                if self.health < 50 and self._location_safety(action.location_id) > 0.7:
                    score += 2.0
            
            elif action.action_type == "hunt":
                # Adjust based on difficulty and hunger
                hunger = 100 - self.energy
                difficulty_penalty = action.difficulty * 0.5
                hunger_bonus = (hunger / 100) * 2.0
                
                score = 1.0 + hunger_bonus - difficulty_penalty
                
                # Avoid dangerous hunts if health is low
                if self.health < 30 and action.difficulty > 0.7:
                    score -= 2.0
            
            elif action.action_type == "rest":
                # Rest is more appealing when energy is low
                energy_factor = (100 - self.energy) / 100
                score = 0.5 + (energy_factor * 2.0)
                
                # Rest is more appealing in territory
                if action.location_id in self.territory:
                    score += 0.5
                
                # Rest is less appealing if hungry and food is available elsewhere
                if self.energy < 30 and any(self._has_food_at_location(loc) for loc in self._get_connected_locations()):
                    score -= 1.0
            
            elif action.action_type == "hide":
                # Hide is more appealing when there are predators nearby
                predator_threat = self._calculate_predator_threat()
                score = 0.5 + (predator_threat * 3.0)
                
                # Hide is more appealing when health is low
                if self.health < 50:
                    score += 1.0
            
            elif action.action_type == "group":
                # Group is more appealing when there are predators nearby
                predator_threat = self._calculate_predator_threat()
                score = 0.5 + (predator_threat * 2.0)
                
                # Group is more appealing for mating season
                if self.world_data.get("season") == "spring":
                    score += 1.5
            
            # Adjust score based on energy cost
            if self.energy < 30:
                # Penalize high energy actions when energy is low
                score -= action.energy_cost
            
            action.score = max(0.1, score)  # Ensure score is positive
    
    def _has_food_at_location(self, location_id: str) -> bool:
        """
        Check if a location has food suitable for this animal.
        
        Args:
            location_id: ID of the location to check
            
        Returns:
            True if food is available, False otherwise
        """
        prey_data = self.world_data.get("prey_data", {})
        if location_id in prey_data and prey_data[location_id]:
            # Check if any prey matches the animal's diet
            return any(prey.get("type") in self.diet for prey in prey_data[location_id])
        return False
    
    def _location_safety(self, location_id: str) -> float:
        """
        Calculate how safe a location is for this animal.
        
        Args:
            location_id: ID of the location to evaluate
            
        Returns:
            Float between 0 and 1, higher is safer
        """
        # Default to medium safety
        safety = 0.5
        
        # Territory is safer
        if location_id in self.territory:
            safety += 0.3
        
        # Check for predators
        predator_data = self.world_data.get("predator_data", {})
        if location_id in predator_data and predator_data[location_id]:
            # Each predator reduces safety
            safety -= 0.2 * len(predator_data[location_id])
        
        # Ensure safety is between 0 and 1
        return max(0.0, min(1.0, safety))
    
    def _calculate_predator_threat(self) -> float:
        """
        Calculate the current threat level from predators.
        
        Returns:
            Float between 0 and 1, higher is more threatening
        """
        # Default to low threat
        threat = 0.1
        
        # Check for predators at current location
        predator_data = self.world_data.get("predator_data", {})
        current_location = self.area_id
        
        if current_location in predator_data and predator_data[current_location]:
            # Each predator increases threat
            threat += 0.3 * len(predator_data[current_location])
        
        # Check connected locations for predators
        connected_locations = self._get_connected_locations()
        for location_id in connected_locations:
            if location_id in predator_data and predator_data[location_id]:
                # Nearby predators increase threat less than immediate predators
                threat += 0.1 * len(predator_data[location_id])
        
        # Ensure threat is between 0 and 1
        return max(0.0, min(1.0, threat))
    
    def _get_connected_locations(self) -> List[str]:
        """
        Get all locations connected to the current location.
        
        Returns:
            List of connected location IDs
        """
        location_graph = self.world_data.get("location_graph", {})
        current_location = self.area_id
        
        if current_location in location_graph:
            return location_graph[current_location]
        return []
    
    def apply_action(self, action: AnimalAction) -> 'AnimalState':
        """
        Apply an action to this state and return the new state.
        
        Args:
            action: The action to apply
            
        Returns:
            A new AnimalState resulting from the action
        """
        # Create a deep copy of the current state
        new_animal_data = copy.deepcopy(self.animal_data)
        new_state = AnimalState(new_animal_data, copy.deepcopy(self.world_data))
        
        # Apply the action effect based on type
        if action.action_type == "move":
            # Update location
            new_state.animal_data["area_id"] = action.location_id
            new_state.area_id = action.location_id
            
            # Reduce energy
            new_state.animal_data["energy"] = max(0, new_state.energy - action.energy_cost)
            new_state.energy = new_state.animal_data["energy"]
            
        elif action.action_type == "hunt":
            # Simulate hunting success or failure
            success = self._simulate_hunt(action.difficulty)
            
            # Reduce energy regardless of outcome
            new_state.animal_data["energy"] = max(0, new_state.energy - action.energy_cost)
            new_state.energy = new_state.animal_data["energy"]
            
            if success:
                # Get prey resources and add to animal's resources
                prey_data = self.world_data.get("prey_data", {})
                current_location = self.area_id
                
                if current_location in prey_data:
                    for prey in prey_data[current_location]:
                        if prey.get("id") == action.prey_id:
                            # Successful hunt - increase energy
                            energy_gain = prey.get("energy_value", 20)
                            new_state.animal_data["energy"] = min(100, new_state.energy + energy_gain)
                            new_state.energy = new_state.animal_data["energy"]
                            break
            else:
                # Failed hunt - small chance of injury
                if random.random() < 0.1:
                    injury = random.randint(5, 15)
                    new_state.animal_data["health"] = max(0, new_state.health - injury)
                    new_state.health = new_state.animal_data["health"]
        
        elif action.action_type == "rest":
            # Resting recovers energy and health
            energy_recovery = 10
            health_recovery = 5
            
            new_state.animal_data["energy"] = min(100, new_state.energy + energy_recovery)
            new_state.energy = new_state.animal_data["energy"]
            
            new_state.animal_data["health"] = min(100, new_state.health + health_recovery)
            new_state.health = new_state.animal_data["health"]
        
        elif action.action_type == "hide":
            # Hiding reduces energy slightly but increases safety
            new_state.animal_data["energy"] = max(0, new_state.energy - action.energy_cost)
            new_state.energy = new_state.animal_data["energy"]
            
            # Update location if hiding in a different area
            if action.location_id != self.area_id:
                new_state.animal_data["area_id"] = action.location_id
                new_state.area_id = action.location_id
        
        elif action.action_type == "group":
            # Grouping moves to the location and has social benefits
            new_state.animal_data["area_id"] = action.location_id
            new_state.area_id = action.location_id
            
            # Reduce energy
            new_state.animal_data["energy"] = max(0, new_state.energy - action.energy_cost)
            new_state.energy = new_state.animal_data["energy"]
            
            # Being in a group improves safety
            if "grouped" not in new_state.animal_data.get("status", []):
                if "status" not in new_state.animal_data:
                    new_state.animal_data["status"] = []
                new_state.animal_data["status"].append("grouped")
        
        # Clear cached actions
        new_state._legal_actions = None
        
        return new_state
    
    def _simulate_hunt(self, difficulty: float) -> bool:
        """
        Simulate the outcome of a hunt based on difficulty.
        
        Args:
            difficulty: The difficulty of the hunt (0.0-1.0)
            
        Returns:
            True if the hunt was successful, False otherwise
        """
        # Base success chance is inverse of difficulty
        success_chance = 1.0 - difficulty
        
        # Adjust for animal's attributes
        if "predator" in self.behaviors:
            success_chance += 0.2  # Predators are better hunters
        
        if self.energy < 30:
            success_chance -= 0.2  # Low energy makes hunting harder
        
        # Ensure chance is between 0.1 and 0.9
        success_chance = max(0.1, min(0.9, success_chance))
        
        # Roll for success
        return random.random() < success_chance
    
    def is_terminal(self) -> bool:
        """
        Check if this is a terminal state (simulation should end).
        
        Returns:
            True if terminal, False otherwise
        """
        # Terminal conditions:
        
        # 1. Animal is dead (health is zero)
        if self.health <= 0:
            return True
        
        # 2. Animal is starving (energy is zero)
        if self.energy <= 0:
            return True
        
        return False
    
    def get_reward(self) -> float:
        """
        Calculate reward value for this state.
        
        Returns:
            Float reward value (higher is better)
        """
        reward = 0.0
        
        # Reward for health
        reward += self.health * 0.05
        
        # Reward for energy
        reward += self.energy * 0.05
        
        # Reward for being in territory
        if self.area_id in self.territory:
            reward += 10.0
        
        # Reward for having food nearby
        if self._has_food_at_location(self.area_id):
            reward += 5.0
        
        # Reward for safety
        safety = self._location_safety(self.area_id)
        reward += safety * 10.0
        
        # Penalty for being near predators
        predator_threat = self._calculate_predator_threat()
        reward -= predator_threat * 15.0
        
        # Social rewards
        if "social" in self.behaviors and "grouped" in self.animal_data.get("status", []):
            reward += 5.0
        
        return reward
    
    def __str__(self) -> str:
        """String representation of the state."""
        species = self.animal_data.get("species", "Unknown")
        name = self.animal_data.get("name", f"Animal {self.animal_data.get('id', 'unknown')}")
        status = ", ".join(self.animal_data.get("status", []))
        status_str = f" ({status})" if status else ""
        
        return f"{species} {name}{status_str} at {self.area_id} with {self.energy} energy, {self.health} health"
        
    # Method for compatibility with the AnimalEntity interface
    @classmethod
    def from_animal_entity(cls, animal, world_info=None):
        """
        Create an AnimalState from an Animal entity.
        
        Args:
            animal: The animal entity
            world_info: Optional world information
            
        Returns:
            AnimalState: A new state object representing the animal
        """
        # Convert animal entity to data dictionary
        animal_data = animal.to_dict() if hasattr(animal, 'to_dict') else {}
        
        # If to_dict isn't available, get properties directly
        if not animal_data and hasattr(animal, 'get_property'):
            animal_data = {
                "id": animal.id,
                "name": animal.get_property("name"),
                "species": animal.get_property("species"),
                "area_id": animal.get_property("area_id"),
                "territory": animal.get_property("territory", []),
                "resources": animal.get_property("resources", {}),
                "diet": animal.get_property("diet", []),
                "behaviors": animal.get_property("behaviors", []),
                "energy": animal.get_property("energy", 100),
                "health": animal.get_property("health", 100),
                "status": animal.get_property("status", [])
            }
            
        return cls(animal_data, world_info or {})