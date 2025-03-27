"""
MCTS state representation for trader decision making.

This module provides a state representation for traders that is compatible
with the Monte Carlo Tree Search algorithm. It includes action generation,
state transition, and reward calculation for trader decision making.

Additional functions to consider adding:
- Action prioritization based on trader personality traits
- Trade action generation for specific markets
- Quest-based action generation
- Improved reward calculation based on trader goals
- Risk assessment for different travel routes
- Weather/season effects on decision making
- Specialized terminal state detection for different trader types
- Serialization methods to store partial search trees
- Heuristic guidance for action selection
- Neural network policy and value function integration
"""

from typing import List, Dict, Any, Optional, Set, Tuple
import random
import logging
import copy
import json

logger = logging.getLogger(__name__)

class TraderAction:
    """Represents an action a trader can take."""
    
    def __init__(self, 
                 action_type: str, 
                 destination_id: Optional[str] = None,
                 destination_name: Optional[str] = None,
                 item_id: Optional[str] = None,
                 price: Optional[float] = None,
                 area_path: Optional[List[str]] = None):
        """
        Initialize a trader action.
        
        Args:
            action_type: Type of action (move, buy, sell, rest, etc.)
            destination_id: ID of the destination location (for move actions)
            destination_name: Name of the destination (for move actions)
            item_id: ID of the item involved (for buy/sell actions)
            price: Price of the item (for buy/sell actions)
            area_path: Path of areas to traverse (for move actions)
        """
        self.action_type = action_type
        self.destination_id = destination_id
        self.destination_name = destination_name
        self.item_id = item_id
        self.price = price
        self.area_path = area_path if area_path else []
        
        # Optional data for specialized actions
        self.risk_level = 0.0  # Higher means more dangerous
        self.estimated_profit = 0.0  # Expected profit from this action
        self.time_cost = 1  # How many time units this action takes
        self.domain_bonus = 0.0  # Bonus for domain-specific heuristics
        
    def __str__(self) -> str:
        """String representation of the action."""
        if self.action_type == "move":
            return f"Move to {self.destination_name}"
        elif self.action_type == "buy":
            return f"Buy {self.item_id} for {self.price}"
        elif self.action_type == "sell":
            return f"Sell {self.item_id} for {self.price}"
        elif self.action_type == "rest":
            return "Rest in current location"
        elif self.action_type == "settle":
            return f"Settle in {self.destination_name}"
        elif self.action_type == "open_shop":
            return f"Open shop in {self.destination_name}"
        else:
            return f"{self.action_type} action"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert action to dictionary."""
        return {
            "action_type": self.action_type,
            "destination_id": self.destination_id,
            "destination_name": self.destination_name,
            "item_id": self.item_id,
            "price": self.price,
            "area_path": self.area_path,
            "risk_level": self.risk_level,
            "estimated_profit": self.estimated_profit,
            "time_cost": self.time_cost,
            "domain_bonus": self.domain_bonus
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TraderAction':
        """Create action from dictionary."""
        action = cls(
            action_type=data.get("action_type", "unknown"),
            destination_id=data.get("destination_id"),
            destination_name=data.get("destination_name"),
            item_id=data.get("item_id"),
            price=data.get("price"),
            area_path=data.get("area_path", [])
        )
        action.risk_level = data.get("risk_level", 0.0)
        action.estimated_profit = data.get("estimated_profit", 0.0)
        action.time_cost = data.get("time_cost", 1)
        action.domain_bonus = data.get("domain_bonus", 0.0)
        return action

class TraderState:
    """
    State representation for trader AI decision-making using MCTS.
    
    This class represents the state of a trader for use in Monte Carlo Tree Search,
    including information about the trader, the world, and available actions.
    """
    
    def __init__(self, trader_data: Dict[str, Any], world_data: Optional[Dict[str, Any]] = None):
        """
        Initialize trader state.
        
        Args:
            trader_data: Dictionary with trader entity properties
            world_data: Dictionary with world state information
        """
        self.trader_data = trader_data
        self.world_data = world_data or {}
        self._legal_actions = None
        self._action_probabilities = None
        
        # Cache frequently used values for performance
        self.current_settlement_id = trader_data.get("current_location_id")
        self.destination_id = trader_data.get("destination_id")
        self.gold = trader_data.get("gold", 0)
        self.inventory = trader_data.get("inventory", {})
        
        # Trader preferences
        self.preferred_settlements = trader_data.get("preferred_settlements", [])
        self.preferred_biomes = trader_data.get("preferred_biomes", [])
        self.visited_settlements = trader_data.get("visited_settlements", [])
        
        # Status flags
        self.is_traveling = trader_data.get("is_traveling", False)
        self.is_settled = trader_data.get("is_settled", False)
        self.is_retired = trader_data.get("is_retired", False)
        self.has_shop = trader_data.get("has_shop", False)
        
        # Day counter for simulations
        self.simulation_days = 0
        
    def get_legal_actions(self) -> List[TraderAction]:
        """
        Get all legal actions in the current state.
        
        Returns:
            List of TraderAction objects representing possible actions
        """
        # Use cached actions if available
        if self._legal_actions is not None:
            return self._legal_actions
        
        actions = []
        
        # Skip actions if retired
        if self.is_retired:
            # Only option is to stay retired
            actions.append(TraderAction(action_type="rest"))
            self._legal_actions = actions
            return actions
        
        # Generate movement actions if we're in a settlement and not settled down
        if self.current_settlement_id and not self.is_settled:
            # Get connected settlements
            settlement_connections = self._get_settlement_connections()
            
            for connection in settlement_connections:
                if connection.get("destination_id") == self.current_settlement_id:
                    # Skip connections pointing to current location
                    continue
                    
                actions.append(TraderAction(
                    action_type="move",
                    destination_id=connection.get("destination_id"),
                    destination_name=connection.get("destination", "Unknown"),
                    area_path=connection.get("path", [])
                ))
        
        # Generate trade actions if we're in a settlement with market data
        if self.current_settlement_id and self._has_market_data():
            # Buy actions
            for item_id, price in self._get_items_for_sale().items():
                if self.gold >= price:
                    actions.append(TraderAction(
                        action_type="buy",
                        item_id=item_id,
                        price=price
                    ))
            
            # Sell actions
            for item_id, count in self.inventory.items():
                if count > 0 and item_id in self._get_items_to_buy():
                    price = self._get_items_to_buy()[item_id]
                    actions.append(TraderAction(
                        action_type="sell",
                        item_id=item_id,
                        price=price
                    ))
        
        # Generate settlement actions if conditions are right
        if self.current_settlement_id:
            # Settle down action - if has enough gold and likes the settlement
            settlement_score = self._calculate_settlement_score(self.current_settlement_id)
            if self.gold >= 500 and settlement_score >= 0.7:
                actions.append(TraderAction(
                    action_type="settle",
                    destination_id=self.current_settlement_id,
                    destination_name=self._get_settlement_name(self.current_settlement_id)
                ))
                
            # Open shop action - if has even more gold and really likes the settlement
            if self.gold >= 1000 and settlement_score >= 0.8:
                actions.append(TraderAction(
                    action_type="open_shop",
                    destination_id=self.current_settlement_id,
                    destination_name=self._get_settlement_name(self.current_settlement_id)
                ))
                
            # Retire action - if very wealthy
            if self.gold >= 2000:
                actions.append(TraderAction(action_type="retire"))
        
        # Add rest action unless traveling
        if not self.is_traveling:
            actions.append(TraderAction(action_type="rest"))
        
        # Calculate action probabilities based on trader preferences
        self._calculate_action_probabilities(actions)
        
        # Cache actions
        self._legal_actions = actions
        return actions
    
    def _calculate_settlement_score(self, settlement_id: str) -> float:
        """
        Calculate how desirable a settlement is for this trader.
        
        Args:
            settlement_id: ID of the settlement to evaluate
            
        Returns:
            Float score between 0 and 1, higher is better
        """
        score = 0.5  # Base score
        
        # Preferred settlement bonus
        if settlement_id in self.preferred_settlements:
            score += 0.3
        
        # Preferred biome bonus
        settlement_biome = self._get_settlement_biome(settlement_id)
        if settlement_biome in self.preferred_biomes:
            score += 0.2
        
        # Market quality bonus
        if self._has_market_data():
            market_size = len(self._get_items_for_sale()) + len(self._get_items_to_buy())
            if market_size > 20:
                score += 0.2
            elif market_size > 10:
                score += 0.1
        
        # Cap at 1.0
        return min(1.0, score)
    
    def _calculate_action_probabilities(self, actions: List[TraderAction]) -> None:
        """
        Calculate probabilities for each action based on trader preferences.
        
        Args:
            actions: List of possible actions
        """
        if not actions:
            self._action_probabilities = {}
            return
            
        probabilities = {}
        
        for action in actions:
            prob = 1.0  # Base probability
            
            if action.action_type == "move":
                # Prefer previously unvisited settlements
                if action.destination_id not in self.visited_settlements:
                    prob *= 1.5
                
                # Prefer settlements of preferred biome
                settlement_biome = self._get_settlement_biome(action.destination_id)
                if settlement_biome in self.preferred_biomes:
                    prob *= 2.0
                
                # Prefer settlements on trader's preferred list
                if action.destination_id in self.preferred_settlements:
                    prob *= 2.5
                
                # If there's a destination set, prioritize moving there
                if self.destination_id and action.destination_id == self.destination_id:
                    prob *= 3.0
            
            elif action.action_type == "buy":
                # Buying preferences could be set here
                # For example, prefer items in short supply
                pass
                
            elif action.action_type == "sell":
                # Selling preferences could be set here
                # For example, prefer selling high-value items
                if action.price and action.price > 50:
                    prob *= 1.5
            
            # Rest is always low priority
            elif action.action_type == "rest":
                prob *= 0.3
                
            # Settlement actions are high priority when available
            elif action.action_type == "settle":
                prob *= 2.0
                
            elif action.action_type == "open_shop":
                prob *= 2.5
                
            elif action.action_type == "retire":
                if self.gold > 5000:  # Really wealthy
                    prob *= 3.0
                else:
                    prob *= 1.5
            
            probabilities[action] = prob
        
        # Normalize probabilities
        total = sum(probabilities.values())
        if total > 0:
            for action in probabilities:
                probabilities[action] /= total
        
        self._action_probabilities = probabilities
    
    def apply_action(self, action: TraderAction) -> 'TraderState':
        """
        Apply an action to this state and return the new state.
        
        Args:
            action: The action to apply
            
        Returns:
            A new TraderState resulting from the action
        """
        # Create a deep copy of the current state
        new_trader_data = copy.deepcopy(self.trader_data)
        new_state = TraderState(new_trader_data, copy.deepcopy(self.world_data))
        
        # Increment simulation days
        new_state.simulation_days = self.simulation_days + action.time_cost
        
        # Apply the action effect
        if action.action_type == "move":
            # Update location
            new_state.trader_data["current_location_id"] = action.destination_id
            
            # Add to visited settlements
            if "visited_settlements" not in new_state.trader_data:
                new_state.trader_data["visited_settlements"] = []
            if action.destination_id not in new_state.trader_data["visited_settlements"]:
                new_state.trader_data["visited_settlements"].append(action.destination_id)
            
            # Clear destination if reached
            if new_state.trader_data.get("destination_id") == action.destination_id:
                new_state.trader_data["destination_id"] = None
            
            # Update traveling flag
            new_state.trader_data["is_traveling"] = len(action.area_path) > 0
            
            # Update cached values
            new_state.current_settlement_id = action.destination_id
            new_state.visited_settlements = new_state.trader_data["visited_settlements"]
            new_state.is_traveling = new_state.trader_data["is_traveling"]
            
        elif action.action_type == "buy":
            # Deduct gold
            new_state.trader_data["gold"] = new_state.gold - action.price
            
            # Add item to inventory
            if "inventory" not in new_state.trader_data:
                new_state.trader_data["inventory"] = {}
            if action.item_id not in new_state.trader_data["inventory"]:
                new_state.trader_data["inventory"][action.item_id] = 0
                
            new_state.trader_data["inventory"][action.item_id] += 1
            
            # Update cached values
            new_state.gold = new_state.trader_data["gold"]
            new_state.inventory = new_state.trader_data["inventory"]
            
        elif action.action_type == "sell":
            # Add gold
            new_state.trader_data["gold"] = new_state.gold + action.price
            
            # Remove item from inventory
            if action.item_id in new_state.trader_data.get("inventory", {}):
                new_state.trader_data["inventory"][action.item_id] -= 1
                if new_state.trader_data["inventory"][action.item_id] <= 0:
                    del new_state.trader_data["inventory"][action.item_id]
            
            # Update cached values
            new_state.gold = new_state.trader_data["gold"]
            new_state.inventory = new_state.trader_data["inventory"]
            
        elif action.action_type == "settle":
            # Settle down in current location
            new_state.trader_data["is_settled"] = True
            new_state.trader_data["is_traveling"] = False
            
            # Update cached values
            new_state.is_settled = True
            new_state.is_traveling = False
            
        elif action.action_type == "open_shop":
            # Open shop in current location
            new_state.trader_data["has_shop"] = True
            new_state.trader_data["shop_location_id"] = action.destination_id
            new_state.trader_data["is_settled"] = True
            new_state.trader_data["is_traveling"] = False
            
            # Deduct startup costs
            new_state.trader_data["gold"] = new_state.gold - 500  # Shop startup cost
            
            # Update cached values
            new_state.has_shop = True
            new_state.is_settled = True
            new_state.is_traveling = False
            new_state.gold = new_state.trader_data["gold"]
            
        elif action.action_type == "retire":
            # Retire from trading
            new_state.trader_data["is_retired"] = True
            new_state.trader_data["is_traveling"] = False
            
            # Update cached values
            new_state.is_retired = True
            new_state.is_traveling = False
            
        elif action.action_type == "rest":
            # Rest - just the time cost applies
            pass
        
        # Clear cached actions
        new_state._legal_actions = None
        new_state._action_probabilities = None
        
        return new_state
    
    def is_terminal(self) -> bool:
        """
        Check if this is a terminal state (simulation should end).
        
        Returns:
            True if terminal, False otherwise
        """
        # Terminal conditions:
        
        # 1. Trader has retired
        if self.is_retired:
            return True
            
        # 2. Trader has opened a shop
        if self.has_shop:
            return True
            
        # 3. Trader has been to all settlements (completed tour)
        settlements = self._get_all_settlements()
        if len(settlements) > 0 and len(self.visited_settlements) >= len(settlements):
            return True
            
        # 4. Trader has reached a destination with full inventory
        if (self.destination_id == self.current_settlement_id and 
            self.destination_id is not None and
            len(self.inventory) >= 5):  # Arbitrary threshold for "full" inventory
            return True
            
        # 5. Long simulation (prevent infinite loops)
        if self.simulation_days > 100:  # Arbitrary limit
            return True
            
        return False
    
    def get_reward(self) -> float:
        """
        Calculate reward value for this state.
        
        Returns:
            Float reward value (higher is better)
        """
        reward = 0.0
        
        # Reward for gold (basic wealth)
        reward += self.gold * 0.1
        
        # Reward for status achievements
        if self.is_retired:
            retirement_bonus = 100.0 * (self.gold / 1000.0)  # Scale with wealth
            reward += retirement_bonus
        
        if self.has_shop:
            shop_bonus = 200.0
            # Bonus for shop location quality
            shop_location = self.trader_data.get("shop_location_id")
            if shop_location:
                settlement_score = self._calculate_settlement_score(shop_location)
                shop_bonus *= settlement_score
            reward += shop_bonus
        
        if self.is_settled and not self.has_shop:
            # Settling down without a shop
            settlement_score = self._calculate_settlement_score(self.current_settlement_id)
            reward += 50.0 * settlement_score
        
        # Reward for valuable inventory
        inventory_value = sum(self._get_item_value(item_id) * count 
                             for item_id, count in self.inventory.items())
        reward += inventory_value * 0.05
        
        # Reward for being in preferred settlement
        if self.current_settlement_id in self.preferred_settlements:
            reward += 10.0
        
        # Reward for being in preferred biome
        settlement_biome = self._get_settlement_biome(self.current_settlement_id)
        if settlement_biome in self.preferred_biomes:
            reward += 5.0
        
        # Reward for exploring new settlements
        exploration_reward = len(self.visited_settlements) * 2.0
        reward += exploration_reward
        
        # Reward for reaching destination
        if self.destination_id == self.current_settlement_id and self.destination_id is not None:
            reward += 20.0
        
        # Penalty for long simulations (encourages efficiency)
        reward -= self.simulation_days * 0.1
        
        return reward
    
    def _get_settlement_connections(self) -> List[Dict[str, Any]]:
        """
        Get connections from the current settlement.
        
        Returns:
            List of connection dictionaries
        """
        if not self.current_settlement_id:
            return []
            
        # Get the settlement data from the world data
        settlements = self.world_data.get("settlements", {})
        current_settlement = settlements.get(self.current_settlement_id, {})
        
        # Get connections - format can vary based on your data structure
        connections = current_settlement.get("connections", [])
        if isinstance(connections, str):
            try:
                connections = json.loads(connections)
            except:
                connections = []
        
        return connections
    
    def _get_all_settlements(self) -> Set[str]:
        """
        Get all settlement IDs from the world data.
        
        Returns:
            Set of settlement IDs
        """
        settlements = self.world_data.get("settlements", {})
        return set(settlements.keys())
    
    def _has_market_data(self) -> bool:
        """
        Check if the current settlement has market data.
        
        Returns:
            True if market data exists, False otherwise
        """
        if not self.current_settlement_id:
            return False
            
        markets = self.world_data.get("markets", {})
        return self.current_settlement_id in markets
    
    def _get_items_for_sale(self) -> Dict[str, float]:
        """
        Get items for sale at the current settlement.
        
        Returns:
            Dictionary of item IDs to prices
        """
        if not self.current_settlement_id:
            return {}
            
        markets = self.world_data.get("markets", {})
        market = markets.get(self.current_settlement_id, {})
        
        return market.get("selling", {})
    
    def _get_items_to_buy(self) -> Dict[str, float]:
        """
        Get items the current settlement will buy.
        
        Returns:
            Dictionary of item IDs to prices
        """
        if not self.current_settlement_id:
            return {}
            
        markets = self.world_data.get("markets", {})
        market = markets.get(self.current_settlement_id, {})
        
        return market.get("buying", {})
    
    def _get_settlement_name(self, settlement_id: Optional[str]) -> str:
        """
        Get the name of a settlement.
        
        Args:
            settlement_id: ID of the settlement
            
        Returns:
            Settlement name or default string
        """
        if not settlement_id:
            return "Unknown"
            
        settlements = self.world_data.get("settlements", {})
        settlement = settlements.get(settlement_id, {})
        
        return settlement.get("name", f"Settlement {settlement_id}")
    
    def _get_settlement_biome(self, settlement_id: Optional[str]) -> Optional[str]:
        """
        Get the biome of a settlement.
        
        Args:
            settlement_id: ID of the settlement
            
        Returns:
            Biome name or None if not found
        """
        if not settlement_id:
            return None
            
        settlements = self.world_data.get("settlements", {})
        settlement = settlements.get(settlement_id, {})
        
        return settlement.get("biome")
    
    def _get_item_value(self, item_id: str) -> float:
        """
        Get the base value of an item.
        
        Args:
            item_id: ID of the item
            
        Returns:
            Base value of the item
        """
        items = self.world_data.get("items", {})
        item = items.get(item_id, {})
        
        return item.get("base_value", 5.0)  # Default to 5 if not specified
    
    def __str__(self) -> str:
        """String representation of the state."""
        name = self.trader_data.get("name", f"Trader {self.trader_data.get('trader_id', 'unknown')}")
        location = self._get_settlement_name(self.current_settlement_id) if self.current_settlement_id else "traveling"
        
        status = "retired" if self.is_retired else \
                 "shopkeeper" if self.has_shop else \
                 "settled" if self.is_settled else \
                 "traveling" if self.is_traveling else "active"
                 
        return f"{name} ({status}) at {location} with {self.gold} gold"