from app.ai.mcts.states.player_state import PlayerState
from app.models.core import Worlds, Settlements, Players
from app.game_state.mcts import MCTS
from sqlalchemy import text
from database import get_db
from typing import Dict, Any, List, Optional

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
        
        # Properties dictionary to store all player data
        self.properties = {}
        
        # Initialize properties dictionary with default values
        self.set_property("name", None)
        self.set_property("description", None)
        
        # Location
        self.set_property("current_location_id", None)
        self.set_property("destination_id", None)
        self.set_property("preferred_biomes", [])
        self.set_property("preferred_locations", [])
        self.set_property("unacceptable_locations", [])
        
        # Reputation
        self.set_property("reputation", {})
        self.set_property("relations", {})
        
        # Resources
        self.set_property("resources", {})
        
        # Emotions
        self.set_property("emotions", {})
        self.set_property("life_goals", [])
        
        # Skills
        self.set_property("skills", {})
        
        # Physical attributes
        self.set_property("physical_attributes", {})
        
        # Secrets
        self.set_property("secrets", [])
        
        # Quests
        self.set_property("completed_quests", [])
        
        # Internal state tracking
        self._dirty = False

    def set_property(self, key: str, value: Any) -> None:
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

    def set_basic_info(self, name: str, description: str, health: int, mana: int, stamina: int) -> None:
        """
        Set basic information about the player.
        
        Args:
            name (str): The player's name
            description (str): A description of the player
            health (int): Initial health value
            mana (int): Initial mana value
            stamina (int): Initial stamina value
        """
        self.set_property("name", name)
        self.set_property("description", description)
        self.set_property("health", health)
        self.set_property("mana", mana)
        self.set_property("stamina", stamina)

    def set_location(self, location_id: Optional[str]) -> None:
        """
        Set the current location of the player.
        
        Args:
            location_id (str): The ID of the location
        """
        self.set_property("current_location_id", location_id)

    def set_destination(self, destination_id: Optional[str]) -> None:
        """
        Set the destination of the player.
        
        Args:
            destination_id (str): The ID of the destination
        """
        self.set_property("destination_id", destination_id)

    def set_preferred_biomes(self, biomes: List[str]) -> None:
        """
        Set the preferred biomes for the player.
        
        Args:
            biomes (list): List of biome IDs
        """
        self.set_property("preferred_biomes", biomes)

    def get_preferred_biomes(self) -> List[str]:
        """
        Get the preferred biomes for the player.
        
        Returns:
            list: List of preferred biome IDs
        """
        return self.get_property("preferred_biomes", [])
    
    def set_preferred_locations(self, locations: List[str]) -> None:
        """
        Set the preferred locations for the player.
        
        Args:
            locations (list): List of location IDs
        """
        self.set_property("preferred_locations", locations)

    def get_preferred_locations(self) -> List[str]:
        """
        Get the preferred locations for the player.
        
        Returns:
            list: List of preferred location IDs
        """
        return self.get_property("preferred_locations", [])
    
    def set_unacceptable_locations(self, locations: List[str]) -> None:
        """
        Set the unacceptable locations for the player.
        
        Args:
            locations (list): List of location IDs
        """
        self.set_property("unacceptable_locations", locations)

    def get_unacceptable_locations(self) -> List[str]:
        """
        Get the unacceptable locations for the player.
        
        Returns:
            list: List of unacceptable location IDs
        """
        return self.get_property("unacceptable_locations", [])
    
    def change_reputation(self, reputation: str, faction: str, value: float) -> None:
        """
        Add or update a reputation value for a specific faction.
        
        Args:
            reputation (str): The reputation type to add/update
            faction (str): The faction to associate the reputation with
            value (int/float): The value to add (can be positive or negative)
        """
        # Get current reputation dictionary
        reputations = self.get_property("reputation", {})
        
        # Initialize the faction if it doesn't exist
        if faction not in reputations:
            reputations[faction] = {}
        
        # Check if this reputation type already exists for this faction
        if reputation in reputations[faction]:
            # Add the value to the existing reputation
            reputations[faction][reputation] += value
        else:
            # Set the initial value
            reputations[faction][reputation] = value
        
        # Update the property
        self.set_property("reputation", reputations)

    def gain_resource(self, resource: str, amount: int) -> None:
        """
        Add a resource to the player's inventory.
        
        Args:
            resource (str): The name of the resource
            amount (int): The quantity of the resource
        """
        resources = self.get_property("resources", {})
        
        if resource in resources:
            resources[resource] += amount
        else:
            resources[resource] = amount
            
        self.set_property("resources", resources)

    def lose_resource(self, resource: str, amount: int) -> bool:
        """
        Remove a resource from the player's inventory.
        
        Args:
            resource (str): The name of the resource
            amount (int): The quantity of the resource
            
        Returns:
            bool: True if resource was removed, False if insufficient quantity
        """
        resources = self.get_property("resources", {})
        
        if resource in resources:
            resources[resource] -= amount
            if resources[resource] <= 0:
                del resources[resource]
            self.set_property("resources", resources)
            return True
        else:
            logger.warning(f"Failed to remove resource from player {self.player_id}: {resource} not found")
            return False
    
    def learn_skill(self, skill: str, level: int) -> None:
        """
        Add or update a skill for the player.
        
        Args:
            skill (str): The name of the skill
            level (int): The level of the skill
        """
        skills = self.get_property("skills", {})
        skills[skill] = level
        self.set_property("skills", skills)

    def update_skill(self, skill: str, level: int) -> None:
        """
        Add or update a skill for the player.
        
        Args:
            skill (str): The name of the skill
            level (int): The level of the skill
        """
        self.learn_skill(skill, level)  # Use the existing method

    def set_physical_attribute(self, attribute: str, value: Any) -> None:
        """
        Set a physical attribute for the player.
        
        Args:
            attribute (str): The name of the attribute
            value (Any): The value of the attribute
        """
        attributes = self.get_property("physical_attributes", {})
        attributes[attribute] = value
        self.set_property("physical_attributes", attributes)

    # State tracking methods
    def is_dirty(self) -> bool:
        """
        Check if this player has unsaved changes.
        
        Returns:
            bool: True if there are unsaved changes
        """
        return self._dirty
        
    def mark_clean(self) -> None:
        """Mark this player as having no unsaved changes."""
        self._dirty = False

    # Serialization methods
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert player to dictionary for storage.
        
        Returns:
            Dict[str, Any]: Dictionary representation of this player
        """
        return {
            "player_id": self.player_id,
            "properties": self.properties
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Player':
        """
        Create player from dictionary data.
        
        Args:
            data (Dict[str, Any]): Dictionary data to create from
            
        Returns:
            Player: New player instance
        """
        player = cls(player_id=data["player_id"])
        if "properties" in data:
            player.properties = data["properties"]
        else:
            # Handle legacy format
            properties = {}
            for key, value in data.items():
                if key != "player_id":
                    properties[key] = value
            player.properties = properties
            
        return player