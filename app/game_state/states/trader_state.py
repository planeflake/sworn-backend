from app.game_state.mcts import MCTS
import logging as logger

class TraderState:
    """
    State representation for trader AI decision-making using MCTS.
    This class represents the state of a trader for use in Monte Carlo Tree Search.
    """
    
    def __init__(self, trader, world_info=None, location_graph=None):
        """
        Initialize a trader state for decision-making.
        
        Args:
            trader: The Trader object this state represents
            world_info: Information about the game world (optional)
            location_graph: Graph of location connections (optional)
        """
        self.trader = trader
        self.world_info = world_info or {}
        self.location_graph = location_graph or {}
        
        # Cache of possible actions for this state
        self._possible_actions = None
        
    def get_possible_actions(self):
        """
        Get all possible actions the trader can take in the current state.
        
        Returns:
            list: List of possible action objects
        """
        if self._possible_actions is not None:
            return self._possible_actions
            
        actions = []
        
        # Add movement actions
        movement_actions = self._get_movement_actions()
        actions.extend(movement_actions)
        
        # Add trade actions
        trade_actions = self._get_trade_actions()
        actions.extend(trade_actions)
        
        # Add quest actions
        quest_actions = self._get_quest_actions()
        actions.extend(quest_actions)
        
        # Add rest action (stay in place)
        actions.append({"type": "rest", "location_id": self.trader.current_location_id})
        
        self._possible_actions = actions
        return actions
    
    def _get_movement_actions(self):
        """
        Get possible movement actions based on the trader's current location.
        
        Returns:
            list: List of possible movement actions
        """
        actions = []
        
        # If we have a location graph, use it to find connected locations
        current_location = self.trader.current_location_id
        if current_location in self.location_graph:
            connected_locations = self.location_graph[current_location]
            
            for location_id in connected_locations:
                # Skip unacceptable locations
                if location_id in self.trader.unacceptable_locations:
                    continue
                    
                # Create movement action
                action = {
                    "type": "move",
                    "location_id": location_id,
                    "score": self._score_location(location_id)
                }
                actions.append(action)
        
        return actions
    
    def _score_location(self, location_id):
        """
        Score a location based on trader preferences.
        
        Args:
            location_id: The ID of the location to score
            
        Returns:
            float: A score for this location (higher is better)
        """
        score = 1.0  # Base score
        
        # Preferred locations get a bonus
        if location_id in self.trader.preferred_locations:
            score += 2.0
        
        # Get location biome if available in world_info
        if 'locations' in self.world_info and location_id in self.world_info['locations']:
            biome = self.world_info['locations'][location_id].get('biome')
            
            # Preferred biomes get a bonus
            if biome in self.trader.preferred_biomes:
                score += 1.5
        
        # Previously visited locations are slightly less interesting
        if hasattr(self.trader, 'visited_locations') and location_id in self.trader.visited_locations:
            score -= 0.5
        
        return score
    
    def _get_trade_actions(self):
        """
        Get possible trade actions at the current location.
        
        Returns:
            list: List of possible trade actions
        """
        actions = []
        
        # Check if there are trade opportunities at the current location
        current_location = self.trader.current_location_id
        if 'market_data' in self.world_info and current_location in self.world_info['market_data']:
            market = self.world_info['market_data'][current_location]
            
            # Buy actions - based on what trader can afford
            for item, price in market.get('selling', {}).items():
                if 'gold' in self.trader.resources and self.trader.resources['gold'] >= price:
                    action = {
                        "type": "buy",
                        "item": item,
                        "price": price,
                        "location_id": current_location
                    }
                    actions.append(action)
            
            # Sell actions - based on what trader has
            for item in self.trader.resources:
                if item != 'gold' and item in market.get('buying', {}):
                    price = market['buying'][item]
                    action = {
                        "type": "sell",
                        "item": item,
                        "price": price,
                        "location_id": current_location
                    }
                    actions.append(action)
        
        return actions
    
    def _get_quest_actions(self):
        """
        Get possible quest-related actions.
        
        Returns:
            list: List of possible quest actions
        """
        actions = []
        
        # Offer available quests at current location
        for quest_id in self.trader.available_quests:
            action = {
                "type": "offer_quest",
                "quest_id": quest_id,
                "location_id": self.trader.current_location_id
            }
            actions.append(action)
        
        return actions
    
    def apply_action(self, action):
        """
        Apply an action to this state and return the new state.
        
        Args:
            action: The action to apply
            
        Returns:
            TraderState: A new state resulting from the action
        """
        # Create a copy of this state
        new_state = self.clone()
        
        # Apply the action based on its type
        if action["type"] == "move":
            new_state.trader.set_location(action["location_id"], "current")
            # Clear destination if we've reached it
            if new_state.trader.destination_id == action["location_id"]:
                new_state.trader.set_location(None, "destination")
                
        elif action["type"] == "buy":
            # Deduct gold
            new_state.trader.remove_resource("gold", action["price"])
            # Add purchased item
            new_state.trader.add_resource(action["item"], 1)
            
        elif action["type"] == "sell":
            # Add gold
            new_state.trader.add_resource("gold", action["price"])
            # Remove sold item
            new_state.trader.remove_resource(action["item"], 1)
            
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
        For traders, there's no real "terminal" state in normal gameplay.
        
        Returns:
            bool: Always False in this implementation
        """
        return False
    
    def get_reward(self):
        """
        Get the reward value for this state.
        Higher means better state for the trader.
        
        Returns:
            float: The calculated reward value
        """
        reward = 0.0
        
        # Reward for resources (especially gold)
        for resource, amount in self.trader.resources.items():
            if resource == "gold":
                reward += amount * 0.1  # Gold is valuable
            else:
                reward += amount * 0.05  # Other resources
        
        # Reward for being in preferred locations/biomes
        current_location = self.trader.current_location_id
        if current_location in self.trader.preferred_locations:
            reward += 2.0
            
        # Check biome if we have world info
        if 'locations' in self.world_info and current_location in self.world_info['locations']:
            biome = self.world_info['locations'][current_location].get('biome')
            if biome in self.trader.preferred_biomes:
                reward += 1.5
        
        return reward
    
    def clone(self):
        """
        Create a deep copy of this state.
        
        Returns:
            TraderState: A new identical state object
        """
        # Convert trader to dict and back for deep copy
        trader_dict = self.trader.to_dict()
        new_trader = self.trader.__class__.from_dict(trader_dict)
        
        # Create new state with copied data
        new_state = TraderState(
            new_trader,
            world_info=self.world_info.copy(),
            location_graph=self.location_graph.copy()
        )
        
        return new_state
    
    def __str__(self):
        """String representation of the state"""
        return f"TraderState({self.trader.name} at {self.trader.current_location_id})"
    
    def to_dict(self):
        """Convert state to dictionary for storage"""
        return {
            "trader": self.trader.to_dict(),
            "world_info": self.world_info,
            "location_graph": self.location_graph
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create state from dictionary data"""
        from ..entities.trader import Trader  # Avoid circular import
        
        trader = Trader.from_dict(data["trader"])
        return cls(
            trader=trader,
            world_info=data.get("world_info", {}),
            location_graph=data.get("location_graph", {})
        )
