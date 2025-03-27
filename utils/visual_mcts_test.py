#!/usr/bin/env python3
"""
Visual MCTS test that doesn't rely on database connections.
This script demonstrates the trader life goals and MCTS decision making visually.
"""

import sys
import os
import logging
import json
import random
import uuid
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Trader entity class for testing
class Trader:
    def __init__(self, trader_id: str):
        self.trader_id = trader_id
        self.properties = {
            "name": "Test Trader",
            "gold": 100,
            "inventory": {
                "cloth": 5,
                "spices": 3,
                "tools": 2
            },
            "current_location_id": None,
            "preferred_biomes": ["forest", "plains"],
            "preferred_settlements": [],
            "visited_settlements": [],
            "life_goals": []
        }
        
    def get_property(self, key: str, default=None):
        return self.properties.get(key, default)
        
    def set_property(self, key: str, value):
        self.properties[key] = value
        
    def set_location(self, location_id, location_type="current"):
        if location_type == "current":
            self.properties["current_location_id"] = location_id
            if location_id and location_id not in self.properties.get("visited_settlements", []):
                visited = self.properties.get("visited_settlements", [])
                visited.append(location_id)
                self.properties["visited_settlements"] = visited
                
    def add_resource(self, resource_id, amount):
        if resource_id == "gold":
            self.properties["gold"] = self.properties.get("gold", 0) + amount
        else:
            inventory = self.properties.get("inventory", {})
            inventory[resource_id] = inventory.get(resource_id, 0) + amount
            self.properties["inventory"] = inventory
            
    def remove_resource(self, resource_id, amount):
        if resource_id == "gold":
            current = self.properties.get("gold", 0)
            if current < amount:
                return False
            self.properties["gold"] = current - amount
            return True
        else:
            inventory = self.properties.get("inventory", {})
            current = inventory.get(resource_id, 0)
            if current < amount:
                return False
            inventory[resource_id] = current - amount
            if inventory[resource_id] <= 0:
                del inventory[resource_id]
            self.properties["inventory"] = inventory
            return True
    
    def __str__(self):
        return f"{self.properties.get('name')} ({self.trader_id})"

