from app.game_state.states.trader_state import TraderState
from models.core import Worlds, Settlements, Traders
from app.game_state.mcts import MCTS
from sqlalchemy import text
from database import get_db

import logging as logger
import random as rand
import json

class Trader:
    def __init__(self, trader_id):
        """
        Initialize a Trader object with the given ID.
        
        The rest of the trader data should be loaded from the database.
        Don't create traders directly; use Traderanager.load_trader() instead.
        
        Args:
            trader_id (str): Unique identifier for this trader
        """
        self.trader_id = trader_id

        #Basic information
        self.name = None
        self.description = None

        #Location
        self.current_location_id = None
        self.destination_id = None
        self.preferred_biomes = []
        self.preferred_locations = []
        self.unacceptable_locations = []

        #Reputation
        self.reputation = []
        self.relations = {}

        #Resources
        self.resources = {}

        #Emotions
        self.emotions = {}
        self.life_goals = []

        #skills
        self.skills = {}

        #secrets
        self.secrets = []

        #Quest offerings
        self.available_quests = []
        self.locked_quests = []
        self.completed_quests = []

        #internal state tracking
        self._dirty = False

    def set_basic_info(self, name, description):
        """
        Set basic information about the trader.
        
        Args:
            name (str): The trader's name
            description (str): A brief description of the trader
        """
        self.name = name
        self.description = description
        self._dirty = True
        logger.info(f"Set basic info for trader {self.trader_id}: name={name}, description={description}")

    def set_location(self, location_id, type):
        """
        Set the current location of the trader.
        
        Args:
            location_id (str): The ID of the location
        """
        if type == "current":
            self.current_location_id = location_id
            logger.info(f"Set current location for trader {self.trader_id} to {location_id}")
        elif type == "destination":
            self.destination_id = location_id
            logger.info(f"Set destination for trader {self.trader_id} to {location_id}")
        else:
            logger.warning(f"Failed to set location for trader {self.trader_id}: Invalid location type {type}")
            raise ValueError(f"Invalid location type: {type}")
        self._dirty = True

    def add_resource(self, resource, amount):
        """
        Add a resource to the trader's inventory.
        
        Args:
            resource (str): The name of the resource
            amount (int): The quantity of the resource
        """
        if resource in self.resources:
            self.resources[resource] += amount
        else:
            self.resources[resource] = amount
        self._dirty = True
        logger.info(f"Added resource to trader {self.trader_id}: {amount} of {resource}")

    def remove_resource(self, resource, amount):
        """
        Remove a resource from the trader's inventory.
        
        Args:
            resource (str): The name of the resource
            amount (int): The quantity of the resource
        """
        if resource in self.resources:
            self.resources[resource] -= amount
            if self.resources[resource] <= 0:
                del self.resources[resource]
            self._dirty = True
            logger.info(f"Removed resource from trader {self.trader_id}: {amount} of {resource}")
        else:
            logger.warning(f"Failed to remove resource from trader {self.trader_id}: {resource} not found")

    def add_favourite_biome(self, biome_id):
        """
        Add a biome to the trader's list of favourite biomes.
        
        Args:
            biome_id (str): The ID of the biome
        """
        if(biome_id not in self.preferred_biomes):
            self.preferred_biomes.append(biome_id)
            self._dirty = True
            logger.info(f"Added favourite biome to trader {self.trader_id}: {biome_id}")

    def remove_favourite_biome(self, biome_id):
        """
        Remove a biome from the trader's favourites.
        
        Args:
            biome (str): The name of the biome to remove
        """
        if(self.preferred_biomes.count(biome_id) > 0):
            self.preferred_biomes.remove(biome_id)
            logger.info(f"Removed favourite biome from trader {self.trader_id}: {biome_id}")
            self._dirty = True

    def add_available_quest(self, quest_id):
        """
        Add a quest to the trader's available quest list.
        
        Args:
            quest_id (str): The ID of the quest
        """
        self.available_quests.append(quest_id)
        logger.info(f"Added available quest to trader {self.trader_id}: {quest_id}")
        self._dirty = True

    def complete_quest(self, quest_id):
        """
        Mark a quest as completed by this trader.
        Removes it from available quests and adds to completed quests.
        
        Args:
            quest_id (str): The ID of the completed quest
        
        Returns:
            bool: True if quest was marked complete, False if not found
        """
        if quest_id in self.available_quests:
            self.available_quests.remove(quest_id)
            
            if quest_id not in self.completed_quests:
                self.completed_quests.append(quest_id)
                logger.info(f"Completed quest for trader {self.trader_id}: {quest_id}")
            self._dirty = True
            return True
        return False

    def has_completed_quest(self, quest_id):
            """
            Check if this trader has completed a specific quest.
            
            Args:
                quest_id (str): The ID of the quest to check
                
            Returns:
                bool: True if the quest has been completed
            """
            return quest_id in self.completed_quests
            
    def remove_available_quest(self, quest_id):
        """
        Remove a quest from the trader's available quest list.
        
        Args:
            quest_id (str): The ID of the quest
        """
        self.available_quests.remove(quest_id)
        logger.info(f"Removed available quest from trader {self.trader_id}: {quest_id}")
        self._dirty = True

   # State tracking methods
    def is_dirty(self):
        """Check if this trader has unsaved changes."""
        return self._dirty
        
    def mark_clean(self):
        """Mark this trader as having no unsaved changes."""
        self._dirty = False

 # Serialization methods
    def to_dict(self):
        """Convert trader to dictionary for storage."""
        return {
            "trader_id": self.trader_id,
            "name": self.name,
            "description": self.description,
            "current_location_id": self.current_location_id,
            "destination_id": self.destination_id,
            "preferred_biomes": self.preferred_biomes,
            "preferred_locations": self.preferred_locations,
            "unacceptable_locations": self.unacceptable_locations,
            "reputation": self.reputation,
            "relations": self.relations,
            "resources": self.resources,
            "emotions": self.emotions,
            "life_goals": self.life_goals,
            "skills": self.skills,
            "secrets": self.secrets,
            "available_quests": self.available_quests,
            "locked_quests": self.locked_quests,
            "completed_quests": self.completed_quests
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create trader from dictionary data."""
        trader = cls(trader_id=data["trader_id"])
        trader.name = data.get("name")
        trader.description = data.get("description")
        trader.current_location_id = data.get("current_location_id")
        trader.destination_id = data.get("destination_id")
        trader.preferred_biomes = data.get("preferred_biomes", [])
        trader.preferred_locations = data.get("preferred_locations", [])
        trader.unacceptable_locations = data.get("unacceptable_locations", [])
        trader.reputation = data.get("reputation", [])
        trader.relations = data.get("relations", {})
        trader.resources = data.get("resources", {})
        trader.emotions = data.get("emotions", {})
        trader.life_goals = data.get("life_goals", [])
        trader.skills = data.get("skills", {})
        trader.secrets = data.get("secrets", [])
        trader.available_quests = data.get("available_quests", [])
        trader.locked_quests = data.get("locked_quests", [])
        trader.completed_quests = data.get("completed_quests", [])
        return trader