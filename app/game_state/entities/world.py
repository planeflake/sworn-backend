# Template for creating world classes in the game state architecture
# Copy this file to app/game_state/entities/ and customize for each world type

import logging
import json
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

class World:
    """
    World class for game entities.
    
    Entities represent game objects with state and behavior. They are the core
    objects that make up the game world (e.g., traders, settlements, animals).
    
    Each world should have:
    1. A unique identifier
    2. State properties relevant to its type
    3. Methods for its behaviors
    4. Serialization/deserialization methods for persistence
    5. State tracking to know when it needs to be saved
    """
    
    def __init__(self, world_id: str):
        """
        Initialize an world with a unique ID.
        
        Args:
            world_id (str): Unique identifier for this world
        """
        self.world_id = world_id
        
        # Basic information
        self.name = None
        self.description = None
        
        # Location
        self.location_id = None
        
        # Other state properties specific to this world type
        self.properties = {}
        
        # Related entities
        self.relations = {}
        
        # Internal state tracking
        self._dirty = False  # Has this world been modified since last save?
    
    def set_basic_info(self, name: str, description: Optional[str] = None):
        """
        Set basic information about the world.
        
        Args:
            name (str): The world's name
            description (str, optional): A brief description of the world
        """
        self.name = name
        self.description = description or f"A {self.__class__.__name__.lower()} named {name}"
        self._dirty = True
        logger.info(f"Set basic info for {self.__class__.__name__} {self.world_id}: name={name}")
    
    
    def add_location(self, key: str, value: Any):
        """
        Set a property value.
        
        Args:
            key (str): The property name
            value (Any): The property value
        """
        self.properties[key] = value
        self._dirty = True
        logger.info(f"Set property {key}={value} for {self.__class__.__name__} {self.world_id}")
    
    def remove_location(self, key: str):
        """
        Remove a property value.
        
        Args:
            key (str): The property name to remove
        """
        if key in self.properties:
            del self.properties[key]
            self._dirty = True
            logger.info(f"Removed property {key} for {self.__class__.__name__} {self.world_id}")
    
    def set_relation(self, world_id: str, relation_type: str, value: Any = None):
        """
        Set a relationship to another world.
        
        Args:
            world_id (str): The ID of the related world
            relation_type (str): The type of relationship
            value (Any, optional): Optional value/strength of relationship
        """
        if world_id not in self.relations:
            self.relations[world_id] = {}
        
        self.relations[world_id][relation_type] = value
        self._dirty = True
        logger.info(f"Set relation {relation_type} to world {world_id} for {self.__class__.__name__} {self.world_id}")
    
    def get_relation(self, world_id: str, relation_type: str, default: Any = None) -> Any:
        """
        Get a relationship value.
        
        Args:
            world_id (str): The ID of the related world
            relation_type (str): The type of relationship
            default (Any, optional): Default value if relation doesn't exist
            
        Returns:
            Any: The relation value or default
        """
        return self.relations.get(world_id, {}).get(relation_type, default)
    
    # State tracking methods
    def is_dirty(self) -> bool:
        """
        Check if this world has unsaved changes.
        
        Returns:
            bool: True if there are unsaved changes
        """
        return self._dirty
    
    def mark_clean(self):
        """Mark this world as having no unsaved changes."""
        self._dirty = False
    
    # Serialization methods
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert world to dictionary for storage.
        
        Returns:
            Dict[str, Any]: Dictionary representation of this world
        """
        return {
            "world_id": self.world_id,
            "name": self.name,
            "description": self.description,
            "location_id": self.location_id,
            "properties": self.properties,
            "relations": self.relations
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'World':
        """
        Create world from dictionary data.
        
        Args:
            data (Dict[str, Any]): Dictionary data to create world from
            
        Returns:
            worldTemplate: New world instance
        """
        world = cls(world_id=data["world_id"])
        world.name = data.get("name")
        world.description = data.get("description")
        world.location_id = data.get("location_id")
        world.properties = data.get("properties", {})
        world.relations = data.get("relations", {})
        return world