from app.game_state.states.player_state import PlayerState
from models.core import Worlds, Settlements, Players
from app.game_state.mcts import MCTS
from sqlalchemy import text
from database import get_db

import logging as logger
import random as rand
import json

class Player:
    def __init__(self, player_id):
        """
        Initialize a player object with the given ID.
        
        The rest of the player data should be loaded from the database.
        Don't create players directly; use playeranager.load_player() instead.
        
        Args:
            player_id (str): Unique identifier for this player
        """
        self.player_id = player_id

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

        #phsyical attributes
        self.physical_attributes = {}

        #secrets
        self.secrets = []

        #Quests
        self.completed_quests = []

        #internal state tracking
        self._dirty = False

    def set_basic_info(self, name, description, health, mana, stamina):
        """
        Set basic information about the player.
        
        Args:
            name (str): The player's name
            description (str): A description of the player
        """
        self.name = name
        self.description = description
        self.health = health
        self.mana = mana
        self.stamina = stamina
        self._dirty = True

    def set_location(self, location_id):
        """
        Set the current location of the player.
        
        Args:
            location_id (str): The ID of the location
        """
        self.current_location_id = location_id
        self._dirty = True

    def set_destination(self, destination_id):
        """
        Set the destination of the player.
        
        Args:
            destination_id (str): The ID of the destination
        """
        self.destination_id = destination_id
        self._dirty = True

    def set_preferred_biomes(self, biomes):
        """
        Set the preferred biomes for the player.
        
        Args:
            biomes (list): List of biome IDs
        """
        self.preferred_biomes = biomes
        self._dirty = True

    def get_prefered_biomes(self):
        return self.preferred_biomes
    
    def set_preferred_locations(self, locations):
        """
        Set the preferred locations for the player.
        
        Args:
            locations (list): List of location IDs
        """
        self.preferred_locations = locations
        self._dirty = True

    def get_prefered_locations(self):
        return self.preferred_locations
    
    def set_unacceptable_locations(self, locations):
        """
        Set the unacceptable locations for the player.
        
        Args:
            locations (list): List of location IDs
        """
        self.unacceptable_locations = locations
        self._dirty = True

    def get_unacceptable_locations(self):
        return self.unacceptable_locations
    
    def change_reputation(self, reputation, faction, value):
        """
        Add or update a reputation value for a specific faction.
        
        Args:
            reputation (str): The reputation type to add/update
            faction (str): The faction to associate the reputation with
            value (int/float): The value to add (can be positive or negative)
        """
        # Initialize the faction if it doesn't exist
        if faction not in self.reputation:
            self.reputation[faction] = {}
        
        # Check if this reputation type already exists for this faction
        if reputation in self.reputation[faction]:
            # Add the value to the existing reputation
            self.reputation[faction][reputation] += value
        else:
            # Set the initial value
            self.reputation[faction][reputation] = value
        
        self._dirty = True

    def gain_resource(self, resource, amount):
        """
        Add a resource to the player's inventory.
        
        Args:
            resource (str): The name of the resource
            amount (int): The quantity of the resource
        """
        if resource in self.resources:
            self.resources[resource] += amount
        else:
            self.resources[resource] = amount
        self._dirty = True

    def lose_resource(self, resource, amount):
        """
        Remove a resource from the player's inventory.
        
        Args:
            resource (str): The name of the resource
            amount (int): The quantity of the resource
        """
        if resource in self.resources:
            self.resources[resource] -= amount
            if self.resources[resource] <= 0:
                del self.resources[resource]
            self._dirty = True
        else:
            logger.warning(f"Failed to remove resource from player {self.player_id}: {resource} not found")
    
    def learn_skill(self, skill, level):
        """
        Add or update a skill for the player.
        
        Args:
            skill (str): The name of the skill
            level (int): The level of the skill
        """
        self.skills[skill] = level
        self._dirty = True

    def update_skill(self, skill, level):
        """
        Add or update a skill for the player.
        
        Args:
            skill (str): The name of the skill
            level (int): The level of the skill
        """
        self.skills[skill] = level
        self._dirty = True

    def set_physical_attribute(self, attribute, value):
        """
        Set a physical attribute for the player.
        
        Args:
            attribute (str): The name of the attribute
            value (int): The value of the attribute
        """

        self.physical_attributes[attribute] = value
        self._dirty = True

   # State tracking methods
    def is_dirty(self):
        """Check if this player has unsaved changes."""
        return self._dirty
        
    def mark_clean(self):
        """Mark this player as having no unsaved changes."""
        self._dirty = False

    # Serialization methods
    def to_dict(self):
        """Convert player to dictionary for storage."""
        return {
            "player_id": self.player_id,
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
            "completed_quests": self.completed_quests
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create player from dictionary data."""
        player = cls(player_id=data["player_id"])
        player.name = data.get("name")
        player.description = data.get("description")
        player.current_location_id = data.get("current_location_id")
        player.destination_id = data.get("destination_id")
        player.preferred_biomes = data.get("preferred_biomes", [])
        player.preferred_locations = data.get("preferred_locations", [])
        player.unacceptable_locations = data.get("unacceptable_locations", [])
        player.reputation = data.get("reputation", [])
        player.relations = data.get("relations", {})
        player.resources = data.get("resources", {})
        player.emotions = data.get("emotions", {})
        player.life_goals = data.get("life_goals", [])
        player.skills = data.get("skills", {})
        player.secrets = data.get("secrets", [])
        player.completed_quests = data.get("completed_quests", [])
        return player