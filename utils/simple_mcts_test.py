#!/usr/bin/env python3
"""
Simplified MCTS test to demonstrate trader life goals.
This script shows how trader's life goals influence MCTS decision making.
"""

import random
import uuid
from typing import Dict, List, Any

# Create a test trader
class TestTrader:
    def __init__(self, name):
        self.id = str(uuid.uuid4())
        self.name = name
        self.gold = 100
        self.inventory = {"cloth": 5, "spices": 3, "tools": 2}
        self.current_location = "town1"
        self.visited_locations = ["town1"]
        self.preferred_biomes = ["forest", "plains"]
        self.life_goals = []
        
    def add_life_goal(self, goal_type, name, description, params, is_retirement=False):
        """Add a life goal to the trader"""
        goal = {
            "id": str(uuid.uuid4()),
            "type": goal_type,
            "name": name,
            "description": description,
            "params": params,
            "progress": 0,
            "completed": False,
            "is_retirement_goal": is_retirement
        }
        self.life_goals.append(goal)
        
    def update_goal_progress(self):
        """Update progress for all goals"""
        for goal in self.life_goals:
            if goal["completed"]:
                continue
                
            if goal["type"] == "WEALTH":
                target = goal["params"]["target_gold"]
                goal["progress"] = min(100, int((self.gold / target) * 100))
                if self.gold >= target:
                    goal["completed"] = True
                    
            elif goal["type"] == "VISIT_SETTLEMENTS":
                target = goal["params"]["target_count"]
                goal["progress"] = min(100, int((len(self.visited_locations) / target) * 100))
                if len(self.visited_locations) >= target:
                    goal["completed"] = True
                    
            elif goal["type"] == "OPEN_SHOP":
                target = goal["params"]["target_gold"]
                goal["progress"] = min(100, int((self.gold / target) * 100))
                if self.gold >= target:
                    goal["completed"] = True

# Create test world data
def create_test_world():
    """Create test world with settlements, connections and markets"""
    world = {
        "settlements": {
            "town1": {
                "name": "Riverdale",
                "biome": "forest",
                "type": "town",
                "population": 500
            },
            "village1": {
                "name": "Oakvale",
                "biome": "forest",
                "type": "village",
                "population": 300
            },
            "town2": {
                "name": "Dryfields",
                "biome": "plains",
                "type": "town",
                "population": 400
            },
            "city1": {
                "name": "Stonebridge",
                "biome": "mountains",
                "type": "city",
                "population": 700
            }
        },
        "connections": {
            "town1": ["village1", "town2"],
            "village1": ["town1", "city1"],
            "town2": ["town1", "city1"],
            "city1": ["village1", "town2"]
        },
        "markets": {
            "town1": {
                "buys": {"cloth": 12, "spices": 8},
                "sells": {"tools": 8, "food": 5}
            },
            "village1": {
                "buys": {"tools": 15},
                "sells": {"cloth": 5, "wood": 3}
            },
            "town2": {
                "buys": {"spices": 20},
                "sells": {"food": 4, "metal": 12}
            },
            "city1": {
                "buys": {"food": 8, "cloth": 10, "tools": 18},
                "sells": {"luxury_goods": 25, "spices": 15}
            }
        }
    }
    return world

# Generate possible actions
def generate_actions(trader, world):
    """Generate possible actions for a trader in the world"""
    actions = []
    current_location = trader.current_location
    
    # Movement actions
    if current_location in world["connections"]:
        for destination in world["connections"][current_location]:
            action = {
                "type": "move",
                "destination": destination,
                "score": score_location(trader, destination, world)
            }
            actions.append(action)
    
    # Trading actions
    if current_location in world["markets"]:
        market = world["markets"][current_location]
        
        # Buy actions
        for item, price in market["sells"].items():
            if trader.gold >= price:
                action = {
                    "type": "buy",
                    "item": item,
                    "price": price,
                    "score": score_buy_action(trader, item, price)
                }
                actions.append(action)
        
        # Sell actions
        for item, qty in trader.inventory.items():
            if qty > 0 and item in market["buys"]:
                price = market["buys"][item]
                action = {
                    "type": "sell",
                    "item": item,
                    "price": price,
                    "score": score_sell_action(trader, item, price)
                }
                actions.append(action)
    
    return actions

