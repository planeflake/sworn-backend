from typing import List, Dict, Optional, Any
import logging
import json

logger = logging.getLogger(__name__)

class Item:
    """
    Item entity class representing game items like weapons, armor, potions, etc.
    
    Items have:
    1. A unique identifier
    2. Properties relevant to the item type
    3. Methods for item behaviors
    4. Serialization/deserialization methods for persistence
    5. State tracking to know when it needs to be saved
    """
    
    def __init__(self, item_id: str):
        """
        Initialize an item with a unique ID.
        
        Args:
            item_id (str): Unique identifier for this item
        """
        self.item_id = item_id
        self.properties = {}  # Dictionary to store all properties
        self._dirty = False
        
        # Set default values through properties
        self.set_property("name", None)
        self.set_property("description", None)
        self.set_property("is_quest_item", False)
        self.set_property("is_equippable", False)
        self.set_property("is_consumable", False)
        self.set_property("is_stackable", False)
        self.set_property("is_unique", False)
        self.set_property("durability", 100)  # Default durability
    
    def set_basic_info(self, name: str, description: Optional[str] = None, is_quest_item: bool = False, 
                       is_equippable: bool = False, is_consumable: bool = False, 
                       is_stackable: bool = False, is_unique: bool = False):
        """
        Set basic information about the item.
        
        Args:
            name (str): The item's name
            description (str, optional): A brief description of the item
            is_quest_item (bool): Whether the item is a quest item
            is_equippable (bool): Whether the item can be equipped
            is_consumable (bool): Whether the item can be consumed
            is_stackable (bool): Whether the item can be stacked
            is_unique (bool): Whether the item is unique
        """
        self.set_property("name", name)
        self.set_property("description", description or f"A {self.__class__.__name__.lower()} named {name}")
        self.set_property("is_quest_item", is_quest_item)
        self.set_property("is_equippable", is_equippable)
        self.set_property("is_consumable", is_consumable)
        self.set_property("is_stackable", is_stackable)
        self.set_property("is_unique", is_unique)
        
        logger.info(f"Set basic info for {self.__class__.__name__} {self.item_id}: name={name}")
    
    def set_property(self, key: str, value: Any):
        """
        Set a property value.
        
        Args:
            key (str): The property name
            value (Any): The property value
        """
        self.properties[key] = value
        self._dirty = True
    
    def get_property(self, key: str, default: Any = None) -> Any:
        """
        Get a property value.
        
        Args:
            key (str): The property name
            default (Any, optional): Default value if property doesn't exist
            
        Returns:
            Any: The property value or default
        """
        return self.properties.get(key, default)
    
    def set_is_stolen(self, is_stolen: bool):
        """
        Set whether the item is stolen.
        
        Args:
            is_stolen (bool): Whether the item is stolen
        """
        self.set_property("is_stolen", is_stolen)
        logger.info(f"Set is_stolen={is_stolen} for {self.__class__.__name__} {self.item_id}")
    
    def set_durability(self, durability: int):
        """
        Set the durability of the item.
        
        Args:
            durability (int): The durability of the item
        """
        self.set_property("durability", durability)
        logger.info(f"Set durability={durability} for {self.__class__.__name__} {self.item_id}")

    def is_broken(self) -> bool:
        """
        Check if the item is broken.
        
        Returns:
            bool: True if the item is broken
        """
        durability = self.get_property("durability", 0)
        logger.info(f"Checking if {self.__class__.__name__} {self.item_id} is broken")
        return durability <= 0
    
    # State tracking methods
    def is_dirty(self) -> bool:
        """
        Check if this entity has unsaved changes.
        
        Returns:
            bool: True if there are unsaved changes
        """
        return self._dirty
    
    def mark_clean(self):
        """Mark this entity as having no unsaved changes."""
        self._dirty = False
    
    # Serialization methods
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert entity to dictionary for storage.
        
        Returns:
            Dict[str, Any]: Dictionary representation of this entity
        """
        return {
            "item_id": self.item_id,
            "properties": self.properties
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Item':
        """
        Create entity from dictionary data.
        
        Args:
            data (Dict[str, Any]): Dictionary data to create entity from
            
        Returns:
            Item: New item instance
        """
        item = cls(item_id=data["item_id"])
        item.properties = data.get("properties", {})
        return item