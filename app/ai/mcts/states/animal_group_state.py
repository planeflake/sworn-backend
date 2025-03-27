"""MCTS state representation for animal group decision making.

This module provides a state representation for animal groups that is compatible
with the Monte Carlo Tree Search algorithm. It includes action generation,
state transition, and reward calculation for animal group decision making.
"""

from typing import List, Dict, Any, Optional, Set, Tuple
import random
import logging
import copy

logger = logging.getLogger(__name__)

class AnimalGroupAction:
    """Represents an action an animal group can take."""
    
    def __init__(self, 
                 action_type: str, 
                 location_id: Optional[str] = None,
                 target_id: Optional[str] = None):
        """
        Initialize an animal group action.
        
        Args:
            action_type: Type of action (move, forage, rest, etc.)
            location_id: ID of the location (for move/rest actions)
            target_id: ID of the target (for forage/attack actions)
        """
        self.action_type = action_type
        self.location_id = location_id
        self.target_id = target_id
        
        # Optional data for specialized actions
        self.risk_level = 0.0  # Higher means more dangerous
        self.energy_cost = 1.0  # Energy cost of this action
        self.score = 1.0  # Base score for action selection
        
    def __str__(self) -> str:
        """String representation of the action."""
        if self.action_type == "move":
            return f"Move to {self.location_id}"
        elif self.action_type == "forage":
            return f"Forage at {self.location_id}"
        elif self.action_type == "attack":
            return f"Attack target {self.target_id}"
        elif self.action_type == "rest":
            return "Rest in current location"
        elif self.action_type == "defend":
            return f"Defend against {self.target_id}"
        elif self.action_type == "migrate":
            return f"Migrate to {self.location_id}"
        else:
            return f"{self.action_type} action"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert action to dictionary."""
        return {
            "action_type": self.action_type,
            "location_id": self.location_id,
            "target_id": self.target_id,
            "risk_level": self.risk_level,
            "energy_cost": self.energy_cost,
            "score": self.score
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AnimalGroupAction':
        """Create action from dictionary."""
        action = cls(
            action_type=data.get("action_type", "unknown"),
            location_id=data.get("location_id"),
            target_id=data.get("target_id")
        )
        action.risk_level = data.get("risk_level", 0.0)
        action.energy_cost = data.get("energy_cost", 1.0)
        action.score = data.get("score", 1.0)
        return action

class AnimalGroupState:
    """
    State representation for animal group AI decision-making using MCTS.
    
    This class represents the state of an animal group for use in Monte Carlo Tree Search,
    including information about the group, the world, and available actions.
    """
    
    def __init__(self, group_data: Dict[str, Any], world_data: Optional[Dict[str, Any]] = None):
        """
        Initialize animal group state.
        
        Args:
            group_data: Dictionary with animal group entity properties
            world_data: Dictionary with world state information
        """
        self.group_data = group_data
        self.world_data = world_data or {}
        self._legal_actions = None
        
        # Cache frequently used values for performance
        self.area_id = group_data.get("area_id")
        self.territory = group_data.get("territory", [])
        self.group_type = group_data.get("group_type", "herd")
        self.species = group_data.get("species")
        self.size = group_data.get("size", 1)
        self.energy = group_data.get("energy", 100)
        self.health = group_data.get("health", 100)
        self.behaviors = group_data.get("behaviors", [])
        self.diet = group_data.get("diet", [])
        
    def get_legal_actions(self) -> List[AnimalGroupAction]:
        """
        Get all legal actions in the current state.
        
        Returns:
            List of AnimalGroupAction objects representing possible actions
        """
        # Use cached actions if available
        if self._legal_actions is not None:
            return self._legal_actions
        
        actions = []
        
        # Add movement actions
        movement_actions = self._get_movement_actions()
        actions.extend(movement_actions)
        
        # Add forage actions
        forage_actions = self._get_forage_actions()
        actions.extend(forage_actions)
        
        # Add attack actions if the group is predatory
        if "predatory" in self.behaviors:
            attack_actions = self._get_attack_actions()
            actions.extend(attack_actions)
        
        # Add defense actions
        defense_actions = self._get_defense_actions()
        actions.extend(defense_actions)
        
        # Add migration actions if seasonal
        if "migratory" in self.behaviors and self._should_migrate():
            migration_actions = self._get_migration_actions()
            actions.extend(migration_actions)
        
        # Add rest action (stay in place)
        rest_action = AnimalGroupAction(action_type="rest", location_id=self.area_id)
        rest_action.energy_cost = 0.5  # Resting costs less energy
        actions.append(rest_action)
        
        # Calculate action scores based on group state
        self._calculate_action_scores(actions)
        
        # Cache actions
        self._legal_actions = actions
        return actions
    
    def _get_movement_actions(self) -> List[AnimalGroupAction]:
        """
        Get possible movement actions based on the group's current location.
        
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
                action = AnimalGroupAction(
                    action_type="move",
                    location_id=location_id
                )
                # Larger groups move slower
                action.energy_cost = 1.0 + (0.1 * min(10, self.size / 5))
                actions.append(action)
        
        return actions
    
    def _get_forage_actions(self) -> List[AnimalGroupAction]:
        """
        Get possible foraging actions at the current location.
        
        Returns:
            List of forage actions
        """
        actions = []
        
        # Forage at current location
        action = AnimalGroupAction(
            action_type="forage",
            location_id=self.area_id
        )
        # Adjust energy cost based on group size
        action.energy_cost = 0.8 + (0.05 * min(10, self.size / 5))
        actions.append(action)
        
        # Check if there are special forage opportunities at connected locations
        location_graph = self.world_data.get("location_graph", {})
        current_location = self.area_id
        
        if current_location in location_graph:
            connected_locations = location_graph[current_location]
            
            for location_id in connected_locations:
                if self._has_food_at_location(location_id):
                    action = AnimalGroupAction(
                        action_type="forage",
                        location_id=location_id
                    )
                    # Adjust energy cost based on group size and travel
                    action.energy_cost = 1.2 + (0.05 * min(10, self.size / 5))
                    actions.append(action)
        
        return actions
    
    def _get_attack_actions(self) -> List[AnimalGroupAction]:
        """
        Get possible attack actions at nearby locations.
        
        Returns:
            List of attack actions
        """
        actions = []
        
        # Check for prey groups at current and connected locations
        current_location = self.area_id
        prey_data = self.world_data.get("animal_group_data", {})
        
        # Current location
        if current_location in prey_data:
            for prey in prey_data[current_location]:
                # Only attack if prey isn't same species and is weaker
                if prey.get("species") != self.species and prey.get("size", 0) < self.size:
                    action = AnimalGroupAction(
                        action_type="attack",
                        location_id=current_location,
                        target_id=prey.get("id")
                    )
                    # Attacking costs energy
                    action.energy_cost = 1.5
                    # Higher risk for larger prey
                    action.risk_level = min(0.8, prey.get("size", 0) / self.size)
                    actions.append(action)
        
        # Connected locations
        location_graph = self.world_data.get("location_graph", {})
        if current_location in location_graph:
            connected_locations = location_graph[current_location]
            
            for location_id in connected_locations:
                if location_id in prey_data:
                    for prey in prey_data[location_id]:
                        # Only attack if prey isn't same species and is weaker
                        if prey.get("species") != self.species and prey.get("size", 0) < self.size:
                            action = AnimalGroupAction(
                                action_type="attack",
                                location_id=location_id,
                                target_id=prey.get("id")
                            )
                            # Attacking and moving costs more energy
                            action.energy_cost = 2.0
                            # Higher risk for larger prey
                            action.risk_level = min(0.8, prey.get("size", 0) / self.size)
                            actions.append(action)
        
        return actions
    
    def _get_defense_actions(self) -> List[AnimalGroupAction]:
        """
        Get possible defense actions if threatened.
        
        Returns:
            List of defense actions
        """
        actions = []
        
        # Check for threatening predators
        current_location = self.area_id
        predator_data = self.world_data.get("predator_data", {})
        
        if current_location in predator_data and predator_data[current_location]:
            for predator in predator_data[current_location]:
                action = AnimalGroupAction(
                    action_type="defend",
                    location_id=current_location,
                    target_id=predator.get("id")
                )
                # Defense costs energy
                action.energy_cost = 1.2
                # Higher risk for larger predators
                action.risk_level = min(0.9, predator.get("size", 0) / self.size)
                actions.append(action)
        
        return actions
    
    def _get_migration_actions(self) -> List[AnimalGroupAction]:
        """
        Get possible migration actions based on season.
        
        Returns:
            List of migration actions
        """
        actions = []
        
        # Get migration targets based on current season
        season = self.world_data.get("season", "summer")
        migration_targets = self.group_data.get("migration_targets", {})
        
        if season in migration_targets and migration_targets[season]:
            for target_id in migration_targets[season]:
                action = AnimalGroupAction(
                    action_type="migrate",
                    location_id=target_id
                )
                # Migration is expensive
                action.energy_cost = 2.0
                actions.append(action)
        
        return actions
    
    def _should_migrate(self) -> bool:
        """
        Determine if the group should consider migration based on season.
        
        Returns:
            True if migration should be considered, False otherwise
        """
        # Check if it's a migration season
        season = self.world_data.get("season", "summer")
        migration_seasons = self.group_data.get("migration_seasons", ["spring", "fall"])
        
        return season in migration_seasons
    
    def _has_food_at_location(self, location_id: str) -> bool:
        """
        Check if a location has food suitable for this group.
        
        Args:
            location_id: ID of the location to check
            
        Returns:
            True if food is available, False otherwise
        """
        # Check vegetation if herbivore
        if "herbivore" in self.diet:
            vegetation_data = self.world_data.get("vegetation_data", {})
            if location_id in vegetation_data and vegetation_data[location_id] > 50:
                return True
        
        # Check prey if carnivore
        if "carnivore" in self.diet:
            prey_data = self.world_data.get("animal_group_data", {})
            if location_id in prey_data and any(prey.get("size", 0) < self.size for prey in prey_data[location_id]):
                return True
        
        return False
    
    def _calculate_action_scores(self, actions: List[AnimalGroupAction]) -> None:
        """
        Calculate scores for each action based on group state and preferences.
        
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
                    
                    # Bonus if group is hungry
                    if self.energy < 50:
                        score += 1.0
                
                # Prefer safer locations
                safety = self._location_safety(action.location_id)
                score += safety * 0.5
            
            elif action.action_type == "forage":
                # Foraging is more important when hungry
                hunger = 100 - self.energy
                score = 1.0 + (hunger / 100) * 2.0
                
                # Bonus for good foraging locations
                if self._has_food_at_location(action.location_id):
                    score += 1.0
            
            elif action.action_type == "attack":
                # Attacking is more important when hungry
                hunger = 100 - self.energy
                score = 0.5 + (hunger / 100) * 1.5
                
                # Penalize risky attacks when health is low
                if self.health < 50:
                    score -= action.risk_level * 2.0
            
            elif action.action_type == "defend":
                # Defense is more important with young in group
                if "has_young" in self.group_data.get("status", []):
                    score += 2.0
                
                # Defense is more important in territory
                if self.area_id in self.territory:
                    score += 1.0
            
            elif action.action_type == "migrate":
                # Migration is high priority in migration seasons
                score = 2.0
                
                # Less appealing if group is weak
                if self.energy < 50 or self.health < 50:
                    score -= 1.0
            
            elif action.action_type == "rest":
                # Rest is more appealing when energy is low
                energy_factor = (100 - self.energy) / 100
                health_factor = (100 - self.health) / 100
                score = 0.5 + (energy_factor * 1.0) + (health_factor * 1.0)
                
                # Rest is more appealing in territory
                if self.area_id in self.territory:
                    score += 0.5
                
                # Rest is less appealing if hungry and food is available elsewhere
                if self.energy < 30 and any(self._has_food_at_location(loc) for loc in self._get_connected_locations()):
                    score -= 1.0
            
            # Adjust score based on energy cost
            if self.energy < 30:
                # Penalize high energy actions when energy is low
                score -= action.energy_cost
            
            # Adjust score based on risk level
            if self.health < 50:
                # Penalize risky actions when health is low
                score -= action.risk_level * 2.0
            
            action.score = max(0.1, score)  # Ensure score is positive
    
    def _location_safety(self, location_id: str) -> float:
        """
        Calculate how safe a location is for this group.
        
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
            # Each predator reduces safety based on relative size
            for predator in predator_data[location_id]:
                size_ratio = predator.get("size", 0) / max(1, self.size)
                safety -= 0.2 * min(1.0, size_ratio)
        
        # Ensure safety is between 0 and 1
        return max(0.0, min(1.0, safety))
    
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
    
    def apply_action(self, action: AnimalGroupAction) -> 'AnimalGroupState':
        """
        Apply an action to this state and return the new state.
        
        Args:
            action: The action to apply
            
        Returns:
            A new AnimalGroupState resulting from the action
        """
        # Create a deep copy of the current state
        new_group_data = copy.deepcopy(self.group_data)
        new_state = AnimalGroupState(new_group_data, copy.deepcopy(self.world_data))
        
        # Apply the action effect based on type
        if action.action_type == "move":
            # Update location
            new_state.group_data["area_id"] = action.location_id
            new_state.area_id = action.location_id
            
            # Reduce energy
            new_state.group_data["energy"] = max(0, new_state.energy - action.energy_cost)
            new_state.energy = new_state.group_data["energy"]
            
        elif action.action_type == "forage":
            # Foraging success depends on location and diet
            success_chance = self._calculate_forage_success(action.location_id)
            success = random.random() < success_chance
            
            # Reduce energy regardless of outcome
            new_state.group_data["energy"] = max(0, new_state.energy - action.energy_cost)
            new_state.energy = new_state.group_data["energy"]
            
            if success:
                # Successful foraging increases energy
                energy_gain = random.randint(10, 20) * success_chance
                new_state.group_data["energy"] = min(100, new_state.energy + energy_gain)
                new_state.energy = new_state.group_data["energy"]
                
                # Potentially increase group size if energy is good
                if new_state.energy > 80 and random.random() < 0.1:
                    new_state.group_data["size"] += 1
                    new_state.size = new_state.group_data["size"]
            
            # If foraging at a different location, move there
            if action.location_id != self.area_id:
                new_state.group_data["area_id"] = action.location_id
                new_state.area_id = action.location_id
            
        elif action.action_type == "attack":
            # Attack success depends on relative size and energy
            target_data = self._get_target_data(action.target_id, action.location_id)
            if target_data:
                size_ratio = self.size / max(1, target_data.get("size", 1))
                energy_factor = self.energy / 100
                success_chance = min(0.9, size_ratio * energy_factor)
                success = random.random() < success_chance
                
                # Reduce energy regardless of outcome
                new_state.group_data["energy"] = max(0, new_state.energy - action.energy_cost)
                new_state.energy = new_state.group_data["energy"]
                
                if success:
                    # Successful attack increases energy
                    energy_gain = target_data.get("size", 0) * 5
                    new_state.group_data["energy"] = min(100, new_state.energy + energy_gain)
                    new_state.energy = new_state.group_data["energy"]
                else:
                    # Failed attack might cause injuries
                    if random.random() < 0.3:
                        injury = random.randint(5, 15)
                        new_state.group_data["health"] = max(0, new_state.health - injury)
                        new_state.health = new_state.group_data["health"]
                        
                        # Potentially decrease group size if badly injured
                        if injury > 10 and self.size > 1:
                            new_state.group_data["size"] -= 1
                            new_state.size = new_state.group_data["size"]
            
            # If attacking at a different location, move there
            if action.location_id != self.area_id:
                new_state.group_data["area_id"] = action.location_id
                new_state.area_id = action.location_id
            
        elif action.action_type == "defend":
            # Defense success depends on group size and health
            size_factor = self.size / 10  # Larger groups defend better
            health_factor = self.health / 100
            success_chance = min(0.9, 0.3 + (size_factor * 0.5) + (health_factor * 0.2))
            success = random.random() < success_chance
            
            # Reduce energy
            new_state.group_data["energy"] = max(0, new_state.energy - action.energy_cost)
            new_state.energy = new_state.group_data["energy"]
            
            if not success:
                # Failed defense causes injuries and possible size reduction
                injury = random.randint(10, 25)
                new_state.group_data["health"] = max(0, new_state.health - injury)
                new_state.health = new_state.group_data["health"]
                
                # Potentially decrease group size
                if self.size > 1 and random.random() < 0.5:
                    size_loss = random.randint(1, max(1, self.size // 4))
                    new_state.group_data["size"] = max(1, new_state.size - size_loss)
                    new_state.size = new_state.group_data["size"]
            
        elif action.action_type == "migrate":
            # Migration moves to new location but costs energy
            new_state.group_data["area_id"] = action.location_id
            new_state.area_id = action.location_id
            
            # Reduce energy significantly
            new_state.group_data["energy"] = max(0, new_state.energy - action.energy_cost)
            new_state.energy = new_state.group_data["energy"]
            
            # Small chance of losing members during migration
            if self.size > 2 and random.random() < 0.2:
                size_loss = random.randint(1, max(1, self.size // 5))
                new_state.group_data["size"] = max(1, new_state.size - size_loss)
                new_state.size = new_state.group_data["size"]
            
            # Add location to the group's territory if not already there
            if action.location_id not in new_state.territory:
                if "territory" not in new_state.group_data:
                    new_state.group_data["territory"] = []
                new_state.group_data["territory"].append(action.location_id)
                new_state.territory = new_state.group_data["territory"]
            
        elif action.action_type == "rest":
            # Resting recovers energy and health
            energy_recovery = 15
            health_recovery = 10
            
            new_state.group_data["energy"] = min(100, new_state.energy + energy_recovery)
            new_state.energy = new_state.group_data["energy"]
            
            new_state.group_data["health"] = min(100, new_state.health + health_recovery)
            new_state.health = new_state.group_data["health"]
            
            # Small chance of increasing group size if conditions are good
            if new_state.energy > 80 and new_state.health > 80 and random.random() < 0.1:
                new_state.group_data["size"] += 1
                new_state.size = new_state.group_data["size"]
                
                if "has_young" not in new_state.group_data.get("status", []):
                    if "status" not in new_state.group_data:
                        new_state.group_data["status"] = []
                    new_state.group_data["status"].append("has_young")
        
        # Clear cached actions
        new_state._legal_actions = None
        
        return new_state
    
    def _calculate_forage_success(self, location_id: str) -> float:
        """
        Calculate the success chance for foraging at a location.
        
        Args:
            location_id: ID of the location to evaluate
            
        Returns:
            Float between 0 and 1, representing chance of success
        """
        # Base success chance
        success_chance = 0.5
        
        # Check vegetation if herbivore
        if "herbivore" in self.diet:
            vegetation_data = self.world_data.get("vegetation_data", {})
            if location_id in vegetation_data:
                # Higher vegetation level increases success chance
                veg_level = vegetation_data[location_id]
                success_chance += (veg_level / 100) * 0.4
        
        # Check prey if carnivore
        if "carnivore" in self.diet:
            prey_data = self.world_data.get("animal_group_data", {})
            if location_id in prey_data:
                # More prey increases success chance
                prey_count = len(prey_data[location_id])
                success_chance += min(0.3, prey_count * 0.1)
        
        # Group size affects foraging success
        size_bonus = min(0.2, (self.size / 20) * 0.2)
        success_chance += size_bonus
        
        # Ensure chance is between 0.1 and 0.9
        return max(0.1, min(0.9, success_chance))
    
    def _get_target_data(self, target_id: str, location_id: str) -> Dict[str, Any]:
        """
        Get data for a target entity (prey, predator, etc.).
        
        Args:
            target_id: ID of the target
            location_id: ID of the location
            
        Returns:
            Dictionary with target data, or empty dict if not found
        """
        # Check animal groups
        animal_group_data = self.world_data.get("animal_group_data", {})
        if location_id in animal_group_data:
            for group in animal_group_data[location_id]:
                if group.get("id") == target_id:
                    return group
        
        # Check predators
        predator_data = self.world_data.get("predator_data", {})
        if location_id in predator_data:
            for predator in predator_data[location_id]:
                if predator.get("id") == target_id:
                    return predator
        
        return {}
    
    def is_terminal(self) -> bool:
        """
        Check if this is a terminal state (simulation should end).
        
        Returns:
            True if terminal, False otherwise
        """
        # Terminal conditions:
        
        # 1. Group is wiped out (size is zero)
        if self.size <= 0:
            return True
        
        # 2. Group is dead (health is zero)
        if self.health <= 0:
            return True
        
        # 3. Group is starving (energy is zero)
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
        
        # Reward for group size
        reward += self.size * 5.0
        
        # Reward for health
        reward += self.health * 0.1
        
        # Reward for energy
        reward += self.energy * 0.1
        
        # Reward for being in territory
        if self.area_id in self.territory:
            reward += 10.0
        
        # Reward for having food nearby
        if self._has_food_at_location(self.area_id):
            reward += 5.0
        
        # Reward for safety
        safety = self._location_safety(self.area_id)
        reward += safety * 10.0
        
        # Reward for successful migration (if migratory)
        if "migratory" in self.behaviors and self._should_migrate():
            season = self.world_data.get("season", "summer")
            migration_targets = self.group_data.get("migration_targets", {})
            
            if season in migration_targets and self.area_id in migration_targets[season]:
                reward += 20.0
        
        # Reward for having young
        if "has_young" in self.group_data.get("status", []):
            reward += 15.0
        
        return reward
    
    def __str__(self) -> str:
        """String representation of the state."""
        species = self.group_data.get("species", "Unknown")
        group_type = self.group_data.get("group_type", "group")
        size = self.group_data.get("size", 0)
        status = ", ".join(self.group_data.get("status", []))
        status_str = f" ({status})" if status else ""
        
        return f"{species} {group_type} of {size}{status_str} at {self.area_id} with {self.energy} energy, {self.health} health"
        
    # Method for compatibility with the AnimalGroupEntity interface
    @classmethod
    def from_animal_group_entity(cls, group, world_info=None):
        """
        Create an AnimalGroupState from an AnimalGroup entity.
        
        Args:
            group: The animal group entity
            world_info: Optional world information
            
        Returns:
            AnimalGroupState: A new state object representing the animal group
        """
        # Convert group entity to data dictionary
        group_data = group.to_dict() if hasattr(group, 'to_dict') else {}
        
        # If to_dict isn't available, get properties directly
        if not group_data and hasattr(group, 'get_property'):
            group_data = {
                "id": group.id,
                "group_type": group.get_property("group_type", "herd"),
                "species": group.get_property("species"),
                "area_id": group.get_property("area_id"),
                "territory": group.get_property("territory", []),
                "behaviors": group.get_property("behaviors", []),
                "diet": group.get_property("diet", []),
                "size": group.get_property("size", 1),
                "energy": group.get_property("energy", 100),
                "health": group.get_property("health", 100),
                "status": group.get_property("status", []),
                "migration_targets": group.get_property("migration_targets", {}),
                "migration_seasons": group.get_property("migration_seasons", [])
            }
            
        return cls(group_data, world_info or {})