# Score location for movement
def score_location(trader, location_id, world):
    """Score a location based on trader preferences and life goals"""
    score = 1.0  # Base score
    
    # Get location info
    location = world["settlements"].get(location_id, {})
    biome = location.get("biome", "unknown")
    settlement_type = location.get("type", "unknown")
    
    # Biome preference
    if biome in trader.preferred_biomes:
        score += 1.5
    
    # Previously visited penalty
    if location_id in trader.visited_locations:
        score -= 0.5
    
    # Life goal considerations
    for goal in trader.life_goals:
        # Visit settlements goal favors unvisited places
        if goal["type"] == "VISIT_SETTLEMENTS" and location_id not in trader.visited_locations:
            score += 1.0
            
        # Open shop goal favors preferred settlement types
        elif goal["type"] == "OPEN_SHOP":
            preferred_types = goal["params"].get("preferred_settlement_types", [])
            if settlement_type in preferred_types:
                score += 1.5
                
                # Extra bonus if close to goal
                if trader.gold >= goal["params"]["target_gold"] * 0.8:
                    score += 1.0
        
        # Market opportunities
        if location_id in world["markets"]:
            market = world["markets"][location_id]
            
            # Wealth goals favor markets that buy our inventory
            if goal["type"] in ["WEALTH", "RETIRE_WEALTHY", "OPEN_SHOP"]:
                for item, qty in trader.inventory.items():
                    if item in market["buys"] and qty > 0:
                        price = market["buys"][item]
                        score += min(1.0, price / 10)
    
    return score

# Score buy action
def score_buy_action(trader, item, price):
    """Score a buy action based on trader goals"""
    score = 1.0  # Base score
    
    # If saving up for retirement goal, reduce desire to spend
    for goal in trader.life_goals:
        if goal["is_retirement_goal"] and goal["progress"] > 50:
            score -= 1.0  # Significant penalty when near retirement goal
    
    return score

# Score sell action
def score_sell_action(trader, item, price):
    """Score a sell action based on trader goals"""
    score = 1.0  # Base score
    
    # Wealth-focused goals favor selling
    for goal in trader.life_goals:
        if goal["type"] in ["WEALTH", "RETIRE_WEALTHY", "OPEN_SHOP"]:
            score += 0.5  # Small bonus for all sales
            
            # Higher price = higher score
            score += (price / 20)
    
    return score

# Simulate MCTS decision (simplified)
def simulate_mcts_decision(trader, world, num_simulations=100):
    """Simulate MCTS decision process (simplified for demonstration)"""
    actions = generate_actions(trader, world)
    
    if not actions:
        return None, {}
    
    # For each action, run simulations and track reward
    action_stats = {}
    for action in actions:
        action_str = action_to_string(action)
        action_stats[action_str] = {
            "visits": 0,
            "total_reward": 0,
            "avg_reward": 0
        }
        
        # Run simulations for this action
        for _ in range(num_simulations):
            reward = simulate_single_action(trader, action, world)
            action_stats[action_str]["visits"] += 1
            action_stats[action_str]["total_reward"] += reward
        
        # Calculate average reward
        action_stats[action_str]["avg_reward"] = (
            action_stats[action_str]["total_reward"] / action_stats[action_str]["visits"]
        )
    
    # Find best action
    best_action = max(actions, key=lambda a: action_stats[action_to_string(a)]["avg_reward"])
    
    return best_action, action_stats

# Simulate a single action
def simulate_single_action(trader, action, world):
    """Simulate the outcome of taking a single action"""
    # Clone trader to avoid modifying original
    sim_trader = TestTrader(trader.name)
    sim_trader.gold = trader.gold
    sim_trader.inventory = trader.inventory.copy()
    sim_trader.current_location = trader.current_location
    sim_trader.visited_locations = list(trader.visited_locations)
    sim_trader.preferred_biomes = list(trader.preferred_biomes)
    sim_trader.life_goals = [goal.copy() for goal in trader.life_goals]
    
    # Apply action
    if action["type"] == "move":
        sim_trader.current_location = action["destination"]
        if action["destination"] not in sim_trader.visited_locations:
            sim_trader.visited_locations.append(action["destination"])
    
    elif action["type"] == "buy":
        sim_trader.gold -= action["price"]
        sim_trader.inventory[action["item"]] = sim_trader.inventory.get(action["item"], 0) + 1
    
    elif action["type"] == "sell":
        sim_trader.gold += action["price"]
        sim_trader.inventory[action["item"]] -= 1
        if sim_trader.inventory[action["item"]] <= 0:
            del sim_trader.inventory[action["item"]]
    
    # Update goals
    sim_trader.update_goal_progress()
    
    # Calculate reward (simplified)
    reward = calculate_reward(sim_trader)
    
    return reward

