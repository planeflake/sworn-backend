#!/usr/bin/env python
# utils/add_trader_life_goals.py
"""
Utility script to add life goals and retirement goals to traders.

Life goals provide motivation for trader behavior and are used in MCTS decision making.
Some goals are shared with players who have sufficient reputation with the trader.
Retirement goals are special life goals that, when achieved, can end a trader's career.
"""

import sys
import os
import logging
import json
import random
import uuid
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import required components
from database.connection import SessionLocal
from app.game_state.entities.trader import Trader
from app.game_state.managers.trader_manager import TraderManager
from app.models.core import Traders, Settlements, Worlds

# Define life goal types
LIFE_GOAL_TYPES = {
    # Regular Life Goals
    "WEALTH": {
        "name": "Wealth Accumulation",
        "description": "Accumulate a specific amount of gold",
        "params": {"target_gold": (1000, 10000)},  # Range for random generation
        "shared_at_reputation": 30,  # Min reputation to share this goal with player
        "retirement_goal": False
    },
    "VISIT_SETTLEMENTS": {
        "name": "World Explorer",
        "description": "Visit a specific number of unique settlements",
        "params": {"target_count": (5, 20)},
        "shared_at_reputation": 20,
        "retirement_goal": False
    },
    "COLLECT_ITEMS": {
        "name": "Item Collector",
        "description": "Collect specific rare items",
        "params": {"item_types": ["luxury", "rare", "artifact"], "target_count": (3, 10)},
        "shared_at_reputation": 40,
        "retirement_goal": False
    },
    "TRADING_VOLUME": {
        "name": "Master Trader",
        "description": "Complete a specific volume of trades",
        "params": {"target_volume": (50, 500)},
        "shared_at_reputation": 25,
        "retirement_goal": False
    },
    "SPECIFIC_SETTLEMENT": {
        "name": "Settlement Seeker",
        "description": "Find and visit a specific settlement",
        "params": {"settlement_type": ["city", "capital", "hidden"]},
        "shared_at_reputation": 35,
        "retirement_goal": False
    },
    
    # Retirement Goals
    "OPEN_SHOP": {
        "name": "Open Own Shop",
        "description": "Save enough gold to open a shop in a specific settlement",
        "params": {
            "target_gold": (2000, 20000),  # Base cost varies by settlement size
            "preferred_settlement_types": ["town", "city"]
        },
        "shared_at_reputation": 60,
        "retirement_goal": True
    },
    "RETIRE_WEALTHY": {
        "name": "Retire Wealthy",
        "description": "Accumulate enough wealth to retire comfortably",
        "params": {"target_gold": (5000, 50000)},
        "shared_at_reputation": 50,
        "retirement_goal": True
    },
    "FOUND_SETTLEMENT": {
        "name": "Found New Settlement",
        "description": "Gather resources and gold to found a new settlement",
        "params": {
            "target_gold": (10000, 100000),
            "required_resources": {"wood": 1000, "stone": 500, "food": 2000}
        },
        "shared_at_reputation": 75,
        "retirement_goal": True
    },
    "FIND_ARTIFACT": {
        "name": "Find Legendary Artifact",
        "description": "Find a specific legendary artifact to retire in fame",
        "params": {"artifact_difficulty": (3, 10)},
        "shared_at_reputation": 80,
        "retirement_goal": True
    }
}

def generate_life_goal_params(goal_type: str) -> Dict[str, Any]:
    """Generate random parameters for a life goal based on its type"""
    goal_template = LIFE_GOAL_TYPES.get(goal_type)
    if not goal_template:
        raise ValueError(f"Unknown life goal type: {goal_type}")
    
    params = {}
    template_params = goal_template["params"]
    
    for key, value in template_params.items():
        if isinstance(value, tuple) and len(value) == 2:
            # This is a range for random generation
            min_val, max_val = value
            params[key] = random.randint(min_val, max_val)
        elif isinstance(value, list):
            # This is a list of choices
            params[key] = random.choice(value)
        else:
            # Direct value
            params[key] = value
    
    return params