# MCTS state class for testing
class TraderState:
    def __init__(self, trader, world_info=None, location_graph=None):
        self.trader = trader
        self.world_info = world_info or {}
        self.location_graph = location_graph or {}
        self._possible_actions = None
        
    def get_possible_actions(self):
        """Get all possible actions for the trader"""
        if self._possible_actions is not None:
            return self._possible_actions
            
        actions = []
        
        # Add movement actions
        movement_actions = self._get_movement_actions()
        actions.extend(movement_actions)
        
        # Add trade actions
        trade_actions = self._get_trade_actions()
        actions.extend(trade_actions)
        
        # Add rest action (stay in place)
        current_location = self.trader.get_property("current_location_id")
        if current_location:
            actions.append({
                "type": "rest", 
                "location_id": current_location,
                "score": 0.5  # Lower base score for resting
            })
        
        self._possible_actions = actions
        return actions
    
    def _get_movement_actions(self):
        """Get possible movement actions"""
        actions = []
        
        current_location = self.trader.get_property("current_location_id")
        if current_location in self.location_graph:
            connected_locations = self.location_graph[current_location]
            
            for location_id in connected_locations:
                score = self._score_location(location_id)
                action = {
                    "type": "move",
                    "location_id": location_id,
                    "score": score
                }
                actions.append(action)
        
        return actions
    
    def _score_location(self, location_id):
        """Score a location based on trader preferences and life goals"""
        score = 1.0  # Base score
        
        # Preferred locations bonus
        preferred_settlements = self.trader.get_property("preferred_settlements", [])
        if location_id in preferred_settlements:
            score += 2.0
        
        # Biome preferences
        if 'locations' in self.world_info and location_id in self.world_info['locations']:
            biome = self.world_info['locations'][location_id].get('biome')
            preferred_biomes = self.trader.get_property("preferred_biomes", [])
            if biome in preferred_biomes:
                score += 1.5
        
        # Previously visited locations penalty
        visited_settlements = self.trader.get_property("visited_settlements", [])
        if location_id in visited_settlements:
            score -= 0.5
        
        # Life goal considerations
        for goal in self.trader.get_property("life_goals", []):
            # Target settlement goal
            if goal["type"] == "SPECIFIC_SETTLEMENT" and goal["params"].get("target_settlement_id") == location_id:
                score += 3.0  # Strong bonus
                
            # Visit settlements goal favors unvisited places
            elif goal["type"] == "VISIT_SETTLEMENTS" and location_id not in visited_settlements:
                score += 1.0
                
            # Open shop goal favors preferred settlement types
            elif goal["type"] == "OPEN_SHOP":
                settlement_type = self.world_info.get("locations", {}).get(location_id, {}).get("settlement_type")
                preferred_types = goal["params"].get("preferred_settlement_types", [])
                if settlement_type in preferred_types:
                    score += 1.5
                    
                    # Extra bonus if close to goal
                    gold = self.trader.get_property("gold", 0)
                    target_gold = goal["params"].get("target_gold", 5000)
                    if gold >= target_gold * 0.8:
                        score += 1.0
            
            # Market considerations
            if 'market_data' in self.world_info and location_id in self.world_info['market_data']:
                market = self.world_info['market_data'][location_id]
                
                # Collectors favor markets with items they want
                if goal["type"] == "COLLECT_ITEMS":
                    item_types = goal["params"].get("item_types", [])
                    for item in market.get("selling", {}):
                        if any(t in item for t in item_types):
                            score += 1.0
                            break
                
                # Wealth seekers favor markets that buy their inventory
                elif goal["type"] in ["WEALTH", "RETIRE_WEALTHY"]:
                    inventory = self.trader.get_property("inventory", {})
                    for item, price in market.get("buying", {}).items():
                        if item in inventory and inventory[item] > 0:
                            score += min(1.0, (price / 100) * (inventory[item] / 10))
        
        return score
    
    def _get_trade_actions(self):
        """Get possible trade actions"""
        actions = []
        
        current_location = self.trader.get_property("current_location_id")
        if 'market_data' in self.world_info and current_location in self.world_info['market_data']:
            market = self.world_info['market_data'][current_location]
            
            # Get trader info
            gold = self.trader.get_property("gold", 0)
            inventory = self.trader.get_property("inventory", {})
            life_goals = self.trader.get_property("life_goals", [])
            
            # Buy actions
            for item, price in market.get('selling', {}).items():
                if gold >= price:
                    action = {
                        "type": "buy",
                        "item": item,
                        "price": price,
                        "location_id": current_location,
                        "score": 1.0
                    }
                    
                    # Adjust score based on life goals
                    for goal in life_goals:
                        if goal["type"] == "COLLECT_ITEMS":
                            item_types = goal["params"].get("item_types", [])
                            if any(t in item for t in item_types):
                                action["score"] += 2.0
                        
                        elif goal.get("is_retirement_goal", False):
                            progress = goal.get("progress", 0)
                            if progress > 50:
                                action["score"] -= 1.0
                    
                    actions.append(action)
            
            # Sell actions
            for item, quantity in inventory.items():
                if quantity > 0 and item in market.get('buying', {}):
                    price = market['buying'][item]
                    action = {
                        "type": "sell",
                        "item": item,
                        "price": price,
                        "location_id": current_location,
                        "score": 1.0
                    }
                    
                    # Adjust score based on life goals
                    for goal in life_goals:
                        if goal["type"] in ["WEALTH", "RETIRE_WEALTHY", "OPEN_SHOP", "FOUND_SETTLEMENT"]:
                            action["score"] += (price / 100) * 0.5
                        
                        elif goal["type"] == "COLLECT_ITEMS":
                            item_types = goal["params"].get("item_types", [])
                            if any(t in item for t in item_types):
                                action["score"] -= 1.5
                    
                    actions.append(action)
        
        return actions
    
    def apply_action(self, action):
        """Apply an action to create a new state"""
        new_state = self.clone()
        
        action_type = action["type"]
        
        if action_type == "move":
            new_state.trader.set_location(action["location_id"], "current")
            
        elif action_type == "buy":
            new_state.trader.remove_resource("gold", action["price"])
            new_state.trader.add_resource(action["item"], 1)
            
        elif action_type == "sell":
            new_state.trader.add_resource("gold", action["price"])
            new_state.trader.remove_resource(action["item"], 1)
            
        elif action_type == "rest":
            # Nothing changes
            pass
        
        # Clear cached actions for new state
        new_state._possible_actions = None
        
        return new_state
    
    def is_terminal(self):
        """Check if this is a terminal state"""
        # For simplicity, we'll say it's terminal if trader has achieved all life goals
        # or if they have no more actions
        
        goals = self.trader.get_property("life_goals", [])
        if goals and all(goal.get("completed", False) for goal in goals):
            return True
            
        # No actions available
        if not self.get_possible_actions():
            return True
            
        return False
    
    def get_reward(self):
        """Calculate reward value for state"""
        reward = 0.0
        
        # Gold reward
        gold = self.trader.get_property("gold", 0)
        reward += gold * 0.1
        
        # Inventory reward
        for item, quantity in self.trader.get_property("inventory", {}).items():
            reward += quantity * 0.05
        
        # Location preferences reward
        current_location = self.trader.get_property("current_location_id")
        preferred_settlements = self.trader.get_property("preferred_settlements", [])
        if current_location in preferred_settlements:
            reward += 2.0
            
        # Biome preferences
        if 'locations' in self.world_info and current_location in self.world_info['locations']:
            biome = self.world_info['locations'][current_location].get('biome')
            preferred_biomes = self.trader.get_property("preferred_biomes", [])
            if biome in preferred_biomes:
                reward += 1.5
        
        # Life goal reward
        life_goal_reward = self._get_life_goal_reward()
        reward += life_goal_reward
        
        return reward
    
    def _get_life_goal_reward(self):
        """Calculate reward contribution from life goals"""
        goals = self.trader.get_property("life_goals", [])
        if not goals:
            return 0.0
        
        # Calculate weighted average of goal progress
        total_weight = 0
        weighted_progress = 0
        
        for goal in goals:
            weight = 2.0 if goal.get("is_retirement_goal", False) else 1.0
            progress = goal.get("progress", 0)
            
            weighted_progress += progress * weight
            total_weight += weight
        
        # Convert to 0-1 scale
        avg_progress = weighted_progress / (total_weight * 100) if total_weight > 0 else 0
        
        # Scale for reward
        return avg_progress * 5.0
    
    def clone(self):
        """Create a deep copy of this state"""
        # Create a new trader with copied properties
        new_trader = Trader(self.trader.trader_id)
        new_trader.properties = {key: value for key, value in self.trader.properties.items()}
        
        # Create new state
        new_state = TraderState(
            new_trader,
            world_info=self.world_info.copy() if self.world_info else {},
            location_graph=self.location_graph.copy() if self.location_graph else {}
        )
        
        return new_state

