"""MCTS state representation for equipment decision making.

This module provides a state representation for equipment that is compatible
with the Monte Carlo Tree Search algorithm. It includes action generation,
state transition, and reward calculation for equipment decision making.
"""

from typing import List, Dict, Any, Optional, Set, Tuple
import random
import logging
import copy

logger = logging.getLogger(__name__)

class EquipmentAction:
    """Represents an action that can be performed on equipment."""
    
    def __init__(self, 
                 action_type: str, 
                 slot: Optional[str] = None,
                 item_id: Optional[str] = None):
        """
        Initialize an equipment action.
        
        Args:
            action_type: Type of action (equip, unequip, swap, etc.)
            slot: Equipment slot involved in the action
            item_id: ID of the item involved in the action
        """
        self.action_type = action_type
        self.slot = slot
        self.item_id = item_id
        
        # Optional data for specialized actions
        self.target_slot = None  # For swap actions between slots
        self.score = 1.0  # Base score for action selection
        
    def __str__(self) -> str:
        """String representation of the action."""
        if self.action_type == "equip":
            return f"Equip item {self.item_id} to {self.slot}"
        elif self.action_type == "unequip":
            return f"Unequip item from {self.slot}"
        elif self.action_type == "swap":
            return f"Swap item in {self.slot} with item in {self.target_slot}"
        elif self.action_type == "repair":
            return f"Repair item in {self.slot}"
        else:
            return f"{self.action_type} action"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert action to dictionary."""
        return {
            "action_type": self.action_type,
            "slot": self.slot,
            "item_id": self.item_id,
            "target_slot": self.target_slot,
            "score": self.score
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EquipmentAction':
        """Create action from dictionary."""
        action = cls(
            action_type=data.get("action_type", "unknown"),
            slot=data.get("slot"),
            item_id=data.get("item_id")
        )
        action.target_slot = data.get("target_slot")
        action.score = data.get("score", 1.0)
        return action

class EquipmentState:
    """
    State representation for equipment AI decision-making using MCTS.
    
    This class represents the state of an equipment loadout for use in Monte Carlo Tree Search,
    including information about equipped items, available inventory, and possible actions.
    """
    
    def __init__(self, equipment_data: Dict[str, Any], world_data: Optional[Dict[str, Any]] = None):
        """
        Initialize equipment state.
        
        Args:
            equipment_data: Dictionary with equipment entity properties
            world_data: Dictionary with world state information
        """
        self.equipment_data = equipment_data
        self.world_data = world_data or {}
        self._legal_actions = None
        
        # Cache frequently used values for performance
        self.equipment_id = equipment_data.get("equipment_id")
        self.character_id = equipment_data.get("character_id")
        self.slots = equipment_data.get("slots", {})
        
        # Standard equipment slots
        self.standard_slots = {
            "head", "chest", "legs", "hands", "feet", "weapon", "shield"
        }
    
    def get_legal_actions(self) -> List[EquipmentAction]:
        """
        Get all legal actions in the current state.
        
        Returns:
            List of EquipmentAction objects representing possible actions
        """
        # Use cached actions if available
        if self._legal_actions is not None:
            return self._legal_actions
        
        actions = []
        
        # Get character's inventory items
        inventory_items = self._get_inventory_items()
        
        # For each empty slot, add equip actions for compatible items
        for slot in self.standard_slots:
            current_item_id = self.slots.get(slot)
            
            # If slot is empty, can equip compatible items
            if not current_item_id:
                compatible_items = self._get_compatible_items(slot, inventory_items)
                for item_id in compatible_items:
                    actions.append(EquipmentAction(
                        action_type="equip",
                        slot=slot,
                        item_id=item_id
                    ))
            # If slot is filled, can unequip
            else:
                actions.append(EquipmentAction(
                    action_type="unequip",
                    slot=slot,
                    item_id=current_item_id
                ))
                
                # Can also swap with compatible items
                compatible_items = self._get_compatible_items(slot, inventory_items)
                for item_id in compatible_items:
                    action = EquipmentAction(
                        action_type="swap",
                        slot=slot,
                        item_id=item_id
                    )
                    actions.append(action)
                
                # Can repair damaged items
                item_data = self._get_item_data(current_item_id)
                if item_data and item_data.get("durability", 100) < 75:
                    actions.append(EquipmentAction(
                        action_type="repair",
                        slot=slot,
                        item_id=current_item_id
                    ))
        
        # Calculate action scores
        self._calculate_action_scores(actions)
        
        # Cache actions
        self._legal_actions = actions
        return actions
    
    def _get_inventory_items(self) -> List[Dict[str, Any]]:
        """
        Get all items in the character's inventory.
        
        Returns:
            List of item data dictionaries
        """
        inventory_items = []
        
        # Find character's inventory in world data
        characters = self.world_data.get("characters", {})
        if self.character_id in characters:
            character_data = characters[self.character_id]
            inventory_ids = character_data.get("inventory_items", [])
            
            # Get item data for each inventory item
            items = self.world_data.get("items", {})
            for item_id in inventory_ids:
                if item_id in items:
                    inventory_items.append(items[item_id])
        
        return inventory_items
    
    def _get_compatible_items(self, slot: str, inventory_items: List[Dict[str, Any]]) -> List[str]:
        """
        Get IDs of inventory items compatible with the given slot.
        
        Args:
            slot: Equipment slot to check compatibility for
            inventory_items: List of item data dictionaries
            
        Returns:
            List of compatible item IDs
        """
        compatible_item_ids = []
        
        for item in inventory_items:
            # Skip items that are not equippable
            if not item.get("is_equippable", False):
                continue
                
            # Check if item is compatible with this slot
            item_slot = item.get("slot_type")
            
            # Skip if already equipped
            if item.get("id") in self.slots.values():
                continue
                
            # Match slot types
            if (slot == "head" and item_slot == "head") or \
               (slot == "chest" and item_slot == "chest") or \
               (slot == "legs" and item_slot == "legs") or \
               (slot == "hands" and item_slot == "hands") or \
               (slot == "feet" and item_slot == "feet") or \
               (slot == "weapon" and item_slot == "weapon") or \
               (slot == "shield" and item_slot in ["shield", "offhand"]):
                compatible_item_ids.append(item.get("id"))
        
        return compatible_item_ids
    
    def _get_item_data(self, item_id: str) -> Optional[Dict[str, Any]]:
        """
        Get data for a specific item.
        
        Args:
            item_id: ID of the item to retrieve
            
        Returns:
            Item data dictionary or None if not found
        """
        items = self.world_data.get("items", {})
        return items.get(item_id)
    
    def _calculate_action_scores(self, actions: List[EquipmentAction]) -> None:
        """
        Calculate scores for each action based on equipment state and world context.
        
        Args:
            actions: List of actions to score
        """
        for action in actions:
            score = 1.0  # Base score
            
            if action.action_type == "equip":
                # Equipping depends on item quality
                item_data = self._get_item_data(action.item_id)
                if item_data:
                    quality = item_data.get("quality", 0)
                    durability = item_data.get("durability", 100)
                    
                    # Better items have higher scores
                    score = 0.5 + (quality / 100)
                    
                    # Adjust for durability
                    if durability < 50:
                        score *= (durability / 100)
            
            elif action.action_type == "unequip":
                # Unequipping depends on item quality/condition
                item_data = self._get_item_data(action.item_id)
                if item_data:
                    quality = item_data.get("quality", 0)
                    durability = item_data.get("durability", 100)
                    
                    # Unequipping low quality or damaged items is more attractive
                    score = 1.0 - (quality / 200) + ((100 - durability) / 200)
            
            elif action.action_type == "swap":
                # Swapping depends on relative quality
                current_item_data = self._get_item_data(action.item_id)
                new_item_data = self._get_item_data(action.item_id)
                
                if current_item_data and new_item_data:
                    current_quality = current_item_data.get("quality", 0)
                    new_quality = new_item_data.get("quality", 0)
                    
                    # Quality difference affects score
                    quality_diff = new_quality - current_quality
                    score = 0.5 + (quality_diff / 100)
            
            elif action.action_type == "repair":
                # Repair depends on item quality and durability
                item_data = self._get_item_data(action.item_id)
                if item_data:
                    quality = item_data.get("quality", 0)
                    durability = item_data.get("durability", 100)
                    
                    # Higher quality items with low durability are worth repairing
                    score = 0.3 + (quality / 100) * ((100 - durability) / 100)
            
            action.score = max(0.1, score)  # Ensure score is positive
    
    def apply_action(self, action: EquipmentAction) -> 'EquipmentState':
        """
        Apply an action to this state and return the new state.
        
        Args:
            action: The action to apply
            
        Returns:
            A new EquipmentState resulting from the action
        """
        # Create a deep copy of the current state
        new_equipment_data = copy.deepcopy(self.equipment_data)
        new_state = EquipmentState(new_equipment_data, copy.deepcopy(self.world_data))
        
        # Apply the action effect based on type
        if action.action_type == "equip":
            # Equip item to slot
            new_state.equipment_data["slots"][action.slot] = action.item_id
            new_state.slots[action.slot] = action.item_id
            
            # Update item in world data
            if "items" in new_state.world_data and action.item_id in new_state.world_data["items"]:
                new_state.world_data["items"][action.item_id]["is_equipped"] = True
                
                # Each equip reduces durability slightly
                current_durability = new_state.world_data["items"][action.item_id].get("durability", 100)
                new_state.world_data["items"][action.item_id]["durability"] = max(0, current_durability - 1)
            
        elif action.action_type == "unequip":
            # Clear the slot
            new_state.equipment_data["slots"][action.slot] = None
            new_state.slots[action.slot] = None
            
            # Update item in world data
            if "items" in new_state.world_data and action.item_id in new_state.world_data["items"]:
                new_state.world_data["items"][action.item_id]["is_equipped"] = False
            
        elif action.action_type == "swap":
            # Get current item in slot
            current_item_id = new_state.equipment_data["slots"][action.slot]
            
            # Swap items
            new_state.equipment_data["slots"][action.slot] = action.item_id
            new_state.slots[action.slot] = action.item_id
            
            # Update both items in world data
            if "items" in new_state.world_data:
                if current_item_id in new_state.world_data["items"]:
                    new_state.world_data["items"][current_item_id]["is_equipped"] = False
                    
                if action.item_id in new_state.world_data["items"]:
                    new_state.world_data["items"][action.item_id]["is_equipped"] = True
                    
                    # Equipping reduces durability slightly
                    current_durability = new_state.world_data["items"][action.item_id].get("durability", 100)
                    new_state.world_data["items"][action.item_id]["durability"] = max(0, current_durability - 1)
            
        elif action.action_type == "repair":
            # Repair the item (increase durability)
            if "items" in new_state.world_data and action.item_id in new_state.world_data["items"]:
                current_durability = new_state.world_data["items"][action.item_id].get("durability", 100)
                repair_amount = min(100 - current_durability, 25)  # Repair up to 25 points
                new_state.world_data["items"][action.item_id]["durability"] = current_durability + repair_amount
        
        # Clear cached actions
        new_state._legal_actions = None
        
        return new_state
    
    def is_terminal(self) -> bool:
        """
        Check if this is a terminal state (simulation should end).
        
        Returns:
            True if terminal, False otherwise
        """
        # For equipment, terminal states could be:
        # 1. All slots filled with high-quality items
        # 2. No suitable items left to equip
        # 3. Simulation time limit reached (handled by MCTS)
        
        # Count equipped slots with good items
        good_equipment_count = 0
        for slot, item_id in self.slots.items():
            if item_id:
                item_data = self._get_item_data(item_id)
                if item_data and item_data.get("quality", 0) >= 75 and item_data.get("durability", 0) >= 75:
                    good_equipment_count += 1
        
        # Terminal if all standard slots have good equipment
        if good_equipment_count >= len(self.standard_slots):
            return True
            
        # Also terminal if no actions available
        return len(self.get_legal_actions()) == 0
    
    def get_reward(self) -> float:
        """
        Calculate reward value for this state.
        
        Returns:
            Float reward value (higher is better)
        """
        reward = 0.0
        
        # Base reward for each equipped item
        for slot, item_id in self.slots.items():
            if not item_id:
                continue
                
            # Get item details
            item_data = self._get_item_data(item_id)
            if not item_data:
                continue
                
            # Calculate item contribution to reward
            quality = item_data.get("quality", 0)
            durability = item_data.get("durability", 100)
            value = item_data.get("value", 0)
            
            # Better items give more reward
            item_reward = (quality / 100) * 5.0
            
            # Durability affects reward
            item_reward *= (durability / 100)
            
            # Value provides a small bonus
            item_reward += (value / 100)
            
            # Different slots may have different importance
            slot_multiplier = 1.0
            if slot == "weapon":
                slot_multiplier = 1.5  # Weapons are more important
            elif slot == "chest":
                slot_multiplier = 1.3  # Chest armor is important
            
            reward += item_reward * slot_multiplier
        
        # Bonus for complete sets of equipment
        equipped_count = sum(1 for item_id in self.slots.values() if item_id)
        if equipped_count >= len(self.standard_slots):
            reward += 10.0  # Big bonus for full equipment
        elif equipped_count >= len(self.standard_slots) * 0.7:
            reward += 5.0  # Medium bonus for mostly equipped
            
        # Bonus for matching equipment
        equipment_types = []
        for slot, item_id in self.slots.items():
            if item_id:
                item_data = self._get_item_data(item_id)
                if item_data:
                    equipment_types.append(item_data.get("equipment_type", "unknown"))
        
        # Count most common type
        type_counts = {}
        for e_type in equipment_types:
            if e_type not in type_counts:
                type_counts[e_type] = 0
            type_counts[e_type] += 1
            
        max_matching = max(type_counts.values()) if type_counts else 0
        if max_matching >= 3:  # At least 3 matching pieces
            reward += max_matching * 2.0  # Reward for matching set
        
        return reward
    
    def __str__(self) -> str:
        """String representation of the state."""
        equipped_count = sum(1 for item_id in self.slots.values() if item_id)
        return f"Equipment for {self.character_id}: {equipped_count}/{len(self.standard_slots)} slots filled"
        
    @classmethod
    def from_equipment_entity(cls, equipment, world_info=None):
        """
        Create an EquipmentState from an Equipment entity.
        
        Args:
            equipment: The equipment entity
            world_info: Optional world information
            
        Returns:
            EquipmentState: A new state object representing the equipment
        """
        # Convert equipment entity to data dictionary
        equipment_data = equipment.to_dict() if hasattr(equipment, 'to_dict') else {}
        
        # If to_dict isn't available, get properties directly
        if not equipment_data and hasattr(equipment, 'character_id'):
            equipment_data = {
                "equipment_id": equipment.equipment_id,
                "character_id": equipment.character_id,
                "slots": equipment.slots
            }
            
        return cls(equipment_data, world_info or {})