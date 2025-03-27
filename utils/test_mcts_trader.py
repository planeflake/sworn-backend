#!/usr/bin/env python
# utils/test_mcts_trader.py
"""
Test script for the MCTS trader decision making.
This script demonstrates how the MCTS algorithm works with trader state
and can be used to debug and improve the decision making process.
"""

import sys
import os
import asyncio
import logging
import json
import random
import uuid
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
from app.ai.mcts.states.trader_state import TraderState
from app.ai.mcts.core import MCTS
from app.game_state.services.trader_service import TraderService
from models.core import Traders, Settlements, Worlds, Areas

async def create_test_trader():
    """Create a test trader with sample data"""
    trader_id = str(uuid.uuid4())
    trader = Trader(trader_id)
    
    # Set basic information
    trader.set_basic_info("Test Trader", "A trader created for testing MCTS")
    
    # Set resources
    trader.set_property("gold", 100)
    trader.add_resource("cloth", 5)
    trader.add_resource("spices", 3)
    trader.add_resource("tools", 2)
    
    # Set location preferences
    trader.set_property("preferred_biomes", ["forest", "plains"])
    
    return trader

async def create_test_world_data():
    """Create sample world data for testing"""
    # Create a simple world with settlements and connections
    settlement_ids = [str(uuid.uuid4()) for _ in range(5)]
    
    # Create settlements
    settlements = {
        settlement_ids[0]: {
            "id": settlement_ids[0],
            "name": "Riverdale",
            "biome": "forest",
            "population": 500,
            "settlement_type": "town"
        },
        settlement_ids[1]: {
            "id": settlement_ids[1],
            "name": "Oakvale",
            "biome": "forest",
            "population": 300,
            "settlement_type": "village"
        },
        settlement_ids[2]: {
            "id": settlement_ids[2],
            "name": "Dryfields",
            "biome": "plains",
            "population": 400,
            "settlement_type": "town"
        },
        settlement_ids[3]: {
            "id": settlement_ids[3],
            "name": "Stonebridge",
            "biome": "mountains",
            "population": 700,
            "settlement_type": "city"
        },
        settlement_ids[4]: {
            "id": settlement_ids[4],
            "name": "Sandport",
            "biome": "coast",
            "population": 800,
            "settlement_type": "city"
        }
    }
    
    # Create location graph (connections between settlements)
    location_graph = {
        settlement_ids[0]: [settlement_ids[1], settlement_ids[2]],  # Riverdale -> Oakvale, Dryfields
        settlement_ids[1]: [settlement_ids[0], settlement_ids[3]],  # Oakvale -> Riverdale, Stonebridge
        settlement_ids[2]: [settlement_ids[0], settlement_ids[4]],  # Dryfields -> Riverdale, Sandport
        settlement_ids[3]: [settlement_ids[1], settlement_ids[4]],  # Stonebridge -> Oakvale, Sandport
        settlement_ids[4]: [settlement_ids[2], settlement_ids[3]]   # Sandport -> Dryfields, Stonebridge
    }
    
    # Create market data (what settlements buy/sell)
    market_data = {}
    for sid in settlement_ids:
        market_data[sid] = {
            "buying": {},  # What the settlement buys (trader sells)
            "selling": {}  # What the settlement sells (trader buys)
        }
    
    # Riverdale buys cloth at good price, sells tools
    market_data[settlement_ids[0]]["buying"]["cloth"] = 12
    market_data[settlement_ids[0]]["selling"]["tools"] = 8
    
    # Oakvale buys tools at good price, sells cloth
    market_data[settlement_ids[1]]["buying"]["tools"] = 15
    market_data[settlement_ids[1]]["selling"]["cloth"] = 5
    
    # Dryfields buys spices at good price, sells food
    market_data[settlement_ids[2]]["buying"]["spices"] = 20
    market_data[settlement_ids[2]]["selling"]["food"] = 4
    
    # Stonebridge buys food at medium price, sells luxury goods
    market_data[settlement_ids[3]]["buying"]["food"] = 8
    market_data[settlement_ids[3]]["selling"]["luxury_goods"] = 25
    
    # Sandport buys luxury goods at high price, sells spices
    market_data[settlement_ids[4]]["buying"]["luxury_goods"] = 35
    market_data[settlement_ids[4]]["selling"]["spices"] = 10
    
    # Create world data structure
    world_data = {
        "world_id": str(uuid.uuid4()),
        "current_game_day": 42,
        "current_season": "summer",
        "locations": settlements,
        "market_data": market_data
    }
    
    return world_data, location_graph, settlement_ids

