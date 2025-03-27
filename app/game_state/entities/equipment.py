from typing import List, Dict, Optional, Any
from app.models.item import Item
import logging
import json

logger = logging.getLogger(__name__)

class Equipment:
    """
    Represents the equipment of a player.
    This includes items that the player is wearing or wielding.
    """
    def __init__(self, character_id: str):
        """
        Initialize the equipment loadout for a character.
        
        Args:
            character_id (str): ID of the character this equipment belongs to
        """
        self.character_id = character_id
        self.equipment_id = f"eq_{character_id}"  # Equipment ID derived from character
        self.slots = {
            "head": None,
            "chest": None,
            "legs": None,
            "hands": None,
            "feet": None,
            "weapon": None,
            "shield": None
        }
        self._dirty = False
        logger.info(f"Equipment loadout initialized for character: {character_id}")

    def get_equipped_items(self):
        """
        Get a list of all equipped items.
        
        Returns:
            List[Item]: A list of all equipped items across all equipment slots.
            Empty slots (None values) are excluded from the returned list.
        """
        return [item for item in self.items.values() if item is not None]
    
    def equip_item(self, slot: str, item: Item) -> bool:
        """
        Equip an item in the specified slot.
        
        Args:
            slot (str): Equipment slot to use
            item (Item): Item to equip
            
        Returns:
            bool: True if successful, False otherwise
        """
        if slot not in self.slots:
            logger.warning(f"Invalid equipment slot: {slot}")
            return False
            
        if not item.is_equippable:
            logger.warning(f"Item {item.name} is not equippable")
            return False
            
        self.slots[slot] = item.item_id
        self._dirty = True
        logger.info(f"Equipped {item.name} in {slot} slot for character {self.character_id}")
        return True
        
    def unequip_item(self, slot: str) -> Optional[str]:
        """
        Unequip an item from the specified slot.
        
        Args:
            slot (str): Equipment slot to unequip
            
        Returns:
            Optional[str]: Item ID of the unequipped item, or None if no item was equipped
        """
        if slot not in self.slots:
            logger.warning(f"Invalid equipment slot: {slot}")
            return None
            
        item_id = self.slots[slot]
        if not item_id:
            logger.info(f"No item equipped in {slot} slot")
            return None
            
        self.slots[slot] = None
        self._dirty = True
        logger.info(f"Unequipped item from {slot} slot for character {self.character_id}")
        return item_id
        
    def is_slot_equipped(self, slot: str) -> bool:
        """
        Check if a slot has an item equipped.
        
        Args:
            slot (str): Equipment slot to check
            
        Returns:
            bool: True if an item is equipped, False otherwise
        """
        if slot not in self.slots:
            return False
        return self.slots[slot] is not None
        
    def get_equipped_item_ids(self) -> Dict[str, str]:
        """
        Get all equipped item IDs by slot.
        
        Returns:
            Dict[str, str]: Dictionary mapping slots to item IDs
        """
        return {slot: item_id for slot, item_id in self.slots.items() if item_id is not None}
    
    # Serialization methods
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for storage.
        
        Returns:
            Dict[str, Any]: Dictionary representation
        """
        return {
            "equipment_id": self.equipment_id,
            "character_id": self.character_id,
            "slots": self.slots
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Equipment':
        """
        Create from dictionary data.
        
        Args:
            data (Dict[str, Any]): Dictionary data
            
        Returns:
            Equipment: New equipment instance
        """
        equipment = cls(character_id=data["character_id"])
        equipment.equipment_id = data.get("equipment_id", f"eq_{data['character_id']}")
        equipment.slots = data.get("slots", {})
        return equipment