# Simplified MCTS implementation for visualization
class MCTS:
    def __init__(self, exploration_weight=1.0):
        self.exploration_weight = exploration_weight
        self.nodes = {}  # Map from state to MCTSNode
        self.decision_stats = {}
        
    def search(self, root_state, get_legal_actions_fn, apply_action_fn, is_terminal_fn, get_reward_fn, num_simulations=100):
        """Run MCTS search and return best action"""
        # Create root node
        root_node = MCTSNode(root_state)
        root_node.untried_actions = get_legal_actions_fn(root_state)
        self.nodes[root_state] = root_node
        
        # Run simulations
        for _ in range(num_simulations):
            # Selection phase
            node = root_node
            state = root_state
            
            # Select until we reach a leaf node
            while not node.untried_actions and node.children:
                node = self.select_child(node)
                state = apply_action_fn(state, node.action)
            
            # Expansion phase
            if node.untried_actions:
                action = random.choice(node.untried_actions)
                node.untried_actions.remove(action)
                next_state = apply_action_fn(state, action)
                child = MCTSNode(next_state, node, action)
                child.untried_actions = get_legal_actions_fn(next_state)
                node.children.append(child)
                self.nodes[next_state] = child
                node = child
                state = next_state
            
            # Simulation phase
            while not is_terminal_fn(state):
                actions = get_legal_actions_fn(state)
                if not actions:
                    break
                action = random.choice(actions)
                state = apply_action_fn(state, action)
            
            # Backpropagation phase
            reward = get_reward_fn(state)
            while node is not None:
                node.visits += 1
                node.value += reward
                node = node.parent
        
        # Get best child from root
        best_child = self.select_best_child(root_node)
        best_action = best_child.action if best_child else None
        
        # Collect statistics
        self.decision_stats = {
            "simulations": num_simulations,
            "best_action": best_action,
            "action_stats": {}
        }
        
        # Collect stats for each action
        for child in root_node.children:
            action_str = self.action_to_string(child.action)
            self.decision_stats["action_stats"][action_str] = {
                "visits": child.visits,
                "average_value": child.value / child.visits if child.visits > 0 else 0,
                "score": child.action.get("score", 0) if isinstance(child.action, dict) else 0
            }
        
        return best_action
    
    def select_child(self, node):
        """Select best child using UCB1 formula"""
        log_visits = math.log(node.visits) if node.visits > 0 else 0
        
        def ucb_score(child):
            if child.visits == 0:
                return float('inf')
            
            # Exploitation term
            exploitation = child.value / child.visits
            
            # Exploration term
            exploration = self.exploration_weight * math.sqrt(log_visits / child.visits)
            
            # Add action score as a bias
            action_score = 0
            if isinstance(child.action, dict) and "score" in child.action:
                action_score = child.action["score"] * 0.2  # Scale down to not overwhelm UCB
                
            return exploitation + exploration + action_score
        
        return max(node.children, key=ucb_score)
    
    def select_best_child(self, node):
        """Select best child based on visits"""
        if not node.children:
            return None
            
        # Return child with most visits
        return max(node.children, key=lambda c: c.visits)
    
    def action_to_string(self, action):
        """Convert action to string representation"""
        if not action:
            return "None"
            
        if isinstance(action, dict):
            if action["type"] == "move":
                return f"Move to {action['location_id']}"
            elif action["type"] == "buy":
                return f"Buy {action['item']} for {action['price']}"
            elif action["type"] == "sell":
                return f"Sell {action['item']} for {action['price']}"
            elif action["type"] == "rest":
                return "Rest"
            return str(action)
        
        return str(action)

