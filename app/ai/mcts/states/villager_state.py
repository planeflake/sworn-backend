"""MCTS state representation for villager decision making.

This module provides a state representation for villagers that is compatible
with the Monte Carlo Tree Search algorithm. It includes action generation,
state transition, and reward calculation for villager decision making.
"""

from typing import List, Dict, Any, Optional, Set, Tuple
import random
import logging
import copy

logger = logging.getLogger(__name__)

class VillagerAction:
    """Represents an action a villager can take."""
    
    def __init__(self, 
                 action_type: str, 
                 location_id: Optional[str] = None,
                 target_id: Optional[str] = None,
                 resource_type: Optional[str] = None):
        """
        Initialize a villager action.
        
        Args:
            action_type: Type of action (work, rest, travel, socialize, etc.)
            location_id: ID of the location (for travel actions)
            target_id: ID of the target entity (for social/work actions)
            resource_type: Type of resource (for resource actions)
        """
        self.action_type = action_type
        self.location_id = location_id
        self.target_id = target_id
        self.resource_type = resource_type
        
        # Optional data for specialized actions
        self.energy_cost = 0  # Energy cost of this action
        self.happiness_change = 0  # Happiness change from this action
        self.gold_change = 0  # Gold change from this action
        self.score = 1.0  # Base score for action selection
        
    def __str__(self) -> str:
        """String representation of the action."""
        if self.action_type == "work":
            work_type = self.resource_type or "general"
            return f"Work ({work_type}) at {self.location_id}"
        elif self.action_type == "rest":
            return "Rest at home"
        elif self.action_type == "travel":
            return f"Travel to {self.location_id}"
        elif self.action_type == "socialize":
            return f"Socialize with {self.target_id}"
        elif self.action_type == "shop":
            return f"Shop at {self.location_id}"
        elif self.action_type == "gather":
            return f"Gather {self.resource_type} at {self.location_id}"
        else:
            return f"{self.action_type} action"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert action to dictionary."""
        return {
            "type": self.action_type,
            "location_id": self.location_id,
            "target_id": self.target_id,
            "resource_type": self.resource_type,
            "energy_cost": self.energy_cost,
            "happiness_change": self.happiness_change,
            "gold_change": self.gold_change,
            "score": self.score
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VillagerAction':
        """Create action from dictionary."""
        action = cls(
            action_type=data.get("type", "unknown"),
            location_id=data.get("location_id"),
            target_id=data.get("target_id"),
            resource_type=data.get("resource_type")
        )
        action.energy_cost = data.get("energy_cost", 0)
        action.happiness_change = data.get("happiness_change", 0)
        action.gold_change = data.get("gold_change", 0)
        action.score = data.get("score", 1.0)
        return action

class VillagerState:
    """
    State representation for villager AI decision-making using MCTS.
    
    This class represents the state of a villager for use in Monte Carlo Tree Search,
    including information about the villager, the world, and available actions.
    """
    
    def __init__(self, villager_data: Dict[str, Any], world_data: Optional[Dict[str, Any]] = None):
        """
        Initialize villager state.
        
        Args:
            villager_data: Dictionary with villager entity properties
            world_data: Dictionary with world state information
        """
        self.villager_data = villager_data
        self.world_data = world_data or {}
        self._legal_actions = None
        
        # Cache frequently used values for performance
        self.villager_id = villager_data.get("id")
        self.villager_name = villager_data.get("name", "Unknown Villager")
        self.current_location_id = villager_data.get("current_location_id")
        self.home_location_id = villager_data.get("home_location_id")
        self.work_location_id = villager_data.get("work_location_id")
        self.faction_id = villager_data.get("faction_id")
        self.profession = villager_data.get("profession", "none")
        self.skills = villager_data.get("skills", {})
        self.relationships = villager_data.get("relationships", {})
        self.energy = villager_data.get("energy", 100)
        self.happiness = villager_data.get("happiness", 50)
        self.health = villager_data.get("health", 100)
        self.gold = villager_data.get("gold", 0)
        self.inventory = villager_data.get("inventory", {})
        self.needs = villager_data.get("needs", {})
        self.daily_routine = villager_data.get("daily_routine", [])
        self.simulation_time = villager_data.get("simulation_time", 0)
        
    def get_legal_actions(self) -> List[VillagerAction]:
        """
        Get all legal actions in the current state.
        
        Returns:
            List of VillagerAction objects representing possible actions
        """
        # Use cached actions if available
        if self._legal_actions is not None:
            return self._legal_actions
        
        actions = []
        
        # Add actions according to time of day and daily routine
        hour_of_day = self.simulation_time % 24
        routine_action = self._get_routine_action(hour_of_day)
        if routine_action:
            actions.append(routine_action)
        
        # Work actions if it's work time (8am-5pm)
        if 8 <= hour_of_day < 17 and self.work_location_id:
            # Only add work actions if we're at work location
            if self.current_location_id == self.work_location_id:
                work_actions = self._get_work_actions()
                actions.extend(work_actions)
            else:
                # Add travel to work action
                travel_action = VillagerAction(
                    action_type="travel",
                    location_id=self.work_location_id
                )
                travel_action.energy_cost = 10
                actions.append(travel_action)
        
        # Rest actions if it's rest time (evening/night)
        if (hour_of_day >= 20 or hour_of_day < 6) and self.home_location_id:
            # Only add rest actions if we're at home
            if self.current_location_id == self.home_location_id:
                rest_action = VillagerAction(
                    action_type="rest",
                    location_id=self.home_location_id
                )
                rest_action.energy_cost = -20  # Negative cost means energy gain
                rest_action.happiness_change = 5
                actions.append(rest_action)
            else:
                # Add travel to home action
                travel_action = VillagerAction(
                    action_type="travel",
                    location_id=self.home_location_id
                )
                travel_action.energy_cost = 10
                actions.append(travel_action)
        
        # Social actions if it's free time
        if 17 <= hour_of_day < 20:
            social_actions = self._get_social_actions()
            actions.extend(social_actions)
        
        # Shopping actions if it's free time and there are shops
        if 10 <= hour_of_day < 19:
            shop_actions = self._get_shop_actions()
            actions.extend(shop_actions)
        
        # Always allow travel to connected locations
        travel_actions = self._get_travel_actions()
        actions.extend(travel_actions)
        
        # Add resource gathering if there are resources nearby and we have energy
        if self.energy > 30:
            gathering_actions = self._get_gathering_actions()
            actions.extend(gathering_actions)
        
        # If energy is very low, add rest action regardless of time
        if self.energy < 20 and self.current_location_id == self.home_location_id:
            rest_action = VillagerAction(
                action_type="rest",
                location_id=self.current_location_id
            )
            rest_action.energy_cost = -20  # Negative cost means energy gain
            rest_action.happiness_change = 5
            actions.append(rest_action)
        
        # Calculate action scores based on villager state
        self._calculate_action_scores(actions)
        
        # Cache actions
        self._legal_actions = actions
        return actions
    
    def _get_routine_action(self, hour_of_day: int) -> Optional[VillagerAction]:
        """
        Get action from daily routine for the current hour.
        
        Args:
            hour_of_day: Current hour (0-23)
            
        Returns:
            Optional action from routine, or None
        """
        for routine in self.daily_routine:
            start_hour = routine.get("start_hour", 0)
            end_hour = routine.get("end_hour", 0)
            
            if start_hour <= hour_of_day < end_hour:
                action_type = routine.get("action_type")
                location_id = routine.get("location_id")
                
                if action_type and location_id:
                    action = VillagerAction(
                        action_type=action_type,
                        location_id=location_id
                    )
                    
                    # Set default costs based on action type
                    if action_type == "work":
                        action.energy_cost = 15
                        action.gold_change = 5
                    elif action_type == "rest":
                        action.energy_cost = -15
                        action.happiness_change = 5
                    elif action_type == "socialize":
                        action.energy_cost = 10
                        action.happiness_change = 10
                    
                    return action
        
        return None
    
    def _get_work_actions(self) -> List[VillagerAction]:
        """
        Get possible work actions based on profession.
        
        Returns:
            List of work actions
        """
        actions = []
        
        # Base work action
        work_action = VillagerAction(
            action_type="work",
            location_id=self.current_location_id
        )
        work_action.energy_cost = 15
        work_action.gold_change = 5
        
        # Modify based on profession
        if self.profession == "farmer":
            work_action.resource_type = "food"
            work_action.gold_change = 3 + (self.skills.get("farming", 0) // 10)
        elif self.profession == "miner":
            work_action.resource_type = "ore"
            work_action.gold_change = 4 + (self.skills.get("mining", 0) // 10)
        elif self.profession == "blacksmith":
            work_action.resource_type = "tools"
            work_action.gold_change = 5 + (self.skills.get("smithing", 0) // 10)
        elif self.profession == "merchant":
            work_action.resource_type = "goods"
            work_action.gold_change = 6 + (self.skills.get("trading", 0) // 10)
        elif self.profession == "guard":
            work_action.resource_type = "security"
            work_action.gold_change = 4 + (self.skills.get("combat", 0) // 10)
        
        actions.append(work_action)
        
        # Add specialized work actions based on skills
        if "farming" in self.skills and self.skills["farming"] > 30:
            farm_action = VillagerAction(
                action_type="work",
                location_id=self.current_location_id,
                resource_type="crops"
            )
            farm_action.energy_cost = 20
            farm_action.gold_change = 7
            actions.append(farm_action)
        
        if "mining" in self.skills and self.skills["mining"] > 30:
            mine_action = VillagerAction(
                action_type="work",
                location_id=self.current_location_id,
                resource_type="minerals"
            )
            mine_action.energy_cost = 25
            mine_action.gold_change = 8
            actions.append(mine_action)
        
        return actions
    
    def _get_social_actions(self) -> List[VillagerAction]:
        """
        Get possible social actions with other villagers.
        
        Returns:
            List of social actions
        """
        actions = []
        
        # Get other villagers at this location
        location_data = self.world_data.get("locations", {})
        if self.current_location_id in location_data:
            present_villagers = []
            for entity_id in location_data[self.current_location_id].get("entities", []):
                if self._get_entity_type(entity_id) == "villager" and entity_id != self.villager_id:
                    present_villagers.append(entity_id)
            
            # Generate social actions for present villagers
            for villager_id in present_villagers:
                relationship = self.relationships.get(villager_id, 0)
                
                # Basic socialize action
                socialize_action = VillagerAction(
                    action_type="socialize",
                    target_id=villager_id,
                    location_id=self.current_location_id
                )
                socialize_action.energy_cost = 5
                socialize_action.happiness_change = 5 + (relationship // 10)
                actions.append(socialize_action)
                
                # Additional options based on relationship level
                if relationship > 50:
                    # Deeper social interaction with good friends
                    friend_action = VillagerAction(
                        action_type="socialize_friend",
                        target_id=villager_id,
                        location_id=self.current_location_id
                    )
                    friend_action.energy_cost = 8
                    friend_action.happiness_change = 12
                    actions.append(friend_action)
        
        return actions
    
    def _get_shop_actions(self) -> List[VillagerAction]:
        """
        Get possible shop/market actions at current location.
        
        Returns:
            List of shop actions
        """
        actions = []
        
        # Get shops at this location
        location_data = self.world_data.get("locations", {})
        if self.current_location_id in location_data:
            shops = location_data[self.current_location_id].get("shops", [])
            
            for shop_id in shops:
                shop_data = self.world_data.get("shops", {}).get(shop_id, {})
                shop_type = shop_data.get("type", "general")
                
                shop_action = VillagerAction(
                    action_type="shop",
                    location_id=self.current_location_id,
                    target_id=shop_id,
                    resource_type=shop_type
                )
                shop_action.energy_cost = 5
                shop_action.happiness_change = 3
                shop_action.gold_change = -5  # Spending money
                
                # Only allow shopping if villager has gold
                if self.gold >= 5:
                    actions.append(shop_action)
        
        return actions
    
    def _get_travel_actions(self) -> List[VillagerAction]:
        """
        Get possible travel actions to connected locations.
        
        Returns:
            List of travel actions
        """
        actions = []
        
        location_graph = self.world_data.get("location_graph", {})
        if self.current_location_id in location_graph:
            connected_locations = location_graph[self.current_location_id]
            
            for location_id in connected_locations:
                # Skip if we're already at this location
                if location_id == self.current_location_id:
                    continue
                    
                # Create travel action
                travel_action = VillagerAction(
                    action_type="travel",
                    location_id=location_id
                )
                
                # Calculate energy cost based on distance or terrain
                location_data = self.world_data.get("locations", {})
                if location_id in location_data and self.current_location_id in location_data:
                    # In a real implementation, this would use distance calculations
                    # For this example, we'll use a simple energy cost
                    travel_action.energy_cost = 10
                else:
                    travel_action.energy_cost = 15
                
                actions.append(travel_action)
        
        return actions
    
    def _get_gathering_actions(self) -> List[VillagerAction]:
        """
        Get possible resource gathering actions at current location.
        
        Returns:
            List of gathering actions
        """
        actions = []
        
        # Get resources at this location
        location_data = self.world_data.get("locations", {})
        if self.current_location_id in location_data:
            resources = location_data[self.current_location_id].get("resources", {})
            
            for resource_type, amount in resources.items():
                # Only consider resources with sufficient amount
                if amount > 10:
                    gather_action = VillagerAction(
                        action_type="gather",
                        location_id=self.current_location_id,
                        resource_type=resource_type
                    )
                    
                    # Set energy cost and reward based on resource type
                    if resource_type == "wood":
                        gather_action.energy_cost = 15
                        gather_action.gold_change = 3
                    elif resource_type == "herbs":
                        gather_action.energy_cost = 10
                        gather_action.gold_change = 4
                    elif resource_type == "berries":
                        gather_action.energy_cost = 8
                        gather_action.gold_change = 2
                    else:
                        gather_action.energy_cost = 12
                        gather_action.gold_change = 2
                    
                    actions.append(gather_action)
        
        return actions
    
    def _get_entity_type(self, entity_id: str) -> str:
        """
        Determine the type of an entity by its ID.
        
        Args:
            entity_id: The ID of the entity
            
        Returns:
            String representing entity type ("villager", "trader", etc.)
        """
        # Check villagers
        villagers = self.world_data.get("villagers", {})
        if entity_id in villagers:
            return "villager"
            
        # Check traders
        traders = self.world_data.get("traders", {})
        if entity_id in traders:
            return "trader"
            
        # Check shops
        shops = self.world_data.get("shops", {})
        if entity_id in shops:
            return "shop"
            
        return "unknown"
    
    def _calculate_action_scores(self, actions: List[VillagerAction]) -> None:
        """
        Calculate scores for each action based on villager state and needs.
        
        Args:
            actions: List of actions to score
        """
        for action in actions:
            score = 1.0  # Base score
            
            # Adjust based on energy level
            energy_factor = self.energy / 100.0
            
            # Apply different scoring strategies based on action type
            if action.action_type == "work":
                # Work is more important if we need money
                if self.gold < 20:
                    score += 1.0
                
                # Work is less appealing if energy is low
                score *= energy_factor
                
                # Profession-specific bonuses
                if action.resource_type and self.profession == action.resource_type:
                    score += 0.5
            
            elif action.action_type == "rest":
                # Rest is more important when energy is low
                rest_factor = 1.0 - energy_factor
                score = 0.5 + (rest_factor * 1.5)
                
                # Extra bonus for resting at home during night
                hour_of_day = self.simulation_time % 24
                if (hour_of_day >= 22 or hour_of_day < 6) and self.current_location_id == self.home_location_id:
                    score += 1.0
            
            elif action.action_type == "travel":
                # Travel to work during work hours
                hour_of_day = self.simulation_time % 24
                if 7 <= hour_of_day < 9 and action.location_id == self.work_location_id:
                    score += 1.5
                
                # Travel home during evening
                elif 18 <= hour_of_day < 22 and action.location_id == self.home_location_id:
                    score += 1.0
                
                # Penalize unnecessary travel when energy is low
                if self.energy < 30:
                    score -= 0.5
            
            elif action.action_type == "socialize":
                # Socializing is more important if happiness is low
                if self.happiness < 40:
                    score += 1.0
                
                # More appealing with friends
                relationship = self.relationships.get(action.target_id, 0)
                score += relationship / 100.0
            
            elif action.action_type == "shop":
                # Shopping depends on gold and needs
                if self.gold < 10:
                    score -= 0.5
                elif self.gold > 50:
                    score += 0.3
                
                # Shop for food if hungry
                if action.resource_type == "food" and "hunger" in self.needs and self.needs["hunger"] > 50:
                    score += 1.0
            
            elif action.action_type == "gather":
                # Gathering is more appealing if we have the skill
                skill_name = f"{action.resource_type}_gathering"
                if skill_name in self.skills:
                    score += self.skills[skill_name] / 100.0
                
                # Less appealing when energy is low
                score *= energy_factor
            
            # Adjust score based on energy cost
            # High energy actions are less appealing when energy is low
            if action.energy_cost > 0 and self.energy < 50:
                energy_penalty = action.energy_cost * (1.0 - energy_factor) * 0.05
                score -= energy_penalty
            
            # Adjust score based on happiness change
            # Actions that increase happiness are more appealing when happiness is low
            if action.happiness_change > 0 and self.happiness < 50:
                happiness_bonus = action.happiness_change * (1.0 - (self.happiness / 100.0)) * 0.1
                score += happiness_bonus
            
            # Consider daily routine priority
            hour_of_day = self.simulation_time % 24
            for routine in self.daily_routine:
                start_hour = routine.get("start_hour", 0)
                end_hour = routine.get("end_hour", 0)
                
                if start_hour <= hour_of_day < end_hour:
                    if routine.get("action_type") == action.action_type:
                        # This action is part of the routine for this hour
                        score += 1.0
            
            # Set final score
            action.score = max(0.1, score)
    
    def apply_action(self, action: VillagerAction) -> 'VillagerState':
        """
        Apply an action to this state and return the new state.
        
        Args:
            action: The action to apply
            
        Returns:
            A new VillagerState resulting from the action
        """
        # Create a deep copy of the current state
        new_villager_data = copy.deepcopy(self.villager_data)
        new_state = VillagerState(new_villager_data, copy.deepcopy(self.world_data))
        
        # Apply the action effect based on type
        if action.action_type == "work":
            # Work generates money but costs energy
            new_state.villager_data["gold"] = new_state.gold + action.gold_change
            new_state.gold = new_state.villager_data["gold"]
            
            # Reduce energy
            new_state.villager_data["energy"] = max(0, new_state.energy - action.energy_cost)
            new_state.energy = new_state.villager_data["energy"]
            
            # Increase relevant skill
            skill_name = f"{action.resource_type}_skill" if action.resource_type else "work_skill"
            if skill_name not in new_state.villager_data["skills"]:
                new_state.villager_data["skills"][skill_name] = 0
            new_state.villager_data["skills"][skill_name] += 1
            new_state.skills = new_state.villager_data["skills"]
        
        elif action.action_type == "rest":
            # Resting recovers energy and increases happiness
            new_state.villager_data["energy"] = min(100, new_state.energy - action.energy_cost)  # Negative cost
            new_state.energy = new_state.villager_data["energy"]
            
            new_state.villager_data["happiness"] += action.happiness_change
            new_state.happiness = new_state.villager_data["happiness"]
            
            # Reduce hunger need if present
            if "hunger" in new_state.villager_data["needs"]:
                new_state.villager_data["needs"]["hunger"] = max(0, new_state.villager_data["needs"]["hunger"] - 10)
                new_state.needs = new_state.villager_data["needs"]
        
        elif action.action_type == "travel":
            # Update location
            new_state.villager_data["current_location_id"] = action.location_id
            new_state.current_location_id = action.location_id
            
            # Reduce energy
            new_state.villager_data["energy"] = max(0, new_state.energy - action.energy_cost)
            new_state.energy = new_state.villager_data["energy"]
            
            # Small chance to find something during travel
            if random.random() < 0.1:
                item_type = random.choice(["coin", "herb", "wood", "stone", "food"])
                if item_type not in new_state.villager_data["inventory"]:
                    new_state.villager_data["inventory"][item_type] = 0
                new_state.villager_data["inventory"][item_type] += 1
                new_state.inventory = new_state.villager_data["inventory"]
        
        elif action.action_type == "socialize" or action.action_type == "socialize_friend":
            # Socializing affects relationships and happiness
            target_id = action.target_id
            current_relationship = new_state.villager_data["relationships"].get(target_id, 0)
            
            # Improve relationship
            relationship_gain = 5 if action.action_type == "socialize" else 10
            new_state.villager_data["relationships"][target_id] = min(100, current_relationship + relationship_gain)
            new_state.relationships = new_state.villager_data["relationships"]
            
            # Increase happiness
            new_state.villager_data["happiness"] = min(100, new_state.happiness + action.happiness_change)
            new_state.happiness = new_state.villager_data["happiness"]
            
            # Reduce energy
            new_state.villager_data["energy"] = max(0, new_state.energy - action.energy_cost)
            new_state.energy = new_state.villager_data["energy"]
        
        elif action.action_type == "shop":
            # Shopping costs gold but can fulfill needs and increase happiness
            new_state.villager_data["gold"] = max(0, new_state.gold + action.gold_change)  # Negative change
            new_state.gold = new_state.villager_data["gold"]
            
            # Increase happiness
            new_state.villager_data["happiness"] = min(100, new_state.happiness + action.happiness_change)
            new_state.happiness = new_state.villager_data["happiness"]
            
            # Reduce energy
            new_state.villager_data["energy"] = max(0, new_state.energy - action.energy_cost)
            new_state.energy = new_state.villager_data["energy"]
            
            # Add purchased item to inventory
            shop_type = action.resource_type
            item_type = shop_type if shop_type != "general" else random.choice(["food", "tool", "clothing"])
            
            if item_type not in new_state.villager_data["inventory"]:
                new_state.villager_data["inventory"][item_type] = 0
            new_state.villager_data["inventory"][item_type] += 1
            new_state.inventory = new_state.villager_data["inventory"]
            
            # Reduce relevant need
            if shop_type == "food" and "hunger" in new_state.villager_data["needs"]:
                new_state.villager_data["needs"]["hunger"] = max(0, new_state.villager_data["needs"]["hunger"] - 30)
                new_state.needs = new_state.villager_data["needs"]
        
        elif action.action_type == "gather":
            # Gathering costs energy but yields resources and gold
            new_state.villager_data["energy"] = max(0, new_state.energy - action.energy_cost)
            new_state.energy = new_state.villager_data["energy"]
            
            # Add gold from selling resources
            new_state.villager_data["gold"] += action.gold_change
            new_state.gold = new_state.villager_data["gold"]
            
            # Add gathered resource to inventory
            resource_type = action.resource_type
            if resource_type not in new_state.villager_data["inventory"]:
                new_state.villager_data["inventory"][resource_type] = 0
            new_state.villager_data["inventory"][resource_type] += 1
            new_state.inventory = new_state.villager_data["inventory"]
            
            # Increase gathering skill
            skill_name = f"{resource_type}_gathering"
            if skill_name not in new_state.villager_data["skills"]:
                new_state.villager_data["skills"][skill_name] = 0
            new_state.villager_data["skills"][skill_name] += 1
            new_state.skills = new_state.villager_data["skills"]
        
        # Update simulation time (1 hour per action)
        new_state.villager_data["simulation_time"] = new_state.simulation_time + 1
        new_state.simulation_time = new_state.villager_data["simulation_time"]
        
        # Increase hunger need over time
        if "hunger" in new_state.villager_data["needs"]:
            new_state.villager_data["needs"]["hunger"] = min(100, new_state.villager_data["needs"]["hunger"] + 5)
            new_state.needs = new_state.villager_data["needs"]
        
        # Clear cached actions
        new_state._legal_actions = None
        
        return new_state
    
    def is_terminal(self) -> bool:
        """
        Check if this is a terminal state (simulation should end).
        
        Returns:
            True if terminal, False otherwise
        """
        # Terminal conditions:
        
        # 1. Villager has no energy
        if self.energy <= 0:
            return True
        
        # 2. Villager has reached a critical health or happiness level
        if self.health <= 0 or self.happiness <= 0:
            return True
        
        # 3. Long simulation (prevent infinite loops)
        if self.simulation_time >= 168:  # One week of simulation
            return True
        
        return False
    
    def get_reward(self) -> float:
        """
        Calculate reward value for this state.
        
        Returns:
            Float reward value (higher is better)
        """
        reward = 0.0
        
        # Reward for health and well-being
        reward += self.energy * 0.05
        reward += self.happiness * 0.1
        reward += self.health * 0.05
        
        # Reward for gold and inventory
        reward += self.gold * 0.2
        inventory_value = sum(1 for _ in self.inventory.values())
        reward += inventory_value * 0.5
        
        # Reward for skills
        for skill, level in self.skills.items():
            reward += level * 0.02
        
        # Reward for strong relationships
        positive_relationships = sum(1 for value in self.relationships.values() if value > 50)
        reward += positive_relationships * 2.0
        
        # Reward for fulfilling needs
        unfulfilled_needs = sum(value for value in self.needs.values())
        reward -= unfulfilled_needs * 0.01
        
        # Reward for being at appropriate locations at appropriate times
        hour_of_day = self.simulation_time % 24
        if 8 <= hour_of_day < 17 and self.current_location_id == self.work_location_id:
            reward += 10.0  # At work during work hours
        elif (hour_of_day >= 20 or hour_of_day < 6) and self.current_location_id == self.home_location_id:
            reward += 10.0  # At home during rest hours
        
        return reward
    
    def __str__(self) -> str:
        """String representation of the state."""
        hour_of_day = self.simulation_time % 24
        location_type = "home" if self.current_location_id == self.home_location_id else \
                        "work" if self.current_location_id == self.work_location_id else \
                        "traveling"
        
        return f"{self.villager_name} ({self.profession}) at {location_type}, hour {hour_of_day}, energy: {self.energy}, happiness: {self.happiness}, gold: {self.gold}"
        
    # Method for compatibility with the VillagerEntity interface
    @classmethod
    def from_villager_entity(cls, villager, world_info=None):
        """
        Create a VillagerState from a Villager entity.
        
        Args:
            villager: The villager entity
            world_info: Optional world information
            
        Returns:
            VillagerState: A new state object representing the villager
        """
        # Convert villager entity to data dictionary
        villager_data = villager.to_dict() if hasattr(villager, 'to_dict') else {}
        
        # If to_dict isn't available, get properties directly
        if not villager_data and hasattr(villager, 'get_property'):
            villager_data = {
                "id": getattr(villager, 'id', None),
                "name": villager.get_property("name"),
                "current_location_id": villager.get_property("current_location_id"),
                "home_location_id": villager.get_property("home_location_id"),
                "work_location_id": villager.get_property("work_location_id"),
                "faction_id": villager.get_property("faction_id"),
                "profession": villager.get_property("profession", "none"),
                "skills": villager.get_property("skills", {}),
                "relationships": villager.get_property("relationships", {}),
                "energy": villager.get_property("energy", 100),
                "happiness": villager.get_property("happiness", 50),
                "health": villager.get_property("health", 100),
                "gold": villager.get_property("gold", 0),
                "inventory": villager.get_property("inventory", {}),
                "needs": villager.get_property("needs", {}),
                "daily_routine": villager.get_property("daily_routine", []),
                "simulation_time": villager.get_property("simulation_time", 0)
            }
            
        return cls(villager_data, world_info or {})