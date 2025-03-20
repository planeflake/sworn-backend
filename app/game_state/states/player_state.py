from app.game_state.mcts import MCTS
import logging as logger


class PlayerState:
    """
    Represents the state of a player in the game.
    This includes their current health, mana, stamina, inventory, and equipment.
    """
    def __init__(self, player):
        self.name = player
        self.health = 100
        self.mana = 100
        self.stamina = 100
        self.inventory = self.Inventory()
        self.equipment = self.Equipment()
        logger.info(f"PlayerState created for {self.player.name}")

    def Inventory(self):
        """
        Represents the inventory of a player.
        This includes items that the player is carrying.
        """
        def __init__(self):
            self.items = []
            self.capacity = 20
            logger.info(f"Inventory created for {self.player.name}")

    def Equipment(self):
        """
        Represents the equipment of a player.
        This includes items that the player is wearing or wielding.
        """
        def __init__(self):
            self.items = {
                "head": None,
                "chest": None,
                "legs": None,
                "hands": None,
                "feet": None,
                "weapon": None,
                "shield": None
            }
            logger.info(f"Equipment created for {self.player.name}")

    def __str__(self):
        return f"{self.player.name} - Health: {self.health}, Mana: {self.mana}, Stamina: {self.stamina}"
    
        ### MCTS-specific methods ###

    def apply_action(self, action):
        """
        Apply an action to this state and return the new state.
        
        Args:
            action: The action to apply
            
        Returns:
            playerState: A new state resulting from the action
        """
        # Create a copy of this state
        new_state = self.clone()
        
        # Apply the action based on its type
        if action["type"] == "move":
            new_state.faction.set_location(action["location_id"], "current")
            # Clear destination if we've reached it
            if new_state.faction.destination_id == action["location_id"]:
                new_state.faction.set_location(None, "destination")
                
        elif action["type"] == "buy":
            # Deduct gold
            new_state.faction.remove_resource("gold", action["price"])
            # Add purchased item
            new_state.faction.add_resource(action["item"], 1)
            
        elif action["type"] == "sell":
            # Add gold
            new_state.faction.add_resource("gold", action["price"])
            # Remove sold item
            new_state.faction.remove_resource(action["item"], 1)
            
        elif action["type"] == "offer_quest":
            # Nothing to do here - just offering a quest doesn't change state
            pass
            
        elif action["type"] == "rest":
            # Nothing to do - staying in place
            pass
        
        # Clear cached actions since the state has changed
        new_state._possible_actions = None
        
        return new_state
    
    def is_terminal(self):
        """
        Check if this is a terminal state.
        For factions, there's no real "terminal" state in normal gameplay.
        
        Returns:
            bool: Always False in this implementation
        """
        return False
    
    def get_reward(self):
        """
        Get the reward value for this state.
        Higher means better state for the faction.
        
        Returns:
            float: The calculated reward value
        """
        reward = 0.0
        
        # Reward for resources (especially gold)
        for resource, amount in self.faction.resources.items():
            if resource == "gold":
                reward += amount * 0.1  # Gold is valuable
            else:
                reward += amount * 0.05  # Other resources
        
        # Reward for being in preferred locations/biomes
        current_location = self.faction.current_location_id
        if current_location in self.faction.preferred_locations:
            reward += 2.0
            
        # Check biome if we have world info
        if 'locations' in self.world_info and current_location in self.world_info['locations']:
            biome = self.world_info['locations'][current_location].get('biome')
            if biome in self.faction.preferred_biomes:
                reward += 1.5
        
        return reward
    
    ### Utility methods ###

    def clone(self):
        """
        Create a deep copy of this state.
        
        Returns:
            factionState: A new identical state object
        """
        # Convert faction to dict and back for deep copy
        faction_dict = self.faction.to_dict()
        new_faction = self.faction.__class__.from_dict(faction_dict)
        
        # Create new state with copied data
        new_state = PlayerState(
            new_faction,
            world_info=self.world_info.copy(),
            location_graph=self.location_graph.copy()
        )
        
        return new_state
    
    def __str__(self):
        """String representation of the state"""
        return f"factionState({self.faction.name} at {self.faction.current_location_id})"
    
    def __repr__(self):
        return f"factionState(faction={self.faction.name}, location={self.faction.current_location_id})"
    
    def to_dict(self):
        """Convert state to dictionary for storage"""
        return {
            "inventory": self.inventory.to_dict(),
            "equipment": self.equipment.to_dict(),
            "equipment": self.world_info,
            "health": self.health,
            "mana": self.mana,
            "stamina": self.stamina,
            "player": self.player.toString()

        }
    
    @classmethod
    def from_dict(cls, data):
        """Create state from dictionary data"""
        from ..entities.player import Player  # Avoid circular import
        
        faction = faction.from_dict(data["faction"])
        return cls(
            inventory=Player.inventory.from_dict(data["inventory"]),
            equipment=Player.equipment.from_dict(data["equipment"]),
            name=Player.name.fromString(data["name"]),
            health=Player.data["health"],
            mana=Player.mana,
            stamina=Player.stamina
        )