# Node for MCTS tree
class MCTSNode:
    def __init__(self, state, parent=None, action=None):
        self.state = state
        self.parent = parent
        self.action = action
        self.children = []
        self.visits = 0
        self.value = 0.0
        self.untried_actions = []

# Generate life goals for testing
def generate_life_goals(trader, include_retirement=True):
    """Add test life goals to a trader"""
    # Regular life goal - wealth accumulation
    wealth_goal = {
        "id": str(uuid.uuid4()),
        "type": "WEALTH",
        "name": "Wealth Accumulation",
        "description": "Accumulate 500 gold",
        "params": {"target_gold": 500},
        "progress": 0,
        "completed": False,
        "shared_at_reputation": 30,
        "created_at": datetime.now().isoformat()
    }
    
    # Regular life goal - visit settlements
    visit_goal = {
        "id": str(uuid.uuid4()),
        "type": "VISIT_SETTLEMENTS",
        "name": "World Explorer",
        "description": "Visit 3 unique settlements",
        "params": {"target_count": 3},
        "progress": 0,
        "completed": False,
        "shared_at_reputation": 20,
        "created_at": datetime.now().isoformat()
    }
    
    # Retirement goal
    shop_goal = {
        "id": str(uuid.uuid4()),
        "type": "OPEN_SHOP",
        "name": "Open Own Shop",
        "description": "Save 1000 gold to open a shop in a town",
        "params": {
            "target_gold": 1000,
            "preferred_settlement_types": ["town", "city"]
        },
        "progress": 0,
        "completed": False,
        "shared_at_reputation": 60,
        "is_retirement_goal": True,
        "created_at": datetime.now().isoformat()
    }
    
    # Add goals to trader
    goals = [wealth_goal, visit_goal]
    if include_retirement:
        goals.append(shop_goal)
        
    trader.set_property("life_goals", goals)
    return trader

# Update goal progress
def update_goal_progress(trader):
    """Update progress for trader goals"""
    goals = trader.get_property("life_goals", [])
    for goal in goals:
        if goal["completed"]:
            continue
            
        if goal["type"] == "WEALTH":
            current_gold = trader.get_property("gold", 0)
            target_gold = goal["params"]["target_gold"]
            goal["progress"] = min(100, int((current_gold / target_gold) * 100))
            if current_gold >= target_gold:
                goal["completed"] = True
                
        elif goal["type"] == "VISIT_SETTLEMENTS":
            visited = trader.get_property("visited_settlements", [])
            target_count = goal["params"]["target_count"]
            goal["progress"] = min(100, int((len(visited) / target_count) * 100))
            if len(visited) >= target_count:
                goal["completed"] = True
                
        elif goal["type"] == "OPEN_SHOP":
            current_gold = trader.get_property("gold", 0)
            target_gold = goal["params"]["target_gold"]
            goal["progress"] = min(100, int((current_gold / target_gold) * 100))
            if current_gold >= target_gold:
                goal["completed"] = True
                trader.set_property("can_retire", True)
    
    trader.set_property("life_goals", goals)
    return trader

