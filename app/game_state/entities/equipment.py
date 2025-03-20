from typing import List, Dict, Optional, Any
import logging
import json

logger = logging.getLogger(__name__)

class Item:
    """
    Base class for all items.
    """
    def __init__(self, name: str, item_type: str, stats: Optional[dict] = None):
        self.name = name
        self.item_type = item_type
        self.stats = stats or {}

class Equipment:
    """
    Represents the equipment of a player.
    This includes items that the player is wearing or wielding.
    """
    def __init__(self):
        """
        Initialize the equipment with empty slots for each equipment type.
        """
        self.items = {
            "head": None,
            "chest": None,
            "legs": None,
            "hands": None,
            "feet": None,
            "weapon": None,
            "shield": None
        }
        logger.info("Equipment initialized with empty slots.")

    def equip_item(self, slot: str, item: Item):
        """
        Equip an item in the specified slot.
        """
        if slot not in self.items:
            raise ValueError(f"Invalid equipment slot: {slot}")
        self.items[slot] = item
        logger.info(f"Equipped {item.name} in {slot} slot.")

    def unequip_item(self, slot: str):
        """
        Unequip an item from the specified slot.
        """
        if slot not in self.items:
            raise ValueError(f"Invalid equipment slot: {slot}")
        self.items[slot] = None
        logger.info(f"Unequipped item from {slot} slot.")

    def get_equipped_items(self):
        """
        Get a list of all equipped items.
        """
        return [item for item in self.items.values() if item is not None]