async def add_life_goals_to_trader(trader: Trader, num_goals: int = 2, require_retirement: bool = True) -> Trader:
    """
    Add life goals to a trader entity.
    
    Args:
        trader: The trader entity to modify
        num_goals: Number of regular life goals to add (default 2)
        require_retirement: Whether to ensure at least one retirement goal (default True)
        
    Returns:
        The updated trader entity
    """
    # Get existing life goals if any
    existing_goals = trader.get_property("life_goals", [])
    
    # Separate goal types into regular and retirement
    regular_goals = [gt for gt, info in LIFE_GOAL_TYPES.items() if not info["retirement_goal"]]
    retirement_goals = [gt for gt, info in LIFE_GOAL_TYPES.items() if info["retirement_goal"]]
    
    # Generate regular life goals
    for _ in range(num_goals):
        goal_type = random.choice(regular_goals)
        goal_template = LIFE_GOAL_TYPES[goal_type]
        params = generate_life_goal_params(goal_type)
        
        goal = {
            "id": str(uuid.uuid4()),
            "type": goal_type,
            "name": goal_template["name"],
            "description": goal_template["description"],
            "params": params,
            "progress": 0,
            "completed": False,
            "shared_at_reputation": goal_template["shared_at_reputation"],
            "created_at": datetime.now().isoformat()
        }
        
        existing_goals.append(goal)
    
    # Generate a retirement goal if required
    if require_retirement:
        retirement_type = random.choice(retirement_goals)
        retirement_template = LIFE_GOAL_TYPES[retirement_type]
        retirement_params = generate_life_goal_params(retirement_type)
        
        retirement_goal = {
            "id": str(uuid.uuid4()),
            "type": retirement_type,
            "name": retirement_template["name"],
            "description": retirement_template["description"],
            "params": retirement_params,
            "progress": 0,
            "completed": False,
            "shared_at_reputation": retirement_template["shared_at_reputation"],
            "is_retirement_goal": True,
            "created_at": datetime.now().isoformat()
        }
        
        existing_goals.append(retirement_goal)
    
    # Update trader's life goals
    trader.set_property("life_goals", existing_goals)
    return trader

async def check_life_goal_progress(trader: Trader) -> Trader:
    """
    Check and update progress toward life goals based on trader's current state.
    
    Args:
        trader: The trader entity to update
        
    Returns:
        The updated trader entity with goal progress
    """
    goals = trader.get_property("life_goals", [])
    
    for goal in goals:
        if goal["completed"]:
            continue
            
        goal_type = goal["type"]
        params = goal["params"]
        
        # Calculate progress based on goal type
        if goal_type == "WEALTH":
            current_gold = trader.get_property("gold", 0)
            target_gold = params.get("target_gold", 1000)
            goal["progress"] = min(100, int((current_gold / target_gold) * 100))
            if current_gold >= target_gold:
                goal["completed"] = True
                
        elif goal_type == "VISIT_SETTLEMENTS":
            visited = trader.get_property("visited_settlements", [])
            target_count = params.get("target_count", 10)
            goal["progress"] = min(100, int((len(visited) / target_count) * 100))
            if len(visited) >= target_count:
                goal["completed"] = True
                
        elif goal_type == "COLLECT_ITEMS":
            inventory = trader.get_property("inventory", {})
            collected_items = sum(1 for item, count in inventory.items() 
                              if any(t in item for t in params.get("item_types", [])))
            target_count = params.get("target_count", 5)
            goal["progress"] = min(100, int((collected_items / target_count) * 100))
            if collected_items >= target_count:
                goal["completed"] = True
                
        elif goal_type == "TRADING_VOLUME":
            trade_count = trader.get_property("total_trades", 0)
            target_volume = params.get("target_volume", 100)
            goal["progress"] = min(100, int((trade_count / target_volume) * 100))
            if trade_count >= target_volume:
                goal["completed"] = True
                
        elif goal_type == "SPECIFIC_SETTLEMENT":
            visited = trader.get_property("visited_settlements", [])
            target_settlement = params.get("target_settlement_id")
            if target_settlement in visited:
                goal["progress"] = 100
                goal["completed"] = True
            else:
                goal["progress"] = 0
                
        elif goal_type == "OPEN_SHOP":
            current_gold = trader.get_property("gold", 0)
            target_gold = params.get("target_gold", 5000)
            goal["progress"] = min(100, int((current_gold / target_gold) * 100))
            if current_gold >= target_gold:
                goal["completed"] = True
                # When completed, trader can retire to open shop
                trader.set_property("can_retire", True)
                
        elif goal_type == "RETIRE_WEALTHY":
            current_gold = trader.get_property("gold", 0)
            target_gold = params.get("target_gold", 20000)
            goal["progress"] = min(100, int((current_gold / target_gold) * 100))
            if current_gold >= target_gold:
                goal["completed"] = True
                trader.set_property("can_retire", True)
                
        elif goal_type == "FOUND_SETTLEMENT":
            # Check gold and resources
            current_gold = trader.get_property("gold", 0)
            inventory = trader.get_property("inventory", {})
            target_gold = params.get("target_gold", 50000)
            required_resources = params.get("required_resources", {})
            
            gold_progress = min(100, int((current_gold / target_gold) * 100))
            resource_progress = []
            
            for resource, amount in required_resources.items():
                current = inventory.get(resource, 0)
                resource_progress.append(min(100, int((current / amount) * 100)))
            
            # Overall progress is average of gold and resources
            goal["progress"] = int((gold_progress + sum(resource_progress) / len(resource_progress)) / 2)
            
            # Check if completed
            gold_ready = current_gold >= target_gold
            resources_ready = all(inventory.get(r, 0) >= a for r, a in required_resources.items())
            
            if gold_ready and resources_ready:
                goal["completed"] = True
                trader.set_property("can_retire", True)
                
        elif goal_type == "FIND_ARTIFACT":
            # Check if trader has the artifact
            inventory = trader.get_property("inventory", {})
            artifact_found = any(item.startswith("artifact_") for item in inventory.keys())
            
            if artifact_found:
                goal["progress"] = 100
                goal["completed"] = True
                trader.set_property("can_retire", True)
            else:
                goal["progress"] = 0
    
    # Update trader's life goals
    trader.set_property("life_goals", goals)
    return trader