# Create test world data
def create_test_world():
    """Create a test world with settlements, connections, and markets"""
    # Create settlements
    settlements = {
        "town1": {
            "id": "town1",
            "name": "Riverdale",
            "biome": "forest",
            "population": 500,
            "settlement_type": "town"
        },
        "village1": {
            "id": "village1",
            "name": "Oakvale",
            "biome": "forest",
            "population": 300,
            "settlement_type": "village"
        },
        "town2": {
            "id": "town2", 
            "name": "Dryfields",
            "biome": "plains",
            "population": 400,
            "settlement_type": "town"
        },
        "city1": {
            "id": "city1",
            "name": "Stonebridge",
            "biome": "mountains",
            "population": 700,
            "settlement_type": "city"
        }
    }
    
    # Create connections between settlements
    location_graph = {
        "town1": ["village1", "town2"],
        "village1": ["town1", "city1"],
        "town2": ["town1", "city1"],
        "city1": ["village1", "town2"]
    }
    
    # Create market data
    market_data = {
        "town1": {
            "buying": {"cloth": 12, "spices": 8},
            "selling": {"tools": 8, "food": 5}
        },
        "village1": {
            "buying": {"tools": 15},
            "selling": {"cloth": 5, "wood": 3}
        },
        "town2": {
            "buying": {"spices": 20},
            "selling": {"food": 4, "metal": 12}
        },
        "city1": {
            "buying": {"food": 8, "cloth": 10, "tools": 18},
            "selling": {"luxury_goods": 25, "spices": 15}
        }
    }
    
    # Create world data
    world_data = {
        "world_id": "test_world",
        "current_game_day": 42,
        "current_season": "summer",
        "locations": settlements,
        "market_data": market_data
    }
    
    return world_data, location_graph

