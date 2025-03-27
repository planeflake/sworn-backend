import logging
import json
from typing import List, Dict, Optional, Any
import random

logger = logging.getLogger(__name__)

class Building:
    """
    Building entity representing structures in the game world.
    
    Buildings have:
    1. A unique identifier
    2. Properties relevant to the building type
    3. Methods for building behaviors
    4. Serialization/deserialization methods for persistence
    5. State tracking to know when it needs to be saved
    """
    
    def __init__(self, building_id: str):
        """
        Initialize a building with a unique ID.
        
        Args:
            building_id (str): Unique identifier for this building
        """
        self.building_id = building_id
        self.properties = {}  # Dictionary to store all properties
        self._dirty = False
        
        # Initialize properties dictionary
        self.set_property("name", None)
        self.set_property("description", None)
        self.set_property("location_id", None)
        self.set_property("inhabitants", {})
        self.set_property("relations", {})
    
    def set_basic_info(self, name: str, description: Optional[str] = None):
        """
        Set basic information about the building.
        
        Args:
            name (str): The building's name
            description (str, optional): A brief description of the building
        """
        self.set_property("name", name)
        self.set_property("description", description or f"A {self.__class__.__name__.lower()} named {name}")
        logger.info(f"Set basic info for {self.__class__.__name__} {self.building_id}: name={name}")
    
    def set_location(self, location_id: Optional[str]):
        """
        Set the current location of the building.
        
        Args:
            location_id (str, optional): The ID of the location, or None
        """
        self.set_property("location_id", location_id)
        logger.info(f"Set location for {self.__class__.__name__} {self.building_id} to {location_id}")
    
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
        logger.info(f"Set relation {relation_type} to entity {entity_id} for {self.__class__.__name__} {self.building_id}")
    
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
        inhabitants = self.get_property("inhabitants", {})
        return bool(inhabitants)
    
    def add_inhabitant(self, entity_id: str):
        """
        Add an entity as an inhabitant of the building.
        
        Args:
            entity_id (str): The ID of the entity to add
        """
        inhabitants = self.get_property("inhabitants", {})
        inhabitants[entity_id] = True
        self.set_property("inhabitants", inhabitants)
        logger.info(f"Added entity {entity_id} as an inhabitant of {self.__class__.__name__} {self.building_id}")

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
        if self.is_upgradeable():
            self.set_property("level", level)
            logger.info(f"Upgraded {self.__class__.__name__} {self.building_id} to level {level}")

    def repair(self, cost: int):
        """
        Repair the building and remove the 'needs_repair' status.
        
        Args:
            cost (int): The cost of repairing the building.
        """
        if self.needs_repairing():
            self.set_property("needs_repair", False)
            logger.info(f"Repaired {self.__class__.__name__} {self.building_id} at a cost of {cost}")

    def evict_inhabitant(self, entity_id: str):
        """
        Remove an inhabitant from the building.
        
        Args:
            entity_id (str): The ID of the entity to evict.
        """
        inhabitants = self.get_property("inhabitants", {})
        if entity_id in inhabitants:
            del inhabitants[entity_id]
            self.set_property("inhabitants", inhabitants)
            logger.info(f"Evicted entity {entity_id} from {self.__class__.__name__} {self.building_id}")

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
        logger.info(f"Assigned {self.__class__.__name__} {self.building_id} to faction {faction_id}")

    def discover(self):
        """
        Mark the building as discovered.
        """
        self.set_property("discovered", True)
        logger.info(f"{self.__class__.__name__} {self.building_id} has been discovered")

    def hide(self):
        """
        Hide the building from the player's view.
        """
        self.set_property("discovered", False)
        logger.info(f"{self.__class__.__name__} {self.building_id} has been hidden")

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
        logger.info(f"Event '{event}' occurred at {self.__class__.__name__} {self.building_id}")
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
        logger.info(f"Generated repair cost for {self.__class__.__name__} {self.building_id}: {repair_cost}")
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
            "building_id": self.building_id,
            "properties": self.properties
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Building':
        """
        Create entity from dictionary data.
        
        Args:
            data (Dict[str, Any]): Dictionary data to create entity from
            
        Returns:
            Building: New building instance
        """
        building = cls(building_id=data["building_id"])
        building.properties = data.get("properties", {})
        return building