def get_life_goal_reward(trader: Trader, state: Any = None) -> float:
    """
    Calculate MCTS reward contribution from life goals.
    This function should be called from the trader state's get_reward method.
    
    Args:
        trader: The trader entity
        state: Optional trader state for additional context
        
    Returns:
        float: Reward value based on life goal progress
    """
    goals = trader.get_property("life_goals", [])
    if not goals:
        return 0.0
    
    # Calculate weighted average of goal progress
    total_weight = 0
    weighted_progress = 0
    
    for goal in goals:
        # Retirement goals are weighted more heavily
        weight = 2.0 if goal.get("is_retirement_goal", False) else 1.0
        progress = goal.get("progress", 0)
        
        weighted_progress += progress * weight
        total_weight += weight
    
    # Convert to 0-1 scale for reward function
    avg_progress = weighted_progress / (total_weight * 100) if total_weight > 0 else 0
    
    # Scale for MCTS reward (typically 0-10 range)
    return avg_progress * 5.0  # Maximum contribution of 5.0 to reward

async def apply_life_goals_to_all_traders(trader_ids: List[str] = None):
    """
    Apply life goals to all traders or a specified list of traders.
    
    Args:
        trader_ids: Optional list of trader IDs to update
    """
    db = SessionLocal()
    try:
        trader_manager = TraderManager(db)
        
        # Get all trader IDs if not specified
        if not trader_ids:
            traders_db = db.query(Traders).all()
            trader_ids = [str(t.trader_id) for t in traders_db]
        
        logger.info(f"Applying life goals to {len(trader_ids)} traders")
        
        for trader_id in trader_ids:
            try:
                # Load trader
                trader = await trader_manager.load_trader(trader_id)
                if not trader:
                    logger.warning(f"Trader {trader_id} not found")
                    continue
                
                # Add life goals
                trader = await add_life_goals_to_trader(trader)
                
                # Save updated trader
                await trader_manager.save_trader(trader)
                
                logger.info(f"Added life goals to trader {trader_id}")
            except Exception as e:
                logger.exception(f"Error adding life goals to trader {trader_id}: {e}")
    
    finally:
        db.close()

