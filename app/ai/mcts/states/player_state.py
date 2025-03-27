"""MCTS state representation for player decision making.

This module provides a state representation for players that is compatible
with the Monte Carlo Tree Search algorithm. It includes action generation,
state transition, and reward calculation for player decision making.
"""

from typing import List, Dict, Any, Optional, Set, Tuple
import random
import logging
import copy

logger = logging.getLogger(__name__)

class PlayerAction:
    """Represents an action that a player can perform."""
    
    def __init__(self, 
                 action_type: str, 
                 target_id: Optional[str] = None,
                 resource_type: Optional[str] = None,
                 amount: Optional[int] = None,
                 location_id: Optional[str] = None):
        """
        Initialize a player action.
        
        Args:
            action_type: Type of action (move, gather, trade, rest, etc.)
            target_id: ID of the target entity (for interaction actions)
            resource_type: Type of resource (for resource-related actions)
            amount: Amount for quantity-based actions
            location_id: ID of the location (for movement actions)
        """
        self.action_type = action_type
        self.target_id = target_id
        self.resource_type = resource_type
        self.amount = amount
        self.location_id = location_id
        
        # Optional data for specialized actions
        self.skill_name = None  # For skill-based actions
        self.item_id = None  # For item-related actions
        self.destination_id = None  # For planning movement
        self.score = 1.0  # Base score for action selection
        
    def __str__(self) -> str:
        """String representation of the action."""
        if self.action_type == "move":
            return f"Move to {self.location_id}"
        elif self.action_type == "gather":
            return f"Gather {self.resource_type}"
        elif self.action_type == "trade":
            return f"Trade with {self.target_id}"
        elif self.action_type == "rest":
            return "Rest to recover"
        elif self.action_type == "use_skill":
            return f"Use skill: {self.skill_name}"
        elif self.action_type == "use_item":
            return f"Use item: {self.item_id}"
        elif self.action_type == "set_destination":
            return f"Set destination to {self.destination_id}"
        else:
            return f"{self.action_type} action"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert action to dictionary."""
        return {
            "action_type": self.action_type,
            "target_id": self.target_id,
            "resource_type": self.resource_type,
            "amount": self.amount,
            "location_id": self.location_id,
            "skill_name": self.skill_name,
            "item_id": self.item_id,
            "destination_id": self.destination_id,
            "score": self.score
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PlayerAction':
        """Create action from dictionary."""
        action = cls(
            action_type=data.get("action_type", "unknown"),
            target_id=data.get("target_id"),
            resource_type=data.get("resource_type"),
            amount=data.get("amount"),
            location_id=data.get("location_id")
        )
        action.skill_name = data.get("skill_name")
        action.item_id = data.get("item_id")
        action.destination_id = data.get("destination_id")
        action.score = data.get("score", 1.0)
        return action

class PlayerState:
    """
    State representation for player AI decision-making using MCTS.
    
    This class represents the state of a player for use in Monte Carlo Tree Search,
    including information about the player, their inventory, equipment, and available actions.
    """
    
    def __init__(self, player_data: Dict[str, Any], world_data: Optional[Dict[str, Any]] = None):
        """
        Initialize player state.
        
        Args:
            player_data: Dictionary with player entity properties
            world_data: Dictionary with world state information
        """
        self.player_data = player_data
        self.world_data = world_data or {}
        self._legal_actions = None
        
        # Cache frequently used values for performance
        self.player_id = player_data.get("player_id")
        self.name = player_data.get("name", "Unknown Player")
        self.current_location_id = player_data.get("current_location_id")
        self.destination_id = player_data.get("destination_id")
        self.resources = player_data.get("resources", {})
        self.skills = player_data.get("skills", {})
        self.health = player_data.get("health", 100)
        self.mana = player_data.get("mana", 100)
        self.stamina = player_data.get("stamina", 100)
        self.preferred_biomes = player_data.get("preferred_biomes", [])
        self.preferred_locations = player_data.get("preferred_locations", [])
        
    def get_legal_actions(self) -> List[PlayerAction]:
        """
        Get all legal actions in the current state.
        
        Returns:
            List of PlayerAction objects representing possible actions
        """
        # Use cached actions if available
        if self._legal_actions is not None:
            return self._legal_actions
        
        actions = []
        
        # Movement actions - get connected locations
        connected_locations = self._get_connected_locations()
        for location_id in connected_locations:
            actions.append(PlayerAction(
                action_type="move",
                location_id=location_id
            ))
        
        # Set destination (longer-term planning)
        known_locations = self._get_known_locations()
        for location_id in known_locations:
            if location_id != self.current_location_id and location_id != self.destination_id:
                action = PlayerAction(
                    action_type="set_destination",
                    destination_id=location_id
                )
                actions.append(action)
        
        # Resource gathering
        resource_types = self._get_available_resources()
        for resource_type in resource_types:
            action = PlayerAction(
                action_type="gather",
                resource_type=resource_type
            )
            actions.append(action)
        
        # Trading actions
        traders = self._get_nearby_traders()
        for trader in traders:
            action = PlayerAction(
                action_type="trade",
                target_id=trader.get("id")
            )
            actions.append(action)
        
        # Rest action (always available)
        actions.append(PlayerAction(action_type="rest"))
        
        # Skill-based actions
        for skill_name, level in self.skills.items():
            if level > 0:  # Only usable skills
                action = PlayerAction(action_type="use_skill")
                action.skill_name = skill_name
                actions.append(action)
        
        # Item-based actions
        inventory_items = self._get_inventory_items()
        for item in inventory_items:
            if item.get("is_usable", False):
                action = PlayerAction(
                    action_type="use_item",
                    item_id=item.get("id")
                )
                actions.append(action)
        
        # Calculate action scores based on player state and preferences
        self._calculate_action_scores(actions)
        
        # Cache actions
        self._legal_actions = actions
        return actions
    
    def _get_connected_locations(self) -> List[str]:
        """
        Get all locations connected to the player's current location.
        
        Returns:
            List of location IDs
        """
        connected = []
        
        # Get location connections from world data
        location_graph = self.world_data.get("location_graph", {})
        current_location = self.current_location_id
        
        if current_location in location_graph:
            connected = location_graph[current_location]
        
        return connected
    
    def _get_known_locations(self) -> List[str]:
        """
        Get all locations known to the player.
        
        Returns:
            List of location IDs
        """
        # In a real implementation, would consider locations player has visited
        # or otherwise knows about. For simplicity, return all locations.
        return list(self.world_data.get("locations", {}).keys())
    
    def _get_available_resources(self) -> List[str]:
        """
        Get types of resources available at the current location.
        
        Returns:
            List of resource types
        """
        resources = []
        
        # Get location details
        locations = self.world_data.get("locations", {})
        current_location = self.current_location_id
        
        if current_location in locations:
            location_data = locations[current_location]
            resources = location_data.get("resources", [])
        
        return resources
    
    def _get_nearby_traders(self) -> List[Dict[str, Any]]:
        """
        Get all traders at the player's current location.
        
        Returns:
            List of trader data dictionaries
        """
        traders = []
        
        # Get entities at current location
        locations = self.world_data.get("locations", {})
        entities = self.world_data.get("entities", {})
        current_location = self.current_location_id
        
        if current_location in locations:
            entity_ids = locations[current_location].get("entities", [])
            
            # Filter for traders
            for entity_id in entity_ids:
                if entity_id in entities:
                    entity = entities[entity_id]
                    if entity.get("type") == "trader":
                        traders.append(entity)
        
        return traders
    
    def _get_inventory_items(self) -> List[Dict[str, Any]]:
        """
        Get all items in the player's inventory.
        
        Returns:
            List of item data dictionaries
        """
        inventory_items = []
        
        # Get player's inventory
        items = self.world_data.get("items", {})
        inventory_ids = self.player_data.get("inventory", [])
        
        for item_id in inventory_ids:
            if item_id in items:
                inventory_items.append(items[item_id])
        
        return inventory_items
    
    def _calculate_action_scores(self, actions: List[PlayerAction]) -> None:
        """
        Calculate scores for each action based on player state and preferences.
        
        Args:
            actions: List of actions to score
        """
        for action in actions:
            score = 1.0  # Base score
            
            if action.action_type == "move":
                # Movement preference based on location and biome preferences
                location_id = action.location_id
                
                # Preferred location bonus
                if location_id in self.preferred_locations:
                    score += 0.5
                
                # Biome preference
                if location_id in self.world_data.get("locations", {}):
                    biome = self.world_data["locations"][location_id].get("biome")
                    if biome in self.preferred_biomes:
                        score += 0.3
                
                # Moving toward destination if one is set
                if self.destination_id:
                    path_length = self._get_path_distance(location_id, self.destination_id)
                    current_distance = self._get_path_distance(self.current_location_id, self.destination_id)
                    
                    # Prefer locations that get us closer to destination
                    if path_length < current_distance:
                        score += 0.4
            
            elif action.action_type == "gather":
                # Resource preference based on current needs
                resource_type = action.resource_type
                
                # Check player's current resources
                current_amount = self.resources.get(resource_type, 0)
                
                # Prefer resources we have less of
                if current_amount < 10:
                    score += 0.5 - (current_amount / 20)
                
                # Skill bonus for gathering
                if f"gather_{resource_type}" in self.skills:
                    score += self.skills[f"gather_{resource_type}"] / 10
            
            elif action.action_type == "trade":
                # Trading preference
                trader_id = action.target_id
                
                # Check if we have resources to trade
                if len(self.resources) > 0 and any(amount >= 5 for amount in self.resources.values()):
                    score += 0.3
                
                # Check relation with trader if available
                relations = self.player_data.get("relations", {})
                if trader_id in relations:
                    relation_value = relations[trader_id]
                    score += relation_value / 200  # Small bonus for good relations
            
            elif action.action_type == "rest":
                # Rest preference based on current health/stamina/mana
                rest_need = (100 - self.health) / 100 + (100 - self.stamina) / 100 + (100 - self.mana) / 100
                score += rest_need * 0.3
            
            elif action.action_type == "use_skill":
                # Skill usage preference based on skill level
                skill_name = action.skill_name
                skill_level = self.skills.get(skill_name, 0)
                
                score += skill_level / 20  # Higher level skills are more preferred
            
            elif action.action_type == "use_item":
                # Item usage preference
                # Would depend on item properties in a full implementation
                score += 0.2
            
            elif action.action_type == "set_destination":
                # Destination selection preference
                destination_id = action.destination_id
                
                # Preferred location bonus
                if destination_id in self.preferred_locations:
                    score += 0.6
                
                # Biome preference
                if destination_id in self.world_data.get("locations", {}):
                    biome = self.world_data["locations"][destination_id].get("biome")
                    if biome in self.preferred_biomes:
                        score += 0.4
                
                # Distance penalty (closer is better)
                distance = self._get_path_distance(self.current_location_id, destination_id)
                score -= min(0.5, distance / 10)  # Small penalty for distant locations
            
            action.score = max(0.1, score)  # Ensure score is positive
    
    def _get_path_distance(self, from_id: str, to_id: str) -> int:
        """
        Calculate approximate path distance between two locations.
        
        Args:
            from_id: Starting location ID
            to_id: Destination location ID
            
        Returns:
            Integer distance (number of steps) or 999 if no path
        """
        # Simple implementation - in a real system would use proper pathfinding
        if from_id == to_id:
            return 0
            
        # Try direct connection
        location_graph = self.world_data.get("location_graph", {})
        if from_id in location_graph and to_id in location_graph[from_id]:
            return 1
            
        # No direct path - return large value
        # A full implementation would use proper pathfinding (BFS/Dijkstra/A*)
        return 999
    
    def apply_action(self, action: PlayerAction) -> 'PlayerState':
        """
        Apply an action to this state and return the new state.
        
        Args:
            action: The action to apply
            
        Returns:
            A new PlayerState resulting from the action
        """
        # Create a deep copy of the current state
        new_player_data = copy.deepcopy(self.player_data)
        new_state = PlayerState(new_player_data, copy.deepcopy(self.world_data))
        
        # Apply the action effect based on type
        if action.action_type == "move":
            # Update location
            new_state.player_data["current_location_id"] = action.location_id
            new_state.current_location_id = action.location_id
            
            # Moving consumes stamina
            stamina_cost = 10  # Base cost
            new_state.player_data["stamina"] = max(0, new_state.stamina - stamina_cost)
            new_state.stamina = new_state.player_data["stamina"]
            
            # If we've reached our destination, clear it
            if new_state.destination_id == action.location_id:
                new_state.player_data["destination_id"] = None
                new_state.destination_id = None
        
        elif action.action_type == "gather":
            # Gather resource
            resource_type = action.resource_type
            gather_amount = 1  # Base amount
            
            # Apply skill bonuses if applicable
            if f"gather_{resource_type}" in new_state.skills:
                skill_level = new_state.skills[f"gather_{resource_type}"]
                gather_amount += skill_level // 5  # Bonus based on skill
            
            # Add to resources
            if resource_type in new_state.resources:
                new_state.player_data["resources"][resource_type] += gather_amount
            else:
                new_state.player_data["resources"][resource_type] = gather_amount
            
            new_state.resources = new_state.player_data["resources"]
            
            # Gathering consumes stamina
            stamina_cost = 5  # Base cost
            new_state.player_data["stamina"] = max(0, new_state.stamina - stamina_cost)
            new_state.stamina = new_state.player_data["stamina"]
        
        elif action.action_type == "trade":
            # Trade would involve complex logic in a real implementation
            # For simplicity, just apply a basic resource exchange
            
            # Add some gold (assuming successful trade)
            if "gold" in new_state.resources:
                new_state.player_data["resources"]["gold"] += 5
            else:
                new_state.player_data["resources"]["gold"] = 5
            
            # Remove some random resource (what was traded away)
            tradeable_resources = [r for r, amt in new_state.resources.items() if r != "gold" and amt > 0]
            if tradeable_resources:
                resource = random.choice(tradeable_resources)
                new_state.player_data["resources"][resource] -= 1
                if new_state.player_data["resources"][resource] <= 0:
                    del new_state.player_data["resources"][resource]
            
            new_state.resources = new_state.player_data["resources"]
            
            # Trading consumes a little stamina
            stamina_cost = 2
            new_state.player_data["stamina"] = max(0, new_state.stamina - stamina_cost)
            new_state.stamina = new_state.player_data["stamina"]
        
        elif action.action_type == "rest":
            # Recover health, stamina, and mana
            recovery_rate = 20  # Base recovery amount
            
            new_state.player_data["health"] = min(100, new_state.health + recovery_rate)
            new_state.player_data["stamina"] = min(100, new_state.stamina + recovery_rate)
            new_state.player_data["mana"] = min(100, new_state.mana + recovery_rate)
            
            new_state.health = new_state.player_data["health"]
            new_state.stamina = new_state.player_data["stamina"]
            new_state.mana = new_state.player_data["mana"]
        
        elif action.action_type == "use_skill":
            # Using skills would have specific effects in a real implementation
            # For simplicity, apply a generic effect
            skill_name = action.skill_name
            
            # Using skills consumes mana
            mana_cost = 5  # Base cost
            new_state.player_data["mana"] = max(0, new_state.mana - mana_cost)
            new_state.mana = new_state.player_data["mana"]
            
            # Skill usage might have specific effects not modeled here
        
        elif action.action_type == "use_item":
            # Using items would have specific effects based on item type
            # For simplicity, apply a generic healing effect
            
            # Assume item is consumed
            item_id = action.item_id
            if "inventory" in new_state.player_data:
                if item_id in new_state.player_data["inventory"]:
                    new_state.player_data["inventory"].remove(item_id)
            
            # Apply health boost as generic effect
            new_state.player_data["health"] = min(100, new_state.health + 15)
            new_state.health = new_state.player_data["health"]
        
        elif action.action_type == "set_destination":
            # Set the destination for future movement
            new_state.player_data["destination_id"] = action.destination_id
            new_state.destination_id = action.destination_id
        
        # Clear cached actions
        new_state._legal_actions = None
        
        return new_state
    
    def is_terminal(self) -> bool:
        """
        Check if this is a terminal state (simulation should end).
        
        Returns:
            True if terminal, False otherwise
        """
        # Terminal conditions for players:
        
        # 1. Health is zero (player is defeated)
        if self.health <= 0:
            return True
        
        # 2. Player has achieved a major goal
        # In a real implementation, would check goal completion
        
        # For now, non-terminal as gameplay continues
        return False
    
    def get_reward(self) -> float:
        """
        Calculate reward value for this state.
        
        Returns:
            Float reward value (higher is better)
        """
        reward = 0.0
        
        # Base reward from health, stamina, and mana
        reward += (self.health / 100) * 10  # Health is important
        reward += (self.stamina / 100) * 5  # Stamina
        reward += (self.mana / 100) * 5  # Mana
        
        # Resource-based rewards
        for resource, amount in self.resources.items():
            if resource == "gold":
                reward += amount * 0.1  # Gold is valuable
            else:
                reward += amount * 0.05  # Other resources
        
        # Location preference reward
        if self.current_location_id in self.preferred_locations:
            reward += 5.0
        
        # Biome preference reward
        locations = self.world_data.get("locations", {})
        if self.current_location_id in locations:
            biome = locations[self.current_location_id].get("biome")
            if biome in self.preferred_biomes:
                reward += 3.0
        
        # Skill-based rewards
        total_skill_levels = sum(self.skills.values())
        reward += total_skill_levels * 0.1
        
        # Goal completion would add more reward in a full implementation
        
        return reward
    
    def __str__(self) -> str:
        """String representation of the state."""
        return f"Player {self.name} at {self.current_location_id}, HP: {self.health}, SP: {self.stamina}, MP: {self.mana}"
        
    @classmethod
    def from_player_entity(cls, player, world_info=None):
        """
        Create a PlayerState from a Player entity.
        
        Args:
            player: The player entity
            world_info: Optional world information
            
        Returns:
            PlayerState: A new state object representing the player
        """
        # Convert player entity to data dictionary
        player_data = player.to_dict() if hasattr(player, 'to_dict') else {}
        
        # If to_dict isn't available, get properties directly
        if not player_data and hasattr(player, 'player_id'):
            player_data = {
                "player_id": player.player_id,
                "name": player.name,
                "description": player.description,
                "current_location_id": player.current_location_id,
                "destination_id": player.destination_id,
                "preferred_biomes": player.preferred_biomes,
                "preferred_locations": player.preferred_locations,
                "reputation": player.reputation,
                "relations": player.relations,
                "resources": player.resources,
                "emotions": player.emotions,
                "life_goals": player.life_goals,
                "skills": player.skills
            }
            
        return cls(player_data, world_info or {})