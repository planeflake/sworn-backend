import logging
import json
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

class Building:
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
        self.inhabitants = {}
        
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
    
    ### Entity Specific Methods ###

    def is_under_construction(self) -> bool:
        """
        Check if the building is under construction.
        
        Returns:
            bool: True if the building is under construction
        """
        return self.get_property("under_construction", False)

    def is_built(self) -> bool:
        """
        Check if the building is fully constructed.
        
        Returns:
            bool: True if the building is fully constructed
        """
        return self.get_property("is_built", False)
    
    def is_faction_building(self, faction_id: str) -> bool:
        """
        Check if the building belongs to a specific faction.
        
        Args:
            faction_id (str): The ID of the faction to check
        
        Returns:
            bool: True if the building belongs to the faction
        """
        return self.get_property("faction_id") == faction_id
    
    def is_inhabited(self) -> bool:
        """
        Check if the building is inhabited.
        
        Returns:
            bool: True if the building is inhabited
        """
        return bool(self.inhabitants)
    
    def add_inhabitant(self, entity_id: str):
        """
        Add an entity as an inhabitant of the building.
        
        Args:
            entity_id (str): The ID of the entity to add
        """
        self.inhabitants[entity_id] = True
        self._dirty = True
        logger.info(f"Added entity {entity_id} as an inhabitant of {self.__class__.__name__} {self.entity_id}")

    def is_under_attack(self) -> bool:
        """
        Check if the building is under attack.
        
        Returns:
            bool: True if the building is under attack
        """
        return self.get_property("under_attack", False)

    def needs_repairing(self) -> bool:
        """
        Check if the building needs repairing.
        
        Returns:
            bool: True if the building needs repairing
        """
        return self.get_property("needs_repair", False)
    
    def is_taxed(self) -> bool:
        """
        Check if the building is taxed.
        
        Returns:
            bool: True if the building is taxed
        """
        return self.get_property("is_taxed", False)

    ### Utility Methods ###

def is_upgradeable(self) -> bool:
    """
    Check if the building is upgradeable.
    
    Returns:
        bool: True if the building is upgradeable
    """
    return self.get_property("is_upgradeable", False)

def upgrade_building(self, level: int):
    """
    Upgrade the building to a specified level.
    
    Args:
        level (int): The new level of the building.
    """
    if(self.is_upgradeable()):
        self.set_property("level", level)
        self._dirty = True
        logger.info(f"Upgraded {self.__class__.__name__} {self.entity_id} to level {level}")

def repair(self, cost: int):
    """
    Repair the building and remove the 'needs_repair' status.
    
    Args:
        cost (int): The cost of repairing the building.
    """
    if self.needs_repairing():
        self.set_property("needs_repair", False)
        self._dirty = True
        logger.info(f"Repaired {self.__class__.__name__} {self.entity_id} at a cost of {cost}")

def evict_inhabitant(self, entity_id: str):
    """
    Remove an inhabitant from the building.
    
    Args:
        entity_id (str): The ID of the entity to evict.
    """
    if entity_id in self.inhabitants:
        del self.inhabitants[entity_id]
        self._dirty = True
        logger.info(f"Evicted entity {entity_id} from {self.__class__.__name__} {self.entity_id}")

def collect_taxes(self) -> int:
    """
    Collect taxes from the building's inhabitants.
    
    Returns:
        int: The amount of taxes collected.
    """
    return self.get_property("tax_income", 0)

def assign_faction(self, faction_id: str):
    """
    Assign the building to a faction.
    
    Args:
        faction_id (str): The ID of the faction.
    """
    self.set_property("faction_id", faction_id)
    self._dirty = True
    logger.info(f"Assigned {self.__class__.__name__} {self.entity_id} to faction {faction_id}")

def discover(self):
    """
    Mark the building as discovered.
    """
    self.set_property("discovered", True)
    self._dirty = True
    logger.info(f"{self.__class__.__name__} {self.entity_id} has been discovered")

def hide(self):
    """
    Hide the building from the player's view.
    """
    self.set_property("discovered", False)
    self._dirty = True
    logger.info(f"{self.__class__.__name__} {self.entity_id} has been hidden")

def calculate_defense(self) -> int:
    """
    Calculate the building's defense value.
    
    Returns:
        int: The defense value.
    """
    return self.get_property("defense", 0)

def generate_event(self) -> str:
    """
    Trigger a random event related to the building.
    
    Returns:
        str: A description of the event.
    """
    events = ["fire", "festival", "attack", "earthquake"]
    event = random.choice(events)
    logger.info(f"Event '{event}' occurred at {self.__class__.__name__} {self.entity_id}")
    return event

def generate_repair_costs(self) -> int:
    """
    Generate the repair cost for the building based on its properties.
    
    Returns:
        int: The cost to repair the building
    """
    base_cost = self.get_property("repair_base_cost", 100)
    damage_level = self.get_property("damage_level", 0)  # Assume damage level is a percentage (0-100)
    repair_cost = int(base_cost * (damage_level / 100))
    logger.info(f"Generated repair cost for {self.__class__.__name__} {self.entity_id}: {repair_cost}")
    return repair_cost

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
    def from_dict(cls, data: Dict[str, Any]) -> 'Building':
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