async def run_mcts_simulation(trader, world_data, location_graph, current_location_id):
    """Run a single MCTS simulation and return the best action"""
    # Set trader's current location
    trader.set_location(current_location_id, "current")
    
    # Create trader state for MCTS
    trader_state = TraderState(
        trader=trader,
        world_info=world_data,
        location_graph=location_graph
    )
    
    # Run MCTS search
    mcts = MCTS(exploration_weight=1.0)
    num_simulations = 200  # More simulations for better decisions
    
    best_action = mcts.search(
        root_state=trader_state,
        get_legal_actions_fn=lambda s: s.get_possible_actions(),
        apply_action_fn=lambda s, a: s.apply_action(a),
        is_terminal_fn=lambda s: s.is_terminal(),
        get_reward_fn=lambda s: s.get_reward(),
        num_simulations=num_simulations
    )
    
    return best_action, mcts.decision_stats

async def test_with_real_database():
    """Test the trader service with data from the actual database"""
    logger.info("Testing with real database data")
    
    db = SessionLocal()
    try:
        # Get an existing trader
        trader_db = db.query(Traders).first()
        if not trader_db:
            logger.error("No traders found in database")
            return
        
        logger.info(f"Using trader: {trader_db.trader_id}")
        
        # Create trader service
        trader_service = TraderService(db)
        
        # Process trader movement
        result = await trader_service.process_trader_movement(str(trader_db.trader_id))
        
        logger.info(f"TraderService decision result: {result}")
        
    except Exception as e:
        logger.exception(f"Error in database test: {e}")
    finally:
        db.close()

async def main():
    """Main test function"""
    logger.info("Starting MCTS trader test")
    
    # Create test trader
    trader = await create_test_trader()
    logger.info(f"Created test trader: {trader}")
    
    # Create test world data
    world_data, location_graph, settlement_ids = await create_test_world_data()
    logger.info(f"Created test world with {len(settlement_ids)} settlements")
    
    # Start at the first settlement
    current_location_id = settlement_ids[0]
    logger.info(f"Starting at settlement: {world_data['locations'][current_location_id]['name']}")
    
    # Run MCTS simulation
    best_action, stats = await run_mcts_simulation(trader, world_data, location_graph, current_location_id)
    
    # Display results
    logger.info(f"MCTS decision stats: {stats}")
    
    if best_action and best_action.get("type") == "move":
        destination_id = best_action["location_id"]
        destination_name = world_data["locations"][destination_id]["name"]
        logger.info(f"Best action: Move to {destination_name}")
        
        # Explain the decision
        biome = world_data["locations"][destination_id]["biome"]
        is_preferred_biome = biome in trader.get_property("preferred_biomes", [])
        
        reasons = []
        if is_preferred_biome:
            reasons.append(f"It has a preferred biome ({biome})")
        
        # Check market opportunities
        market = world_data["market_data"][destination_id]
        for item, price in market["buying"].items():
            if item in trader.get_property("inventory", {}):
                reasons.append(f"Can sell {item} for {price} gold")
        
        logger.info(f"Reasons for this decision: {', '.join(reasons) if reasons else 'Unknown'}")
    
    else:
        logger.info(f"Best action: {best_action}")
    
    # Test with real database if available
    try:
        await test_with_real_database()
    except Exception as e:
        logger.warning(f"Database test skipped: {e}")
    
    logger.info("MCTS trader test completed")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test MCTS for trader decision making")
    parser.add_argument("--simulations", type=int, default=200, help="Number of MCTS simulations to run")
    parser.add_argument("--db-test", action="store_true", help="Run test with actual database")
    parser.add_argument("--log-level", type=str, default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"], 
                        help="Logging level")
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Run the async main function
    asyncio.run(main())