# Visual representation of MCTS decision
def visualize_mcts_decision(trader, world_data, location_graph, action, stats):
    """Print a visual representation of MCTS decision"""
    print("\n" + "="*80)
    print(f"MCTS DECISION VISUALIZATION FOR TRADER: {trader.get_property('name')}")
    print("="*80)
    
    # Trader info
    print("\nTRADER STATE:")
    print(f"  Location: {trader.get_property('current_location_id')} ({world_data['locations'].get(trader.get_property('current_location_id'), {}).get('name', 'Unknown')})")
    print(f"  Gold: {trader.get_property('gold')}")
    print(f"  Inventory: {trader.get_property('inventory')}")
    print(f"  Visited: {trader.get_property('visited_settlements')}")
    
    # Life goals
    print("\nLIFE GOALS:")
    for goal in trader.get_property("life_goals", []):
        status = "✓" if goal.get("completed", False) else f"{goal.get('progress', 0)}%"
        retirement = " (Retirement Goal)" if goal.get("is_retirement_goal", False) else ""
        print(f"  {goal['name']}{retirement}: {status}")
        print(f"    Description: {goal['description']}")
        if not goal.get("completed", False):
            if goal["type"] == "WEALTH" or goal["type"] == "OPEN_SHOP":
                current = trader.get_property("gold", 0)
                target = goal["params"].get("target_gold", 0)
                remaining = max(0, target - current)
                print(f"    Progress: {current}/{target} gold ({remaining} remaining)")
            elif goal["type"] == "VISIT_SETTLEMENTS":
                current = len(trader.get_property("visited_settlements", []))
                target = goal["params"].get("target_count", 0)
                remaining = max(0, target - current)
                print(f"    Progress: {current}/{target} settlements ({remaining} remaining)")
    
    # Actions considered
    print("\nACTIONS CONSIDERED:")
    
    # Sort actions by visits (most visited first)
    sorted_actions = sorted(
        stats.get("action_stats", {}).items(),
        key=lambda x: x[1].get("visits", 0),
        reverse=True
    )
    
    # Display the top 5 actions
    for i, (action_str, action_stats) in enumerate(sorted_actions[:5]):
        visits = action_stats.get("visits", 0)
        avg_value = action_stats.get("average_value", 0)
        action_score = action_stats.get("score", 0)
        
        # Calculate percentage of visits
        total_visits = sum(act.get("visits", 0) for act in stats.get("action_stats", {}).values())
        visit_pct = (visits / total_visits * 100) if total_visits > 0 else 0
        
        # Visual bar for relative preference
        bar_length = int(visit_pct / 2)  # Scale to max 50 chars
        bar = "█" * bar_length
        
        print(f"  {i+1}. {action_str}")
        print(f"     Visits: {visits} ({visit_pct:.1f}%) {bar}")
        print(f"     Value: {avg_value:.2f}, Action Score: {action_score:.2f}")
    
    # Best action
    if action:
        print("\nBEST ACTION CHOSEN:")
        action_type = action.get("type", "unknown")
        
        if action_type == "move":
            location_id = action.get("location_id", "unknown")
            location_name = world_data.get("locations", {}).get(location_id, {}).get("name", "Unknown")
            settlement_type = world_data.get("locations", {}).get(location_id, {}).get("settlement_type", "unknown")
            biome = world_data.get("locations", {}).get(location_id, {}).get("biome", "unknown")
            
            print(f"  Move to {location_name} ({location_id})")
            print(f"  Settlement Type: {settlement_type}")
            print(f"  Biome: {biome}")
            
            # Explain the decision
            reasons = []
            
            # Check if this is a new settlement (exploration)
            if location_id not in trader.get_property("visited_settlements", []):
                for goal in trader.get_property("life_goals", []):
                    if goal["type"] == "VISIT_SETTLEMENTS":
                        reasons.append("Helps complete the World Explorer goal by visiting a new settlement")
                        break
            
            # Check if biome is preferred
            if biome in trader.get_property("preferred_biomes", []):
                reasons.append(f"The {biome} biome is preferred by this trader")
            
            # Check shop goal
            for goal in trader.get_property("life_goals", []):
                if goal["type"] == "OPEN_SHOP":
                    preferred_types = goal["params"].get("preferred_settlement_types", [])
                    if settlement_type in preferred_types:
                        reasons.append(f"This {settlement_type} is a potential location for opening a shop (retirement goal)")
            
            # Check market opportunities
            if location_id in world_data.get("market_data", {}):
                market = world_data["market_data"][location_id]
                
                # Check selling opportunities
                inventory = trader.get_property("inventory", {})
                for item in inventory:
                    if item in market.get("buying", {}):
                        price = market["buying"][item]
                        reasons.append(f"Can sell {item} for {price} gold")
                
                # Check buying opportunities that match collection goals
                for goal in trader.get_property("life_goals", []):
                    if goal["type"] == "COLLECT_ITEMS":
                        item_types = goal["params"].get("item_types", [])
                        for item in market.get("selling", {}):
                            if any(t in item for t in item_types):
                                reasons.append(f"Market sells items needed for collection goal")
                                break
            
            if reasons:
                print("\n  Decision Factors:")
                for reason in reasons:
                    print(f"  - {reason}")
            
        elif action_type == "buy":
            item = action.get("item", "unknown")
            price = action.get("price", 0)
            print(f"  Buy {item} for {price} gold")
            
            # Explain purchase decision
            reasons = []
            for goal in trader.get_property("life_goals", []):
                if goal["type"] == "COLLECT_ITEMS" and "item_types" in goal["params"]:
                    if any(t in item for t in goal["params"]["item_types"]):
                        reasons.append(f"This item helps complete the {goal['name']} goal")
            
            if reasons:
                print("\n  Decision Factors:")
                for reason in reasons:
                    print(f"  - {reason}")
            
        elif action_type == "sell":
            item = action.get("item", "unknown")
            price = action.get("price", 0)
            print(f"  Sell {item} for {price} gold")
            
            # Explain sell decision
            reasons = []
            for goal in trader.get_property("life_goals", []):
                if goal["type"] in ["WEALTH", "OPEN_SHOP", "RETIRE_WEALTHY"]:
                    target_gold = goal["params"].get("target_gold", 0)
                    current_gold = trader.get_property("gold", 0)
                    remaining = target_gold - current_gold
                    if remaining > 0:
                        reasons.append(f"Selling helps reach {goal['name']} goal ({current_gold}/{target_gold} gold)")
            
            if reasons:
                print("\n  Decision Factors:")
                for reason in reasons:
                    print(f"  - {reason}")
            
        elif action_type == "rest":
            print("  Rest at current location")
    else:
        print("\nNo action chosen.")
    
    print("\n" + "="*80)

