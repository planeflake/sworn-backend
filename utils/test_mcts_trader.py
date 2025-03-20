#!/usr/bin/env python
# utils/test_mcts_trader.py

import sys
import os
import logging
import json
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add root directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import get_db
from app.game_state.manager import GameStateManager
from models.core import Traders, Settlements

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('mcts_trader_test.log')
    ]
)
logger = logging.getLogger("mcts_trader_test")

def test_mcts_trader(trader_id=None, simulations=100, log_level="INFO"):
    """
    Test the MCTS implementation for trader decision making.
    
    Args:
        trader_id: The ID of a specific trader to test. If None, will test for all traders in a settlement.
        simulations: Number of MCTS simulations to run.
        log_level: Logging level (INFO, DEBUG, etc.)
    """
    # Set log level
    logger.setLevel(getattr(logging, log_level))
    
    # Get a database session
    session = next(get_db())
    
    try:
        manager = GameStateManager(session)
        
        # If trader_id provided, test for that trader
        if trader_id:
            logger.info(f"Testing MCTS decision for trader {trader_id}")
            result = manager.get_mcts_trader_decision(trader_id, simulations)
            
            if result["status"] == "success":
                logger.info(f"MCTS decision successful")
                logger.info(f"Selected destination: {result['next_settlement_name']} ({result['next_settlement_id']})")
                
                # Pretty print the MCTS stats
                stats = result.get("mcts_stats", {})
                logger.info(f"MCTS stats:")
                logger.info(f"  - Simulations: {stats.get('simulations', 0)}")
                logger.info(f"  - Actions evaluated: {stats.get('actions_evaluated', 0)}")
                logger.info(f"  - Exploration weight: {stats.get('exploration_weight', 0)}")
                
                # Log action stats
                action_stats = stats.get("action_stats", {})
                logger.info("Action evaluations:")
                for action, action_data in action_stats.items():
                    avg_value = action_data.get("average_value", 0)
                    visits = action_data.get("visits", 0)
                    logger.info(f"  - {action}: {visits} visits, avg value {avg_value:.2f}")
                
                return result
            else:
                logger.error(f"MCTS decision failed: {result.get('message', 'Unknown error')}")
                return result
        else:
            # No specific trader ID provided, test for a random trader in a settlement
            logger.info("No trader ID provided, finding an active trader...")
            
            # Find a trader who is in a settlement
            trader = session.query(Traders).filter(Traders.current_settlement_id != None).first()
            
            if not trader:
                logger.error("No suitable trader found for testing")
                return {"status": "error", "message": "No suitable trader found"}
            
            logger.info(f"Selected trader: {trader.npc_name} ({trader.trader_id})")
            result = manager.get_mcts_trader_decision(str(trader.trader_id), simulations)
            
            if result["status"] == "success":
                logger.info(f"MCTS decision successful")
                logger.info(f"Selected destination: {result['next_settlement_name']} ({result['next_settlement_id']})")
                
                # Pretty print the MCTS stats
                stats = result.get("mcts_stats", {})
                logger.info(f"MCTS stats:")
                logger.info(f"  - Simulations: {stats.get('simulations', 0)}")
                logger.info(f"  - Actions evaluated: {stats.get('actions_evaluated', 0)}")
                
                return result
            else:
                logger.error(f"MCTS decision failed: {result.get('message', 'Unknown error')}")
                return result
    
    except Exception as e:
        logger.exception(f"Error testing MCTS trader: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        session.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test MCTS for trader decision making")
    parser.add_argument("--trader-id", type=str, help="Specific trader ID to test")
    parser.add_argument("--simulations", type=int, default=100, help="Number of MCTS simulations to run")
    parser.add_argument("--log-level", type=str, default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"], 
                        help="Logging level")
    
    args = parser.parse_args()
    
    result = test_mcts_trader(args.trader_id, args.simulations, args.log_level)
    
    # Print final result as JSON
    print(json.dumps(result, indent=2, default=str))