def integrate_life_goals_with_mcts(trader_state, action):
    """
    Example of how to integrate life goals with MCTS decision making.
    This demonstrates how life goals affect action selection.
    
    Args:
        trader_state: The trader state for MCTS
        action: A potential action to evaluate
        
    Returns:
        float: Adjustment to action score based on life goals
    """
    trader = trader_state.trader
    goals = trader.get_property("life_goals", [])
    
    if not goals:
        return 0.0
    
    adjustment = 0.0
    
    for goal in goals:
        goal_type = goal["type"]
        
        # Different goal types influence different actions
        if goal_type == "WEALTH" and action["type"] in ["sell", "trade"]:
            # Wealth goals favor selling at better prices
            if "price" in action:
                adjustment += 0.5 * (action["price"] / 100.0)  # Scale by price
        
        elif goal_type == "VISIT_SETTLEMENTS" and action["type"] == "move":
            # Explorer goals favor visiting new settlements
            if ("location_id" in action and 
                action["location_id"] not in trader.get_property("visited_settlements", [])):
                adjustment += 1.0
        
        elif goal_type == "COLLECT_ITEMS" and action["type"] == "buy":
            # Collector goals favor buying specific items
            if ("item" in action and 
                any(t in action["item"] for t in goal["params"].get("item_types", []))):
                adjustment += 1.5
        
        elif goal_type == "OPEN_SHOP" and action["type"] == "move":
            # Shop goals favor visiting potential shop locations
            preferred_types = goal["params"].get("preferred_settlement_types", [])
            if ("location_id" in action and 
                trader_state.world_info.get("locations", {}).get(action["location_id"], {}).get("settlement_type") in preferred_types):
                adjustment += 0.8
        
        # Retirement goals generally favor actions that accumulate resources
        if goal.get("is_retirement_goal", False):
            if action["type"] == "sell":
                adjustment += 0.3
            elif action["type"] == "buy" and "luxury" in action.get("item", ""):
                adjustment -= 0.5  # Penalize luxury purchases when saving for retirement
    
    return adjustment

# Add this to the TraderState.get_reward method:
"""
# Include life goal progress in reward calculation
life_goal_reward = get_life_goal_reward(self.trader)
reward += life_goal_reward
"""

# Example of how to modify action scoring in TraderState._score_location:
"""
def _score_location(self, location_id):
    score = 1.0  # Base score
    
    # ... existing scoring logic ...
    
    # Add life goal considerations
    for goal in self.trader.get_property("life_goals", []):
        if goal["type"] == "SPECIFIC_SETTLEMENT" and goal["params"].get("target_settlement_id") == location_id:
            score += 3.0  # Strong bonus for target settlement
        elif goal["type"] == "OPEN_SHOP":
            # Check if this is a preferred settlement type
            settlement_type = self.world_info.get("locations", {}).get(location_id, {}).get("settlement_type")
            if settlement_type in goal["params"].get("preferred_settlement_types", []):
                score += 1.5
    
    return score
"""

async def main():
    """Main function for direct script execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Add life goals to traders")
    parser.add_argument("--trader-id", type=str, help="Specific trader ID to update")
    parser.add_argument("--all", action="store_true", help="Update all traders")
    parser.add_argument("--num-goals", type=int, default=2, help="Number of regular life goals to add")
    parser.add_argument("--check-progress", action="store_true", help="Check progress of existing goals")
    
    args = parser.parse_args()
    
    if args.all:
        await apply_life_goals_to_all_traders()
    elif args.trader_id:
        db = SessionLocal()
        try:
            trader_manager = TraderManager(db)
            trader = await trader_manager.load_trader(args.trader_id)
            
            if not trader:
                logger.error(f"Trader {args.trader_id} not found")
                return
            
            if args.check_progress:
                trader = await check_life_goal_progress(trader)
                logger.info(f"Updated goal progress for trader {args.trader_id}")
                
                # Print current goals and progress
                goals = trader.get_property("life_goals", [])
                if goals:
                    logger.info(f"Current life goals for trader {trader.get_property('name')}:")
                    for goal in goals:
                        logger.info(f"  - {goal['name']}: {goal['progress']}% complete")
                        if goal.get("is_retirement_goal", False):
                            logger.info(f"    (Retirement goal)")
            else:
                trader = await add_life_goals_to_trader(trader, args.num_goals)
                logger.info(f"Added {args.num_goals} regular life goals and 1 retirement goal to trader {args.trader_id}")
            
            await trader_manager.save_trader(trader)
            
        finally:
            db.close()
    else:
        logger.error("Please specify --all or --trader-id")

if __name__ == "__main__":
    asyncio.run(main())