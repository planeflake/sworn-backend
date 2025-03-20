import logging
import json
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

class Settlement:
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
    
    def __init__(self, entity_id: str):
        """
        Initialize an entity with a unique ID.
        
        Args:
            entity_id (str): Unique identifier for this entity
        """
        self.entity_id = entity_id
        
        # Basic information
        self.name = None
        self.description = None
        
        # Location
        self.location_id = None
        
        # Other state properties specific to this entity type
        self.properties = {}
        
        # Related entities
        self.relations = {}
        
        # Internal state tracking
        self._dirty = False  # Has this entity been modified since last save?
    
    def set_basic_info(self, name: str, description: Optional[str] = None):
        """
        Set basic information about the entity.
        
        Args:
            name (str): The entity's name
            description (str, optional): A brief description of the entity
        """
        self.name = name
        self.description = description or f"A {self.__class__.__name__.lower()} named {name}"
        self._dirty = True
        logger.info(f"Set basic info for {self.__class__.__name__} {self.entity_id}: name={name}")
    
    def set_location(self, location_id: Optional[str]):
        """
        Set the current location of the entity.
        
        Args:
            location_id (str, optional): The ID of the location, or None
        """
        self.location_id = location_id
        self._dirty = True
        logger.info(f"Set location for {self.__class__.__name__} {self.entity_id} to {location_id}")
    
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
    
    def set_relation(self, entity_id: str, relation_type: str, value: Any = None):
        """
        Set a relationship to another entity.
        
        Args:
            entity_id (str): The ID of the related entity
            relation_type (str): The type of relationship
            value (Any, optional): Optional value/strength of relationship
        """
        if entity_id not in self.relations:
            self.relations[entity_id] = {}
        
        self.relations[entity_id][relation_type] = value
        self._dirty = True
        logger.info(f"Set relation {relation_type} to entity {entity_id} for {self.__class__.__name__} {self.entity_id}")
    
    def get_relation(self, entity_id: str, relation_type: str, default: Any = None) -> Any:
        """
        Get a relationship value.
        
        Args:
            entity_id (str): The ID of the related entity
            relation_type (str): The type of relationship
            default (Any, optional): Default value if relation doesn't exist
            
        Returns:
            Any: The relation value or default
        """
        return self.relations.get(entity_id, {}).get(relation_type, default)

    ### Entity unique methods ###

    def is_under_repair(self) -> bool:
        """
        Check if the settlement is under repair.
        
        Returns:
            bool: True if the settlement is under repair
        """
        return self.get_property("is_under_repair", False)

    def set_is_repairable(self, is_repairable: bool):
        """
        Set whether the settlement is repairable.
        
        Args:
            is_repairable (bool): Whether the settlement is repairable
        """
        self.set_property("is_repairable", is_repairable)
        logger.info(f"Set is_repairable={is_repairable} for {self.__class__.__name__} {self.entity_id}")

    def set_is_damaged(self, is_damaged: bool):
        """
        Set whether the settlement is damaged.
        
        Args:
            is_damaged (bool): Whether the settlement is damaged
        """
        self.set_property("is_damaged", is_damaged)
        logger.info(f"Set is_damaged={is_damaged} for {self.__class__.__name__} {self.entity_id}")

    def set_has_started_building(self, has_started_building: bool):
        """
        Set whether the settlement has started building.
        
        Args:
            has_started_building (bool): Whether the settlement has started building
        """
        self.set_property("has_started_building", has_started_building)
        logger.info(f"Set has_started_building={has_started_building} for {self.__class__.__name__} {self.entity_id}")

    def is_built(self) -> bool:
        """
        Check if the settlement is built.
        
        Returns:
            bool: True if the settlement is built
        """
        return self.get_property("is_built", False)

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
            "entity_id": self.entity_id,
            "name": self.name,
            "description": self.description,
            "location_id": self.location_id,
            "properties": self.properties,
            "relations": self.relations
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Settlement':
        """
        Create entity from dictionary data.
        
        Args:
            data (Dict[str, Any]): Dictionary data to create entity from
            
        Returns:
            EntityTemplate: New entity instance
        """
        entity = cls(entity_id=data["entity_id"])
        entity.name = data.get("name")
        entity.description = data.get("description")
        entity.location_id = data.get("location_id")
        entity.properties = data.get("properties", {})
        entity.relations = data.get("relations", {})
        return entity