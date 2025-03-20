from typing import List, Dict, Optional, Any
import logging
import json

logger = logging.getLogger(__name__)

class Item:
    """
    Template class for game entities.
    
    Entities represent game objects with state and behavior. They are the core
    objects that make up the game world (e.g., traders, settlements, animals).
    
    Each entity should have:
    1. A unique identifier
    2. State properties relevant to its type
    3. Methods for its behaviors
    4. Serialization/deserialization methods for persistence
    5. State tracking to know when it needs to be saved
    """
    
    def __init__(self, item_id: str):
        """
        Initialize an entity with a unique ID.
        
        Args:
            entity_id (str): Unique identifier for this entity
        """
        self.item_id = item_id
        self.name = None
        self.description = None
        self.is_quest_item = False
        self.is_equippable = False
        self.is_consumable = False
        self.is_stackable = False
        self.is_unique = False
        self.durability = 100  # Default durability
        self.properties = {}
        self._dirty = False
    
    def set_basic_info(self, name: str, description: Optional[str] = None, is_quest_item: bool = False, is_equippable: bool = False, is_consumable: bool = False, is_stackable: bool = False, is_unique: bool = False):
        """
        Set basic information about the entity.
        
        Args:
            name (str): The entity's name
            description (str, optional): A brief description of the entity
            is_quest_item (bool): Whether the item is a quest item
            is_equippable (bool): Whether the item can be equipped
            is_consumable (bool): Whether the item can be consumed
            is_stackable (bool): Whether the item can be stacked
            is_unique (bool): Whether the item is unique
        """
        self.name = name
        self.description = description or f"A {self.__class__.__name__.lower()} named {name}"
        self.is_quest_item = False
        self.is_equippable = False
        self.is_consumable = False
        self.is_stackable = False
        self.is_unique = False
        self._dirty = True
        logger.info(f"Set basic info for {self.__class__.__name__} {self.entity_id}: name={name}")
    
    def set_property(self, key: str, value: Any):
        """
        Set a property value.
        
        Args:
            key (str): The property name
            value (Any): The property value
        """
        self.properties[key] = value
        self._dirty = True
        logger.info(f"Set property {key}={value} for {self.__class__.__name__} {self.entity_id}")
    
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
        self.is_stolen = is_stolen
        self._dirty = True
        logger.info(f"Set is_stolen={is_stolen} for {self.__class__.__name__} {self.entity_id}")
    
    def set_durability(self, durability: int):
        """
        Set the durability of the item.
        
        Args:
            durability (int): The durability of the item
        """
        self.durability = durability
        self._dirty = True
        logger.info(f"Set durability={durability} for {self.__class__.__name__}) {self.entity_id}")

    def is_broken(self) -> bool:
        """
        Check if the item is broken.
        
        Returns:
            bool: True if the item is broken
        """
        logger.info(f"Checking if {self.__class__.__name__} {self.entity_id} is broken")
        return self.durability <= 0
    
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
            "name": self.name,
            "description": self.description,
            "is_quest_item": self.is_quest_item,
            "is_equippable": self.is_equippable,
            "is_consumable": self.is_consumable,
            "is_stackable": self.is_stackable,
            "is_unique": self.is_unique,
            "durability": self.durability,
            "properties": self.properties,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Item':
        """
        Create entity from dictionary data.
        
        Args:
            data (Dict[str, Any]): Dictionary data to create entity from
            
        Returns:
            EntityTemplate: New entity instance
        """
        item = cls(item_id=data["item_id"])
        item.name = data.get("name")
        item.description = data.get("description")
        item.properties = data.get("properties", {})
        item.is_consumable = data.get("is_consumable", False)
        item.is_equippable = data.get("is_equippable", False)
        item.is_quest_item = data.get("is_quest_item", False)
        item.is_stackable = data.get("is_stackable", False)
        item.is_unique = data.get("is_unique", False)
        item.is_stolen = data.get("is_stolen", False)
        return item