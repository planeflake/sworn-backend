from typing import List, Dict, Optional, Any
import logging
import json

logger = logging.getLogger(__name__)

class EntityTemplate:
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
        self.properties = {}  # Dictionary to store all properties
        self._dirty = False
        
        # Initialize properties dictionary with default values
        self.set_property("name", None)
        self.set_property("description", None)
        self.set_property("location_id", None)
        self.set_property("relations", {})
    
    def set_basic_info(self, name: str, description: Optional[str] = None):
        """
        Set basic information about the entity.
        
        Args:
            name (str): The entity's name
            description (str, optional): A brief description of the entity
        """
        self.set_property("name", name)
        self.set_property("description", description or f"A {self.__class__.__name__.lower()} named {name}")
        logger.info(f"Set basic info for {self.__class__.__name__} {self.entity_id}: name={name}")
    
    def set_location(self, location_id: Optional[str]):
        """
        Set the current location of the entity.
        
        Args:
            location_id (str, optional): The ID of the location, or None
        """
        self.set_property("location_id", location_id)
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
        relations = self.get_property("relations", {})
        if entity_id not in relations:
            relations[entity_id] = {}
        
        relations[entity_id][relation_type] = value
        self.set_property("relations", relations)
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
        relations = self.get_property("relations", {})
        return relations.get(entity_id, {}).get(relation_type, default)
    
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
            "properties": self.properties
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EntityTemplate':
        """
        Create entity from dictionary data.
        
        Args:
            data (Dict[str, Any]): Dictionary data to create entity from
            
        Returns:
            EntityTemplate: New entity instance
        """
        entity = cls(entity_id=data["entity_id"])
        entity.properties = data.get("properties", {})
        return entity