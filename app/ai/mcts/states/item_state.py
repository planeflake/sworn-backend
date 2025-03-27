"""MCTS state representation for item decision making.

This module provides a state representation for items that is compatible
with the Monte Carlo Tree Search algorithm. It includes action generation,
state transition, and reward calculation for item decision making.
"""

from typing import List, Dict, Any, Optional, Set, Tuple
import random
import logging
import copy

logger = logging.getLogger(__name__)

class ItemAction:
    """Represents an action that can be performed on an item."""
    
    def __init__(self, 
                 action_type: str, 
                 owner_id: Optional[str] = None,
                 location_id: Optional[str] = None):
        """
        Initialize an item action.
        
        Args:
            action_type: Type of action (equip, use, drop, etc.)
            owner_id: ID of the owner entity (for transfer actions)
            location_id: ID of the location (for drop actions)
        """
        self.action_type = action_type
        self.owner_id = owner_id
        self.location_id = location_id
        
        # Optional data for specialized actions
        self.durability_change = 0  # Change in durability from this action
        self.value_change = 0.0  # Change in value from this action
        self.score = 1.0  # Base score for action selection
        
    def __str__(self) -> str:
        """String representation of the action."""
        if self.action_type == "equip":
            return f"Equip item to {self.owner_id}"
        elif self.action_type == "use":
            return "Use item"
        elif self.action_type == "drop":
            return f"Drop item at {self.location_id}"
        elif self.action_type == "transfer":
            return f"Transfer item to {self.owner_id}"
        elif self.action_type == "repair":
            return "Repair item"
        elif self.action_type == "store":
            return f"Store item at {self.location_id}"
        else:
            return f"{self.action_type} action"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert action to dictionary."""
        return {
            "action_type": self.action_type,
            "owner_id": self.owner_id,
            "location_id": self.location_id,
            "durability_change": self.durability_change,
            "value_change": self.value_change,
            "score": self.score
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ItemAction':
        """Create action from dictionary."""
        action = cls(
            action_type=data.get("action_type", "unknown"),
            owner_id=data.get("owner_id"),
            location_id=data.get("location_id")
        )
        action.durability_change = data.get("durability_change", 0)
        action.value_change = data.get("value_change", 0.0)
        action.score = data.get("score", 1.0)
        return action

class ItemState:
    """
    State representation for item AI decision-making using MCTS.
    
    This class represents the state of an item for use in Monte Carlo Tree Search,
    including information about the item, the world, and available actions.
    """
    
    def __init__(self, item_data: Dict[str, Any], world_data: Optional[Dict[str, Any]] = None):
        """
        Initialize item state.
        
        Args:
            item_data: Dictionary with item entity properties
            world_data: Dictionary with world state information
        """
        self.item_data = item_data
        self.world_data = world_data or {}
        self._legal_actions = None
        
        # Cache frequently used values for performance
        self.item_id = item_data.get("id")
        self.item_type = item_data.get("type", "miscellaneous")
        self.is_equipped = item_data.get("is_equipped", False)
        self.is_in_inventory = item_data.get("is_in_inventory", True)
        self.current_owner = item_data.get("current_owner")
        self.current_location = item_data.get("current_location", "inventory")
        self.durability = item_data.get("durability", 100)
        self.value = item_data.get("value", 0)
        self.is_equippable = item_data.get("is_equippable", False)
        self.is_consumable = item_data.get("is_consumable", False)
        self.is_stackable = item_data.get("is_stackable", False)
        self.item_properties = item_data.get("properties", {})
        
    def get_legal_actions(self) -> List[ItemAction]:
        """
        Get all legal actions in the current state.
        
        Returns:
            List of ItemAction objects representing possible actions
        """
        # Use cached actions if available
        if self._legal_actions is not None:
            return self._legal_actions
        
        actions = []
        
        # Generate actions based on item state
        if self.is_in_inventory:
            # Item can be equipped if it's equippable
            if self.is_equippable and not self.is_equipped and self.durability > 0:
                actions.append(ItemAction(
                    action_type="equip",
                    owner_id=self.current_owner
                ))
            
            # Item can be used if it's consumable
            if self.is_consumable:
                actions.append(ItemAction(
                    action_type="use",
                    owner_id=self.current_owner
                ))
            
            # Item can be dropped
            if self.current_location != "ground":
                drop_action = ItemAction(
                    action_type="drop",
                    location_id=self._get_owner_location()
                )
                actions.append(drop_action)
            
            # Item can be transferred if there are other entities nearby
            nearby_entities = self._get_nearby_entities()
            for entity in nearby_entities:
                transfer_action = ItemAction(
                    action_type="transfer",
                    owner_id=entity.get("id")
                )
                actions.append(transfer_action)
            
            # Item can be stored if there are storage options nearby
            storage_options = self._get_storage_options()
            for storage in storage_options:
                store_action = ItemAction(
                    action_type="store",
                    location_id=storage.get("id")
                )
                actions.append(store_action)
        
        # Equipped items can be unequipped
        if self.is_equipped:
            actions.append(ItemAction(
                action_type="unequip",
                owner_id=self.current_owner
            ))
        
        # Items on the ground can be picked up
        if self.current_location == "ground":
            nearby_entities = self._get_nearby_entities()
            for entity in nearby_entities:
                pickup_action = ItemAction(
                    action_type="pickup",
                    owner_id=entity.get("id")
                )
                actions.append(pickup_action)
        
        # Damaged items can be repaired
        if self.durability < 75 and self.is_equippable:
            repair_action = ItemAction(action_type="repair")
            repair_action.durability_change = min(100 - self.durability, 25)  # Repair up to 25 points
            actions.append(repair_action)
        
        # Calculate action scores
        self._calculate_action_scores(actions)
        
        # Cache actions
        self._legal_actions = actions
        return actions
    
    def _get_owner_location(self) -> str:
        """
        Get the current location of the item's owner.
        
        Returns:
            String ID of the owner's location
        """
        if not self.current_owner:
            return "unknown"
            
        entities = self.world_data.get("entities", {})
        if self.current_owner in entities:
            return entities[self.current_owner].get("location_id", "unknown")
        
        return "unknown"
    
    def _get_nearby_entities(self) -> List[Dict[str, Any]]:
        """
        Get all entities near the item that could interact with it.
        
        Returns:
            List of entity data dictionaries
        """
        nearby = []
        
        # If item is in inventory, only the owner is nearby
        if self.is_in_inventory and self.current_owner:
            entities = self.world_data.get("entities", {})
            if self.current_owner in entities:
                nearby.append(entities[self.current_owner])
            return nearby
        
        # Otherwise, get entities at the item's current location
        location_id = self.current_location
        if location_id == "inventory":
            location_id = self._get_owner_location()
        
        location_data = self.world_data.get("locations", {})
        if location_id in location_data:
            entity_ids = location_data[location_id].get("entities", [])
            entities = self.world_data.get("entities", {})
            
            for entity_id in entity_ids:
                if entity_id in entities:
                    nearby.append(entities[entity_id])
        
        return nearby
    
    def _get_storage_options(self) -> List[Dict[str, Any]]:
        """
        Get all storage options near the item.
        
        Returns:
            List of storage data dictionaries
        """
        storage = []
        
        # Get the current location
        location_id = self.current_location
        if location_id == "inventory":
            location_id = self._get_owner_location()
        
        location_data = self.world_data.get("locations", {})
        if location_id in location_data:
            storage_ids = location_data[location_id].get("storage", [])
            storage_data = self.world_data.get("storage", {})
            
            for storage_id in storage_ids:
                if storage_id in storage_data:
                    storage.append(storage_data[storage_id])
        
        return storage
    
    def _calculate_action_scores(self, actions: List[ItemAction]) -> None:
        """
        Calculate scores for each action based on item state and world context.
        
        Args:
            actions: List of actions to score
        """
        for action in actions:
            score = 1.0  # Base score
            
            if action.action_type == "equip":
                # Equipping is more valuable for good items
                quality = self.item_properties.get("quality", 0)
                score = 1.0 + (quality / 100)
                
                # Adjust for item durability
                if self.durability < 50:
                    score *= (self.durability / 100)
            
            elif action.action_type == "use":
                # Using consumables depends on their effect
                effect_value = self.item_properties.get("effect_value", 1)
                score = effect_value / 10
            
            elif action.action_type == "drop":
                # Dropping is less valuable for good items
                quality = self.item_properties.get("quality", 0)
                value = self.value
                
                # Higher quality/value items should be dropped less readily
                score = 0.5 - min(0.4, (quality / 100) + (value / 100))
                
                # Dropping makes more sense for broken items
                if self.durability <= 0:
                    score += 0.5
            
            elif action.action_type == "transfer":
                # Transferring depends on the relationship with recipient
                recipient_id = action.owner_id
                relationship = self._get_relationship_value(recipient_id)
                
                # Better relationships mean more likely to transfer
                score = 0.3 + (relationship * 0.7)
            
            elif action.action_type == "store":
                # Storing makes sense for valuable items
                value = self.value
                score = 0.5 + min(0.5, value / 100)
            
            elif action.action_type == "repair":
                # Repair is more valuable for good items with low durability
                quality = self.item_properties.get("quality", 0)
                missing_durability = 100 - self.durability
                
                score = 0.2 + (quality / 100) + (missing_durability / 100)
            
            elif action.action_type == "pickup":
                # Pickup depends on item value and quality
                quality = self.item_properties.get("quality", 0)
                value = self.value
                
                score = 0.5 + min(0.5, (quality / 100) + (value / 100))
            
            action.score = max(0.1, score)  # Ensure score is positive
    
    def _get_relationship_value(self, entity_id: str) -> float:
        """
        Get the relationship value between the current owner and another entity.
        
        Args:
            entity_id: ID of the other entity
            
        Returns:
            Float between 0 and 1, representing relationship quality
        """
        if not self.current_owner:
            return 0.5  # Default to neutral
        
        relationships = self.world_data.get("relationships", {})
        
        # Check if there's a direct relationship
        relationship_key = f"{self.current_owner}:{entity_id}"
        if relationship_key in relationships:
            return min(1.0, max(0.0, relationships[relationship_key] / 100))
        
        # Check reverse relationship
        relationship_key = f"{entity_id}:{self.current_owner}"
        if relationship_key in relationships:
            return min(1.0, max(0.0, relationships[relationship_key] / 100))
        
        return 0.5  # Default to neutral
    
    def apply_action(self, action: ItemAction) -> 'ItemState':
        """
        Apply an action to this state and return the new state.
        
        Args:
            action: The action to apply
            
        Returns:
            A new ItemState resulting from the action
        """
        # Create a deep copy of the current state
        new_item_data = copy.deepcopy(self.item_data)
        new_state = ItemState(new_item_data, copy.deepcopy(self.world_data))
        
        # Apply the action effect based on type
        if action.action_type == "equip":
            # Equip the item
            new_state.item_data["is_equipped"] = True
            new_state.is_equipped = True
            
            # Each use reduces durability
            new_state.item_data["durability"] = max(0, new_state.durability - 1)
            new_state.durability = new_state.item_data["durability"]
            
            # Being equipped can change value (wear and tear)
            value_change = -0.5  # Small depreciation
            new_state.item_data["value"] = max(0, new_state.value + value_change)
            new_state.value = new_state.item_data["value"]
            
        elif action.action_type == "use":
            if new_state.is_consumable:
                # Consumable item is used up
                new_state.item_data["is_in_inventory"] = False
                new_state.is_in_inventory = False
                new_state.item_data["current_location"] = "consumed"
                new_state.current_location = "consumed"
                
                # Apply any effects of using the item (in a real implementation)
                # This would affect the user, but is not modeled here
            
        elif action.action_type == "drop":
            # Drop the item
            new_state.item_data["is_in_inventory"] = False
            new_state.is_in_inventory = False
            new_state.item_data["is_equipped"] = False
            new_state.is_equipped = False
            
            # Set location to ground
            new_state.item_data["current_location"] = "ground"
            new_state.current_location = "ground"
            
            # Clear owner
            new_state.item_data["current_owner"] = None
            new_state.current_owner = None
            
            # Items on ground can lose value
            value_change = -1.0
            new_state.item_data["value"] = max(0, new_state.value + value_change)
            new_state.value = new_state.item_data["value"]
            
        elif action.action_type == "transfer":
            # Transfer to new owner
            new_state.item_data["current_owner"] = action.owner_id
            new_state.current_owner = action.owner_id
            
            # Remains in inventory
            new_state.item_data["is_in_inventory"] = True
            new_state.is_in_inventory = True
            
            # But is unequipped
            new_state.item_data["is_equipped"] = False
            new_state.is_equipped = False
            
            # Set location to inventory
            new_state.item_data["current_location"] = "inventory"
            new_state.current_location = "inventory"
            
        elif action.action_type == "store":
            # Store in a container
            new_state.item_data["is_in_inventory"] = False
            new_state.is_in_inventory = False
            new_state.item_data["is_equipped"] = False
            new_state.is_equipped = False
            
            # Set location to storage
            new_state.item_data["current_location"] = action.location_id
            new_state.current_location = action.location_id
            
        elif action.action_type == "repair":
            # Improve durability
            new_state.item_data["durability"] = min(100, new_state.durability + action.durability_change)
            new_state.durability = new_state.item_data["durability"]
            
            # Repair may increase value
            value_change = action.durability_change * 0.1
            new_state.item_data["value"] = max(0, new_state.value + value_change)
            new_state.value = new_state.item_data["value"]
            
        elif action.action_type == "pickup":
            # Pick up from ground
            new_state.item_data["is_in_inventory"] = True
            new_state.is_in_inventory = True
            
            # Set new owner
            new_state.item_data["current_owner"] = action.owner_id
            new_state.current_owner = action.owner_id
            
            # Set location to inventory
            new_state.item_data["current_location"] = "inventory"
            new_state.current_location = "inventory"
            
        elif action.action_type == "unequip":
            # Unequip the item
            new_state.item_data["is_equipped"] = False
            new_state.is_equipped = False
            
        # Clear cached actions
        new_state._legal_actions = None
        
        return new_state
    
    def is_terminal(self) -> bool:
        """
        Check if this is a terminal state (simulation should end).
        
        Returns:
            True if terminal, False otherwise
        """
        # Terminal conditions for items:
        
        # 1. Item is consumed
        if self.current_location == "consumed":
            return True
        
        # 2. Item is completely broken (if durability is applicable)
        if self.is_equippable and self.durability <= 0:
            return True
        
        # 3. Item is sold (not modeled in this implementation)
        
        return False
    
    def get_reward(self) -> float:
        """
        Calculate reward value for this state.
        
        Returns:
            Float reward value (higher is better)
        """
        reward = 0.0
        
        # Base reward from item value
        reward += self.value * 0.1
        
        # Reward for durability
        if self.is_equippable:
            reward += self.durability * 0.05
        
        # Reward for being equipped (item is fulfilling its purpose)
        if self.is_equipped:
            # Higher quality equipment gives more reward when equipped
            quality = self.item_properties.get("quality", 0)
            reward += 5.0 + (quality * 0.1)
        
        # Reward for being in inventory (better than on ground)
        if self.is_in_inventory:
            reward += 3.0
        
        # Reward for being stored safely
        if not self.is_in_inventory and self.current_location != "ground" and self.current_location != "consumed":
            reward += 2.0
        
        # Penalty for being on the ground
        if self.current_location == "ground":
            reward -= 5.0
        
        # Additional reward based on item properties
        enchantment = self.item_properties.get("enchantment", 0)
        if enchantment > 0:
            reward += enchantment * 0.5
        
        return reward
    
    def __str__(self) -> str:
        """String representation of the state."""
        item_type = self.item_data.get("type", "item")
        name = self.item_data.get("name", f"Item {self.item_data.get('id', 'unknown')}")
        
        status = "equipped" if self.is_equipped else \
                "in inventory" if self.is_in_inventory else \
                f"at {self.current_location}"
                
        durability_info = f", {self.durability}% durability" if self.is_equippable else ""
        
        return f"{name} ({item_type}): {status}{durability_info}, value {self.value}"
        
    # Method for compatibility with the ItemEntity interface
    @classmethod
    def from_item_entity(cls, item, world_info=None):
        """
        Create an ItemState from an Item entity.
        
        Args:
            item: The item entity
            world_info: Optional world information
            
        Returns:
            ItemState: A new state object representing the item
        """
        # Convert item entity to data dictionary
        item_data = item.to_dict() if hasattr(item, 'to_dict') else {}
        
        # If to_dict isn't available, get properties directly
        if not item_data and hasattr(item, 'get_property'):
            item_data = {
                "id": item.id,
                "name": item.get_property("name"),
                "type": item.get_property("type", "miscellaneous"),
                "is_equipped": item.get_property("is_equipped", False),
                "is_in_inventory": item.get_property("is_in_inventory", True),
                "current_owner": item.get_property("current_owner"),
                "current_location": item.get_property("current_location", "inventory"),
                "durability": item.get_property("durability", 100),
                "value": item.get_property("value", 0),
                "is_equippable": item.get_property("is_equippable", False),
                "is_consumable": item.get_property("is_consumable", False),
                "is_stackable": item.get_property("is_stackable", False),
                "properties": item.get_property("properties", {})
            }
            
        return cls(item_data, world_info or {})