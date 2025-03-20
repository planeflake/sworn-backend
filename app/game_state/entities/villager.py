from typing import Optional, Dict, List, Any
from uuid import UUID
import logging as logger

class Villager:
    """
    Villager class for game entities. This class represents a villager in the game world.
    """
    def __init__(self, villager_id: str):
        """
        Initialize a villager with a unique ID.
        
        Args:
            villager_id (str): Unique identifier for this villager
        """
        self.villager_id = villager_id
        
        # Basic information
        self.name = None
        self.description = None
        
        # Location
        self.location_id = None
        self.destination_id = None
        
        # Other state properties specific to this villager type
        self.properties = {}
        
        # Related entities
        self.relations = {}

        # Emotions and preferences
        self.emotions = []
        self.preferred_biome = None
        self.unacceptable_biomes = []
        
        # Tasks and skills
        self.tasks = []
        self.skills = {}

        # Internal state tracking
        self._dirty = False

    def set_basic_info(self, name: str, description: Optional[str] = None):
        """
        Set basic information about the villager.
        
        Args:
            name (str): The villager's name
            description (str, optional): A brief description of the villager
        """
        self.name = name
        self.description = description or f"A {self.__class__.__name__.lower()} named {name}"
        self._dirty = True
        logger.info(f"Set basic info for {self.__class__.__name__} {self.villager_id}: name={name}")

    def set_location(self, location_id: Optional[str], location_type: str = "current"):
        """
        Set the current or destination location of the villager.
        
        Args:
            location_id (str, optional): The ID of the location, or None
            location_type (str): Either "current" or "destination"
        """
        if location_type == "current":
            self.location_id = location_id
            logger.info(f"Set current location for {self.__class__.__name__} {self.villager_id} to {location_id}")
        elif location_type == "destination":
            self.destination_id = location_id
            logger.info(f"Set destination for {self.__class__.__name__} {self.villager_id} to {location_id}")
        else:
            raise ValueError(f"Invalid location type: {location_type}")
            
        self._dirty = True

    def set_property(self, key: str, value: Any):
        """
        Set a property value.
        
        Args:
            key (str): The property name
            value: The property value
        """
        self.properties[key] = value
        self._dirty = True
        logger.info(f"Set property for {self.__class__.__name__} {self.villager_id}: {key}={value}")

    def set_preferred_biome(self, biome: str):
        """
        Set the preferred biome for this villager.
        
        Args:
            biome (str): The biome ID
        """
        self.preferred_biome = biome
        self._dirty = True
        logger.info(f"Set preferred biome for {self.__class__.__name__} {self.villager_id} to {biome}")

    def add_unacceptable_biome(self, biome: str):
        """
        Add a biome to the list of unacceptable biomes.
        
        Args:
            biome (str): The biome ID
        """
        if biome not in self.unacceptable_biomes:
            self.unacceptable_biomes.append(biome)
            self._dirty = True
            logger.info(f"Added unacceptable biome for {self.__class__.__name__} {self.villager_id}: {biome}")

    def add_emotion(self, emotion: str):
        """
        Add an emotion to the villager.
        
        Args:
            emotion (str): The emotion ID
        """
        self.emotions.append(emotion)
        self._dirty = True
        logger.info(f"Added emotion for {self.__class__.__name__} {self.villager_id}: {emotion}")

    def set_skill(self, skill_name: str, level: int):
        """
        Set or improve a skill.
        
        Args:
            skill_name (str): The name of the skill
            level (int): The skill level
        """
        self.skills[skill_name] = level
        self._dirty = True
        logger.info(f"Set skill for {self.__class__.__name__} {self.villager_id}: {skill_name}={level}")

    def improve_skill(self, skill_name: str, amount: int = 1):
        """
        Improve an existing skill.
        
        Args:
            skill_name (str): The name of the skill
            amount (int): The amount to improve by
        """
        current_level = self.skills.get(skill_name, 0)
        self.skills[skill_name] = current_level + amount
        self._dirty = True
        logger.info(f"Improved skill for {self.__class__.__name__} {self.villager_id}: {skill_name}+{amount}")

    def add_task(self, task: str):
        """
        Add a task for the villager.
        
        Args:
            task (str): The task ID
        """
        self.tasks.append(task)
        self._dirty = True
        logger.info(f"Added task for {self.__class__.__name__} {self.villager_id}: {task}")

    def complete_task(self, task: str):
        """
        Mark a task as completed.
        
        Args:
            task (str): The task ID
            
        Returns:
            bool: True if task was found and removed, False otherwise
        """
        if task in self.tasks:
            self.tasks.remove(task)
            self._dirty = True
            logger.info(f"Completed task for {self.__class__.__name__} {self.villager_id}: {task}")
            return True
        return False
        
    # State tracking methods
    def is_dirty(self):
        """Check if this villager has unsaved changes."""
        return self._dirty
        
    def mark_clean(self):
        """Mark this villager as having no unsaved changes."""
        self._dirty = False

    # Serialization methods
    def to_dict(self) -> Dict[str, Any]:
        """Convert villager to dictionary for storage."""
        return {
            "villager_id": self.villager_id,
            "name": self.name,
            "description": self.description,
            "location_id": self.location_id,
            "destination_id": self.destination_id,
            "properties": self.properties,
            "relations": self.relations,
            "emotions": self.emotions,
            "preferred_biome": self.preferred_biome,
            "unacceptable_biomes": self.unacceptable_biomes,
            "tasks": self.tasks,
            "skills": self.skills
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create villager from dictionary data."""
        villager = cls(villager_id=data["villager_id"])
        villager.name = data.get("name")
        villager.description = data.get("description")
        villager.location_id = data.get("location_id")
        villager.destination_id = data.get("destination_id")
        villager.properties = data.get("properties", {})
        villager.relations = data.get("relations", {})
        villager.emotions = data.get("emotions", [])
        villager.preferred_biome = data.get("preferred_biome")
        villager.unacceptable_biomes = data.get("unacceptable_biomes", [])
        villager.tasks = data.get("tasks", [])
        villager.skills = data.get("skills", {})
        return villager