import json
import random
import math

class TraderState:
    """Represents the current state of a trader and the world."""
    
    def __init__(self, trader_data, settlements_data, current_location):
        self.trader = trader_data
        self.settlements = settlements_data
        self.current_location = current_location
        
    def get_legal_actions(self):
        """Get all valid destinations the trader can move to from current location."""
        actions = []
        
        # Find current settlement
        for settlement in self.settlements:
            if settlement["name"] == self.current_location:
                # Add all connections as possible actions
                for connection in settlement.get("connections", []):
                    actions.append(TraderAction(destination=connection["destination"]))
                break
                
        return actions
    
    def apply_action(self, action):
        """Apply an action to this state and return the new state."""
        # Create deep copies to avoid modifying the original data
        new_trader = self._deep_copy_trader(self.trader)
        new_settlements = self._deep_copy_settlements(self.settlements)
        
        # Simulate travel
        self._simulate_travel(new_trader, self.current_location, action.destination, new_settlements)
        
        # Simulate trading
        self._simulate_trading(new_trader, action.destination, new_settlements)
        
        # Return a new state
        return TraderState(new_trader, new_settlements, action.destination)
    
    def _deep_copy_trader(self, trader):
        """Create a deep copy of trader data."""
        return json.loads(json.dumps(trader))
    
    def _deep_copy_settlements(self, settlements):
        """Create a deep copy of settlements data."""
        return json.loads(json.dumps(settlements))
        
    def _simulate_travel(self, trader, from_location, to_location, settlements):
        """Simulate travel between settlements."""
        # Find the route
        route = None
        for settlement in settlements:
            if settlement["name"] == from_location:
                for connection in settlement.get("connections", []):
                    if connection["destination"] == to_location:
                        route = connection
                        break
                break
        
        if not route:
            return
        
        # Apply travel effects
        # Reduce cart health based on route condition
        condition_damage = {
            "good": 1,
            "moderate": 3,
            "poor": 5,
            "difficult": 8,
            "treacherous": 12,
            "hidden": 10,
            "secret": 15
        }
        
        damage = condition_damage.get(route.get("path_condition", "moderate"), 3)
        
        # Adjust for underground travel
        if route.get("underground_route", False):
            # Check if trader has proper equipment
            if not self._has_underground_equipment(trader):
                damage *= 2
        
        # Apply damage
        trader["logistics"]["cart_health"] = max(0, trader["logistics"]["cart_health"] - damage)
        
        # Simulate travel events (simplified for now)
        if route.get("danger_level", 0) > 5:
            # High danger routes have a chance of events
            if random.random() < route["danger_level"] * 0.05:
                # Simulate a simple event - more damage and potential gold loss
                trader["logistics"]["cart_health"] = max(0, trader["logistics"]["cart_health"] - random.randint(5, 15))
                
                if random.random() < 0.3:  # 30% chance of losing some gold
                    gold_loss = min(trader["status"]["gold"], random.randint(10, 30))
                    trader["status"]["gold"] -= gold_loss
    
    def _simulate_trading(self, trader, location, settlements):
        """Simulate trading at a settlement."""
        # Find the settlement
        settlement = None
        for s in settlements:
            if s["name"] == location:
                settlement = s
                break
        
        if not settlement:
            return
        
        # Simulate selling goods based on settlement needs
        for item, details in list(trader["wares"].items()):
            if item in settlement.get("needs", {}):
                need = settlement["needs"][item]
                
                # Calculate how much to sell
                quantity_to_sell = min(details["quantity"], random.randint(1, details["quantity"]))
                
                # Calculate sale price
                sale_price = min(details["price"] * 1.4, need["max_price"])
                
                # Update trader
                trader["wares"][item]["quantity"] -= quantity_to_sell
                trader["status"]["gold"] += int(quantity_to_sell * sale_price)
                
                # Remove empty items
                if trader["wares"][item]["quantity"] <= 0:
                    del trader["wares"][item]
        
        # Simulate buying goods based on settlement resources
        if trader["status"]["gold"] > 50:  # Only buy if we have some gold
            for resource, amount in settlement.get("initial_resources", {}).items():
                # Skip non-tradable resources like population
                if resource in ["population", "water"]:
                    continue
                    
                # Check if this resource is valuable elsewhere
                is_needed = False
                for other_settlement in settlements:
                    if other_settlement["name"] != location and resource in other_settlement.get("needs", {}):
                        is_needed = True
                        break
                
                if is_needed and random.random() < 0.7:  # 70% chance to buy needed resources
                    # Calculate buy price (this would be more complex in reality)
                    buy_price = random.randint(3, 8)  # Simplified pricing
                    
                    # Calculate how much to buy
                    max_affordable = trader["status"]["gold"] // buy_price
                    max_capacity = max(0, trader["logistics"]["cart_capacity"] - self._get_current_load(trader))
                    
                    quantity_to_buy = min(max_affordable, max_capacity, random.randint(5, 20))
                    
                    if quantity_to_buy > 0:
                        # Update trader
                        if resource not in trader["wares"]:
                            trader["wares"][resource] = {"quantity": 0, "price": buy_price}
                        
                        trader["wares"][resource]["quantity"] += quantity_to_buy
                        trader["status"]["gold"] -= quantity_to_buy * buy_price
    
    def _get_current_load(self, trader):
        """Calculate current load of trader's cart."""
        return sum(item["quantity"] for item in trader["wares"].values())
    
    def _has_underground_equipment(self, trader):
        """Check if trader has necessary equipment for underground travel."""
        return any(item.endswith("lantern") for item in trader.get("equipment", []))
    
    def get_state_features(self):
        """Extract features for neural network input."""
        trader = self.trader
        
        # Trader personality features
        personality_features = [
            trader["personality"]["greed"] / 10.0,
            trader["personality"]["risk_tolerance"] / 10.0,
            trader["personality"]["loyalty"] / 10.0,
            trader["personality"]["specialty_focus"] / 10.0
        ]
        
        # Trader status features
        status_features = [
            trader["logistics"]["cart_health"] / 100.0,
            trader["status"]["health"] / 100.0,
            trader["status"]["gold"] / 1000.0,  # Normalize gold
            len(trader["logistics"]["cart_upgrades"]) / 5.0,  # Normalize upgrades
            self._get_current_load(trader) / trader["logistics"]["cart_capacity"]  # Load percentage
        ]
        
        # Current location features (one-hot encode area type)
        location_features = [0, 0, 0, 0, 0]  # forest, mountains, plains, coastal, underground
        current_settlement = self._get_settlement(self.current_location)
        
        if current_settlement:
            area_type = current_settlement.get("area_type", "")
            if area_type == "forest":
                location_features[0] = 1
            elif area_type == "mountains":
                location_features[1] = 1
            elif area_type == "plains":
                location_features[2] = 1
            elif area_type == "coastal":
                location_features[3] = 1
            elif area_type == "underground":
                location_features[4] = 1
        
        # Combine all features
        return personality_features + status_features + location_features
    
    def _get_settlement(self, name):
        """Find a settlement by name."""
        for settlement in self.settlements:
            if settlement["name"] == name:
                return settlement
        return None
        
    def is_terminal(self):
        """Check if this is a terminal state (trader can't move or trade)."""
        # If cart is completely broken
        if self.trader["logistics"]["cart_health"] <= 0:
            return True
            
        # If trader is out of goods and money
        if len(self.trader["wares"]) == 0 and self.trader["status"]["gold"] < 10:
            return True
            
        return False
    
    def get_reward(self):
        """Calculate the reward for reaching this state."""
        # Base reward is trader's gold
        reward = self.trader["status"]["gold"]
        
        # Add value of current inventory
        for item, details in self.trader["wares"].items():
            reward += details["quantity"] * details["price"] * 0.8  # Discount for unsold goods
        
        # Penalize damaged cart
        cart_health = self.trader["logistics"]["cart_health"]
        if cart_health < 50:
            reward -= (50 - cart_health) * 5
        
        # Penalize damaged health
        trader_health = self.trader["status"]["health"]
        if trader_health < 50:
            reward -= (50 - trader_health) * 7
        
        # Add bonus for reaching life goal
        if "life_goal" in self.trader and "progress" in self.trader["life_goal"]:
            reward += self.trader["life_goal"]["progress"] * 1000
        
        return reward


class TraderAction:
    """Represents an action a trader can take."""
    
    def __init__(self, destination):
        self.destination = destination
    
    def __eq__(self, other):
        if not isinstance(other, TraderAction):
            return False
        return self.destination == other.destination
    
    def __hash__(self):
        return hash(self.destination)