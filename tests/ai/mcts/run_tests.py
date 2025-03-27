#!/usr/bin/env python
"""Test runner for MCTS tests.

This script runs the test suite for the MCTS implementation and related state classes.
It can be run with various options to control which tests are run and how.
"""

import unittest
import argparse
import time
import sys
import os

def run_tests(test_pattern, verbosity=2, benchmark=False):
    """Run the test suite.
    
    Args:
        test_pattern: Pattern to match test files or path to specific test file
        verbosity: Level of test output detail
        benchmark: Whether to include benchmark tests
        
    Returns:
        True if all tests passed, False otherwise
    """
    # Set environment variable for benchmarking
    if benchmark:
        os.environ["MCTS_BENCHMARK"] = "1"
    else:
        os.environ.pop("MCTS_BENCHMARK", None)
    
    # Find and run tests
    start_time = time.time()
    
    # Print test info
    print(f"Running tests with pattern: {test_pattern}")
    
    # Run the tests
    command = f"python -m unittest {test_pattern}"
    exit_code = os.system(command)
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"\nTests completed in {duration:.2f} seconds")
    
    return exit_code == 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run MCTS tests")
    parser.add_argument("--benchmark", action="store_true", help="Run benchmark tests")
    parser.add_argument("--verbosity", "-v", type=int, default=2, help="Verbosity level")
    
    # Test selection options
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--all", action="store_true", help="Run all tests")
    group.add_argument("--core", action="store_true", help="Run only core tests")
    group.add_argument("--states", action="store_true", help="Run only state tests")
    group.add_argument("--integration", action="store_true", help="Run only integration tests")
    group.add_argument("--trader", action="store_true", help="Run only trader state tests")
    group.add_argument("--player", action="store_true", help="Run only player state tests")
    group.add_argument("--equipment", action="store_true", help="Run only equipment state tests")
    
    args = parser.parse_args()
    
    # Determine test pattern based on arguments
    if args.all or not any([args.core, args.states, args.integration, 
                            args.trader, args.player, args.equipment]):
        test_pattern = "discover -s tests/ai/mcts"
    elif args.core:
        test_pattern = "tests.ai.mcts.test_core"
    elif args.states:
        test_pattern = "discover -s tests/ai/mcts/states"
    elif args.integration:
        test_pattern = "tests.ai.mcts.test_integration"
    elif args.trader:
        test_pattern = "tests.ai.mcts.states.test_trader_state"
    elif args.player:
        test_pattern = "tests.ai.mcts.states.test_player_state"
    elif args.equipment:
        test_pattern = "tests.ai.mcts.states.test_equipment_state"
    
    # Run the tests
    success = run_tests(test_pattern, args.verbosity, args.benchmark)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)