# Run a simulation for several days
def run_simulation(num_days=5):
    """Run a simulation for multiple days to show how life goals affect decisions"""
    import math  # Import here to avoid global import issue
    
    print("Running MCTS Trader Life Goals Simulation\n")
    
    # Create test trader
    trader = Trader(str(uuid.uuid4()))
    trader.set_property("name", "Eldric the Trader")
    trader.set_property("gold", 100)
    trader.set_property("preferred_biomes", ["forest", "plains"])
    
    # Add life goals
    trader = generate_life_goals(trader)
    
    # Create test world
    world_data, location_graph = create_test_world()
    
    # Start at town1
    trader.set_location("town1")
    
    # Run simulation for several days
    for day in range(1, num_days + 1):
        print(f"\n\n===== DAY {day} =====")
        
        # Update goal progress
        trader = update_goal_progress(trader)
        
        # Check if trader can retire
        if trader.get_property("can_retire", False):
            retire_chance = 0.3
            if random.random() < retire_chance:
                print(f"\n{trader.get_property('name')} has decided to retire!")
                shop_name = f"{trader.get_property('name')}'s Trading Post"
                current_location = trader.get_property("current_location_id")
                print(f"Opening shop '{shop_name}' in {world_data['locations'][current_location]['name']}")
                break
        
        # Create state
        state = TraderState(trader, world_data, location_graph)
        
        # Run MCTS search
        mcts = MCTS(exploration_weight=1.0)
        action = mcts.search(
            root_state=state,
            get_legal_actions_fn=lambda s: s.get_possible_actions(),
            apply_action_fn=lambda s, a: s.apply_action(a),
            is_terminal_fn=lambda s: s.is_terminal(),
            get_reward_fn=lambda s: s.get_reward(),
            num_simulations=50  # Reduced from 200 for faster execution
        )
        
        # Visualize decision
        visualize_mcts_decision(trader, world_data, location_graph, action, mcts.decision_stats)
        
        # Apply decision
        if action:
            action_type = action.get("type", "")
            
            if action_type == "move":
                location_id = action.get("location_id", "")
                location_name = world_data["locations"].get(location_id, {}).get("name", "Unknown")
                print(f"\nTrader moves to {location_name}")
                trader.set_location(location_id)
                
            elif action_type == "buy":
                item = action.get("item", "")
                price = action.get("price", 0)
                trader.remove_resource("gold", price)
                trader.add_resource(item, 1)
                print(f"\nTrader buys {item} for {price} gold")
                
            elif action_type == "sell":
                item = action.get("item", "")
                price = action.get("price", 0)
                trader.remove_resource(item, 1)
                trader.add_resource("gold", price)
                print(f"\nTrader sells {item} for {price} gold")
                
                # Record trade
                trades = trader.get_property("total_trades", 0)
                trader.set_property("total_trades", trades + 1)
                
            elif action_type == "rest":
                print("\nTrader rests at current location")
        
        # Simulate some random market changes
        market = world_data["market_data"].get(trader.get_property("current_location_id"), {})
        for category in ["buying", "selling"]:
            for item in list(market.get(category, {}).keys()):
                # 10% chance to adjust price
                if random.random() < 0.1:
                    current_price = market[category][item]
                    adjustment = random.uniform(0.9, 1.1)
                    market[category][item] = int(current_price * adjustment)
        
        # Every 2nd day, add a new item to trader's inventory (simulating production/finds)
        if day % 2 == 0:
            new_items = ["cloth", "spices", "tools", "food", "wood", "metal"]
            trader.add_resource(random.choice(new_items), 1)
            
        # End day - add a small amount of gold (simulating other minor trades)
        trader.add_resource("gold", random.randint(5, 15))

# Main function
if __name__ == "__main__":
    # Run a shorter simulation
    run_simulation(num_days=3)