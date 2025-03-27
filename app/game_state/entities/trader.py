"""
Trader entity module for the game state.

This module defines the Trader entity class that represents traders in the game world.
Traders travel between settlements, buy and sell goods, offer quests, and interact with players.

Additional functions to consider adding:
- set_trader_type() - Assign a specific type/personality to the trader
- set_inventory_capacity() - Set max carrying capacity
- add_trade_route() - Define a regular trade route for the trader 
- set_reputation_with_faction() - Set reputation with a specific faction
- add_home_settlement() - Set a home base for the trader
- settle_down() - Convert a traveling trader to a permanent merchant
- retire() - End the trader's career with accumulated wealth
- update_prices() - Update buying/selling prices based on market conditions
- get_trade_history() - Get history of past trades
- learn_secret() - Learn a secret about a location or other entity
- reveal_secret() - Share a secret with a player
"""

from typing import Dict, Any, List, Optional
import logging
import json
import uuid

logger = logging.getLogger(__name__)

class Trader:
    """
    Represents a trader entity in the game world.
    
    Traders travel between settlements, buy and sell goods, and interact
    with players and other NPCs. They have inventories, preferences for
    locations, and can offer quests.
    """
    
    def __init__(self, trader_id: str):
        """
        Initialize a Trader object with the given ID.
        
        Args:
            trader_id (str): Unique identifier for this trader
        """
        self.trader_id = trader_id
        
        # Properties dictionary for standardized access
        self.properties = {
            # Basic information
            "name": None,
            "description": None,
            "trader_type": "merchant",  # merchant, peddler, smuggler, etc.
            
            # Location
            "current_location_id": None,
            "destination_id": None,
            "home_settlement_id": None,
            "preferred_biomes": [],
            "preferred_settlements": [],
            "unacceptable_settlements": [],
            "visited_settlements": [],
            
            # Reputation and relations
            "faction_id": None,
            "reputation": {},  # settlement_id -> reputation value
            "relations": {},   # entity_id -> relation value
            
            # Resources and inventory
            "gold": 0,
            "inventory": {},   # item_id -> quantity
            "inventory_capacity": 100,
            
            # Trade data
            "buy_prices": {},  # item_id -> price multiplier
            "sell_prices": {}, # item_id -> price multiplier
            "trade_priorities": {}, # item_id -> priority value
            "trade_routes": [], # List of settlement IDs forming routes
            
            # Status flags
            "is_traveling": False,
            "is_settled": False,
            "is_retired": False,
            "has_shop": False,
            "shop_location_id": None,
            "can_move": True,              # Whether trader is allowed to move (tasks may block movement)
            "active_task_id": None,        # ID of active task that may be affecting the trader
            
            # Character traits
            "traits": [],
            "skills": {},
            "life_goals": [],
            
            # Quest data
            "available_quests": [],
            "locked_quests": [],
            "completed_quests": [],
            
            # Secret knowledge
            "known_secrets": []
        }
        
        # State tracking
        self._dirty = False
    
    def get_property(self, key: str, default: Any = None) -> Any:
        """
        Get a property value from the properties dictionary.
        
        Args:
            key (str): The property name
            default (Any, optional): Default value if property doesn't exist
            
        Returns:
            Any: The property value or default
        """
        return self.properties.get(key, default)
    
    def set_property(self, key: str, value: Any) -> None:
        """
        Set a property value in the properties dictionary.
        
        Args:
            key (str): The property name
            value (Any): The property value
        """
        self.properties[key] = value
        self._dirty = True
        logger.info(f"Set property {key} for trader {self.trader_id}")
    
    def set_relation(self, entity_id: str, relation_type: str, value: Any) -> None:
        """
        Set a relation with another entity.
        
        Args:
            entity_id (str): ID of the related entity
            relation_type (str): Type of relation (faction, settlement, etc.)
            value (Any): Value of the relation
        """
        relations = self.get_property("relations", {})
        if relation_type not in relations:
            relations[relation_type] = {}
        
        relations[relation_type][entity_id] = value
        self.set_property("relations", relations)
        logger.info(f"Set {relation_type} relation with {entity_id} for trader {self.trader_id}")
    
    def get_relation(self, entity_id: str, relation_type: str, default: Any = None) -> Any:
        """
        Get a relation value with another entity.
        
        Args:
            entity_id (str): ID of the related entity
            relation_type (str): Type of relation (faction, settlement, etc.)
            default (Any, optional): Default value if relation doesn't exist
            
        Returns:
            Any: The relation value or default
        """
        relations = self.get_property("relations", {})
        type_relations = relations.get(relation_type, {})
        return type_relations.get(entity_id, default)
    
    # Convenient shorthand methods for common operations
    
    def set_basic_info(self, name: str, description: Optional[str] = None) -> None:
        """
        Set basic information about the trader.
        
        Args:
            name (str): The trader's name
            description (str, optional): A brief description of the trader
        """
        self.set_property("name", name)
        self.set_property("description", description or f"A trader named {name}")
    
    def set_location(self, location_id: Optional[str], location_type: str = "current") -> None:
        """
        Set a location for the trader.
        
        Args:
            location_id (Optional[str]): The ID of the location
            location_type (str): Type of location (current, destination, home)
        """
        if location_type == "current":
            self.set_property("current_location_id", location_id)
            
            # Add to visited settlements if not already there
            if location_id:
                visited = self.get_property("visited_settlements", [])
                if location_id not in visited:
                    visited.append(location_id)
                    self.set_property("visited_settlements", visited)
                    
        elif location_type == "destination":
            self.set_property("destination_id", location_id)
        elif location_type == "home":
            self.set_property("home_settlement_id", location_id)
        else:
            raise ValueError(f"Invalid location type: {location_type}")
    
    def add_resource(self, resource_id: str, amount: int) -> None:
        """
        Add a resource to the trader's inventory.
        
        Args:
            resource_id (str): The ID of the resource
            amount (int): The quantity to add
        """
        if resource_id == "gold":
            current_gold = self.get_property("gold", 0)
            self.set_property("gold", current_gold + amount)
        else:
            inventory = self.get_property("inventory", {})
            current_amount = inventory.get(resource_id, 0)
            inventory[resource_id] = current_amount + amount
            self.set_property("inventory", inventory)
    
    def remove_resource(self, resource_id: str, amount: int) -> bool:
        """
        Remove a resource from the trader's inventory.
        
        Args:
            resource_id (str): The ID of the resource
            amount (int): The quantity to remove
            
        Returns:
            bool: True if resource was removed, False if insufficient quantity
        """
        if resource_id == "gold":
            current_gold = self.get_property("gold", 0)
            if current_gold < amount:
                return False
            self.set_property("gold", current_gold - amount)
            return True
        else:
            inventory = self.get_property("inventory", {})
            current_amount = inventory.get(resource_id, 0)
            
            if current_amount < amount:
                return False
                
            inventory[resource_id] = current_amount - amount
            if inventory[resource_id] <= 0:
                del inventory[resource_id]
                
            self.set_property("inventory", inventory)
            return True
    
    def add_quest(self, quest_id: str, quest_type: str = "available") -> None:
        """
        Add a quest to the trader.
        
        Args:
            quest_id (str): The ID of the quest
            quest_type (str): Quest type (available, locked, completed)
        """
        quests = self.get_property(f"{quest_type}_quests", [])
        if quest_id not in quests:
            quests.append(quest_id)
            self.set_property(f"{quest_type}_quests", quests)
    
    def complete_quest(self, quest_id: str) -> bool:
        """
        Mark a quest as completed.
        
        Args:
            quest_id (str): The ID of the quest
            
        Returns:
            bool: True if quest was completed, False otherwise
        """
        available_quests = self.get_property("available_quests", [])
        
        if quest_id not in available_quests:
            return False
            
        # Remove from available quests
        available_quests.remove(quest_id)
        self.set_property("available_quests", available_quests)
        
        # Add to completed quests
        completed_quests = self.get_property("completed_quests", [])
        if quest_id not in completed_quests:
            completed_quests.append(quest_id)
            self.set_property("completed_quests", completed_quests)
            
        return True
    
    def has_completed_quest(self, quest_id: str) -> bool:
        """
        Check if a quest has been completed.
        
        Args:
            quest_id (str): The ID of the quest
            
        Returns:
            bool: True if quest is completed, False otherwise
        """
        completed_quests = self.get_property("completed_quests", [])
        return quest_id in completed_quests
    
    def settle_down(self, settlement_id: str) -> None:
        """
        Have the trader settle down in a permanent location.
        
        Args:
            settlement_id (str): The ID of the settlement
        """
        self.set_property("is_settled", True)
        self.set_property("is_traveling", False)
        self.set_location(settlement_id, "current")
        self.set_location(None, "destination")
    
    def open_shop(self, settlement_id: str, shop_name: Optional[str] = None) -> None:
        """
        Have the trader open a permanent shop.
        
        Args:
            settlement_id (str): The ID of the settlement
            shop_name (Optional[str]): Name of the shop
        """
        self.set_property("has_shop", True)
        self.set_property("shop_location_id", settlement_id)
        
        if shop_name:
            self.set_property("shop_name", shop_name)
        else:
            trader_name = self.get_property("name", "Trader")
            self.set_property("shop_name", f"{trader_name}'s Shop")
            
        # Also settle down
        self.settle_down(settlement_id)
    
    def retire(self) -> None:
        """Have the trader retire from trading."""
        self.set_property("is_retired", True)
        self.set_property("is_traveling", False)
    
    # State tracking methods
    def is_dirty(self) -> bool:
        """
        Check if this trader has unsaved changes.
        
        Returns:
            bool: True if there are unsaved changes
        """
        return self._dirty
    
    def mark_clean(self) -> None:
        """Mark this trader as having no unsaved changes."""
        self._dirty = False
    
    # Serialization methods
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert trader to dictionary for storage.
        
        Returns:
            Dict[str, Any]: Dictionary representation of trader
        """
        return {
            "trader_id": self.trader_id,
            "properties": self.properties
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Trader':
        """
        Create trader from dictionary data.
        
        Args:
            data (Dict[str, Any]): Dictionary data to create from
            
        Returns:
            Trader: New trader instance
        """
        trader = cls(trader_id=data["trader_id"])
        trader.properties = data.get("properties", {})
        return trader
    
    def __str__(self) -> str:
        """String representation of the trader."""
        name = self.get_property("name", f"Trader {self.trader_id}")
        return f"{name} (Trader ID: {self.trader_id})"