# Calculate reward
def calculate_reward(trader):
    """Calculate reward for trader state"""
    reward = 0.0
    
    # Gold reward
    reward += trader.gold * 0.1
    
    # Inventory reward
    for item, qty in trader.inventory.items():
        reward += qty * 0.05
    
    # Life goal reward
    for goal in trader.life_goals:
        # Regular goals
        if not goal["is_retirement_goal"]:
            reward += goal["progress"] * 0.03
        else:
            # Retirement goals weighted higher
            reward += goal["progress"] * 0.06
        
        # Completed goals bonus
        if goal["completed"]:
            reward += 5.0
    
    return reward

# Convert action to string
def action_to_string(action):
    """Convert action dictionary to string representation"""
    if action["type"] == "move":
        return f"Move to {action['destination']}"
    elif action["type"] == "buy":
        return f"Buy {action['item']} for {action['price']} gold"
    elif action["type"] == "sell":
        return f"Sell {action['item']} for {action['price']} gold"
    return str(action)

# Print visual results
def print_mcts_results(trader, world, best_action, action_stats):
    """Print visual representation of MCTS decision making"""
    print("\n" + "="*80)
    print(f"MCTS DECISION MAKING FOR TRADER: {trader.name}")
    print("="*80)
    
    # Trader info
    print("\nTRADER STATE:")
    current_settlement = world["settlements"][trader.current_location]["name"]
    print(f"  Location: {current_settlement} ({trader.current_location})")
    print(f"  Gold: {trader.gold}")
    print(f"  Inventory: {trader.inventory}")
    print(f"  Visited: {trader.visited_locations}")
    
    # Life goals
    print("\nLIFE GOALS:")
    for goal in trader.life_goals:
        status = "✓" if goal["completed"] else f"{goal['progress']}%"
        retirement = " (Retirement Goal)" if goal["is_retirement_goal"] else ""
        print(f"  {goal['name']}{retirement}: {status}")
        print(f"    Description: {goal['description']}")
        
        if not goal["completed"]:
            if goal["type"] == "WEALTH" or goal["type"] == "OPEN_SHOP":
                target = goal["params"]["target_gold"]
                remaining = max(0, target - trader.gold)
                print(f"    Progress: {trader.gold}/{target} gold ({remaining} remaining)")
            elif goal["type"] == "VISIT_SETTLEMENTS":
                target = goal["params"]["target_count"]
                current = len(trader.visited_locations)
                remaining = max(0, target - current)
                print(f"    Progress: {current}/{target} settlements ({remaining} remaining)")
    
    # Actions considered
    print("\nACTIONS CONSIDERED:")
    # Sort actions by average reward
    sorted_actions = sorted(
        action_stats.items(),
        key=lambda x: x[1]["avg_reward"],
        reverse=True
    )
    
    for action_str, stats in sorted_actions[:5]:  # Show top 5
        visits = stats["visits"]
        avg_reward = stats["avg_reward"]
        
        # Visual bar for preference
        bar_length = int(avg_reward * 2)
        bar = "#" * bar_length
        
        print(f"  {action_str}")
        print(f"    Avg Reward: {avg_reward:.2f} {bar}")
        print(f"    Simulations: {visits}")
    
    # Best action
    print("\nBEST ACTION CHOSEN:")
    if best_action:
        action_str = action_to_string(best_action)
        print(f"  {action_str}")
        
        # Explain decision
        print("\n  Decision Factors:")
        
        if best_action["type"] == "move":
            destination = best_action["destination"]
            settlement = world["settlements"][destination]
            
            # Check if this is a new settlement (exploration)
            if destination not in trader.visited_locations:
                for goal in trader.life_goals:
                    if goal["type"] == "VISIT_SETTLEMENTS":
                        print(f"  - Helps complete the World Explorer goal by visiting a new settlement")
                        break
            
            # Check biome preference
            if settlement["biome"] in trader.preferred_biomes:
                print(f"  - The {settlement['biome']} biome is preferred by this trader")
            
            # Check shop goal
            for goal in trader.life_goals:
                if goal["type"] == "OPEN_SHOP":
                    preferred_types = goal["params"].get("preferred_settlement_types", [])
                    if settlement["type"] in preferred_types:
                        print(f"  - This {settlement['type']} is a potential location for opening a shop (retirement goal)")
            
            # Check market opportunities
            if destination in world["markets"]:
                market = world["markets"][destination]
                
                for item, qty in trader.inventory.items():
                    if item in market["buys"] and qty > 0:
                        price = market["buys"][item]
                        print(f"  - Can sell {item} for {price} gold")
        
        elif best_action["type"] == "sell":
            item = best_action["item"]
            price = best_action["price"]
            
            # Check wealth/retirement goals
            for goal in trader.life_goals:
                if goal["type"] in ["WEALTH", "OPEN_SHOP"]:
                    target_gold = goal["params"]["target_gold"]
                    print(f"  - Selling helps reach {goal['name']} goal ({trader.gold}/{target_gold} gold)")
        
        elif best_action["type"] == "buy":
            item = best_action["item"]
            
            # Check if buying for collection goals
            for goal in trader.life_goals:
                if goal["type"] == "COLLECT_ITEMS" and "item_types" in goal["params"]:
                    for item_type in goal["params"]["item_types"]:
                        if item_type in item:
                            print(f"  - This item helps complete the {goal['name']} goal")
    else:
        print("  No action chosen")
    
    print("\n" + "="*80)

# Main function
def main():
    # Create test world
    world = create_test_world()
    
    # Show beginning trader state
    trader = TestTrader("Eldric the Trader")
    
    # Add life goals
    trader.add_life_goal(
        "WEALTH",
        "Wealth Accumulation",
        "Accumulate 500 gold",
        {"target_gold": 500}
    )
    
    trader.add_life_goal(
        "VISIT_SETTLEMENTS",
        "World Explorer",
        "Visit 3 unique settlements",
        {"target_count": 3}
    )
    
    trader.add_life_goal(
        "OPEN_SHOP",
        "Open Own Shop",
        "Save 1000 gold to open a shop in a town",
        {"target_gold": 1000, "preferred_settlement_types": ["town", "city"]},
        is_retirement=True
    )
    
    # Update goals
    trader.update_goal_progress()
    
    print("==== BEGINNING STAGE: New Trader ====")
    # Run simplified MCTS
    best_action, action_stats = simulate_mcts_decision(trader, world, num_simulations=50)
    
    # Print results
    print_mcts_results(trader, world, best_action, action_stats)
    
    # Now simulate a trader who has made progress on the WEALTH goal
    print("\n\n==== MIDDLE STAGE: Progress on Wealth Goal ====")
    trader_mid = TestTrader("Eldric the Trader")
    trader_mid.gold = 450  # Close to completing wealth goal
    trader_mid.inventory = {"cloth": 2, "spices": 1, "tools": 3}
    trader_mid.current_location = "town1"
    trader_mid.visited_locations = ["town1", "village1"]  # Visited 2 of 3 needed
    
    # Add same life goals
    trader_mid.add_life_goal(
        "WEALTH",
        "Wealth Accumulation",
        "Accumulate 500 gold",
        {"target_gold": 500}
    )
    
    trader_mid.add_life_goal(
        "VISIT_SETTLEMENTS",
        "World Explorer",
        "Visit 3 unique settlements",
        {"target_count": 3}
    )
    
    trader_mid.add_life_goal(
        "OPEN_SHOP",
        "Open Own Shop",
        "Save 1000 gold to open a shop in a town",
        {"target_gold": 1000, "preferred_settlement_types": ["town", "city"]},
        is_retirement=True
    )
    
    # Update goals
    trader_mid.update_goal_progress()
    
    # Run MCTS for mid-stage trader
    best_action_mid, action_stats_mid = simulate_mcts_decision(trader_mid, world, num_simulations=50)
    print_mcts_results(trader_mid, world, best_action_mid, action_stats_mid)
    
    # Finally, simulate a trader who is close to retirement
    print("\n\n==== LATE STAGE: Close to Retirement Goal ====")
    trader_late = TestTrader("Eldric the Trader")
    trader_late.gold = 850  # Very close to retirement goal
    trader_late.inventory = {"cloth": 3, "spices": 2, "luxury_goods": 1}
    trader_late.current_location = "village1"
    trader_late.visited_locations = ["town1", "village1", "town2"]  # Completed exploration
    
    # Add same life goals
    trader_late.add_life_goal(
        "WEALTH",
        "Wealth Accumulation",
        "Accumulate 500 gold",
        {"target_gold": 500}
    )
    
    trader_late.add_life_goal(
        "VISIT_SETTLEMENTS",
        "World Explorer",
        "Visit 3 unique settlements",
        {"target_count": 3}
    )
    
    trader_late.add_life_goal(
        "OPEN_SHOP",
        "Open Own Shop",
        "Save 1000 gold to open a shop in a town",
        {"target_gold": 1000, "preferred_settlement_types": ["town", "city"]},
        is_retirement=True
    )
    
    # Update goals
    trader_late.update_goal_progress()
    
    # Run MCTS for late-stage trader
    best_action_late, action_stats_late = simulate_mcts_decision(trader_late, world, num_simulations=50)
    print_mcts_results(trader_late, world, best_action_late, action_stats_late)

if __name__ == "__main__":
    main()