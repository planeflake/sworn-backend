#!/usr/bin/env python3
"""
Test script to run MCTS simulations for all traders and display the results.
This is useful for benchmarking and validating the MCTS implementation.

Usage:
    python run_trader_simulations.py [--simulations NUM] [--traders TRADER1,TRADER2] [--verbose]
"""

import os
import sys
import json
import time
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Add the project root to the Python path so we can import from workers
project_root = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

from workers.mcts_trader.tasks import update_trader_location_mcts
from workers.celery_app import get_traders


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Run MCTS simulations for traders')
    parser.add_argument('--simulations', type=int, default=50,
                        help='Number of MCTS simulations to run per trader (default: 50)')
    parser.add_argument('--traders', type=str, default=None,
                        help='Comma-separated list of trader names to test (default: all traders)')
    parser.add_argument('--verbose', action='store_true',
                        help='Show verbose output including full decision details')
    return parser.parse_args()


def setup_logging():
    """Set up logging configuration."""
    # Configure root logger for console output
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # Return the path to the log file
    log_file = os.path.join(project_root, 'logs', 'mcts_trader_decisions.log')
    return log_file


def get_trader_names(traders_arg):
    """Get list of traders to test, either from argument or all available."""
    if traders_arg:
        # Use specified traders
        return [name.strip() for name in traders_arg.split(',')]
    else:
        # Use all available traders
        return [trader['name'] for trader in get_traders()]


def run_simulations(trader_names, num_simulations, verbose):
    """Run MCTS simulations for the specified traders and display results."""
    results = []
    total_start_time = time.time()
    
    print(f"\nRunning {num_simulations} MCTS simulations for {len(trader_names)} traders...\n")
    
    # Create a table header
    print(f"{'Trader':<15} {'Start Location':<15} {'Destination':<15} {'Gold Δ':<10} {'Cart Δ':<10} {'Time (s)':<10}")
    print('-' * 80)
    
    for trader_name in trader_names:
        start_time = time.time()
        
        # Get trader's initial state
        initial_trader = next((t for t in get_traders() if t['name'] == trader_name), None)
        if not initial_trader:
            print(f"Trader {trader_name} not found, skipping")
            continue
            
        initial_location = initial_trader.get('current_location', initial_trader.get('settlement', initial_trader['home_settlement']))
        initial_gold = initial_trader['status']['gold']
        initial_cart_health = initial_trader['logistics']['cart_health']
        
        # Run MCTS simulations
        result = update_trader_location_mcts(trader_name, num_simulations)
        
        # Calculate time taken
        elapsed_time = time.time() - start_time
        
        # Handle error case
        if 'error' in result:
            print(f"{trader_name:<15} {'ERROR':<15} {result['error']:<15}")
            continue
            
        # Handle case where trader stays put
        if 'stayed_at' in result:
            print(f"{trader_name:<15} {initial_location:<15} {'(stayed put)':<15} {'0':<10} {'0':<10} {elapsed_time:.2f}")
            continue
            
        # Calculate changes
        gold_change = result['current_gold'] - initial_gold
        cart_change = result['cart_health'] - initial_cart_health
        
        # Print result row
        print(f"{trader_name:<15} {initial_location:<15} {result['moved_to']:<15} {gold_change:<+10} {cart_change:<+10} {elapsed_time:.2f}")
        
        # Store detailed result for later
        results.append({
            'trader': trader_name,
            'initial_location': initial_location,
            'destination': result.get('moved_to', result.get('stayed_at', 'unknown')),
            'gold_change': gold_change if 'moved_to' in result else 0,
            'cart_change': cart_change if 'moved_to' in result else 0,
            'time_taken': elapsed_time
        })
    
    total_time = time.time() - total_start_time
    print('-' * 80)
    print(f"Total time: {total_time:.2f} seconds for {len(trader_names)} traders")
    
    # Show the log file content
    print("\nRecent log entries:")
    print('=' * 80)
    log_file = os.path.join(project_root, 'logs', 'mcts_trader_decisions.log')
    show_log_tail(log_file, trader_names, verbose)
    
    return results


def show_log_tail(log_file, trader_names, verbose=False):
    """Show the tail of the log file, filtered by trader names."""
    if not os.path.exists(log_file):
        print(f"Log file not found: {log_file}")
        return
    
    # Read the entire log file
    with open(log_file, 'r') as f:
        log_lines = f.readlines()
    
    # Show last 100 lines by default, or more if verbose
    line_count = 500 if verbose else 100
    log_tail = log_lines[-line_count:]
    
    # Look for decision sections for the traders we simulated
    current_trader = None
    in_decision_section = False
    decision_lines = []
    
    for line in log_tail:
        # Check for decision start
        if "Starting MCTS decision for trader" in line:
            trader_found = False
            for trader in trader_names:
                if f"Starting MCTS decision for trader {trader}" in line:
                    current_trader = trader
                    trader_found = True
                    in_decision_section = True
                    decision_lines.append(line)
                    break
            if not trader_found:
                in_decision_section = False
        elif in_decision_section:
            # Only include detailed JSON blocks if verbose mode is enabled
            if "MCTS decision details:" in line and not verbose:
                continue
            decision_lines.append(line)
    
    # Print filtered log lines
    for line in decision_lines:
        print(line.rstrip())


def main():
    """Main entry point."""
    args = parse_args()
    log_file = setup_logging()
    
    # Get list of traders to test
    trader_names = get_trader_names(args.traders)
    
    if not trader_names:
        print("No traders found to test")
        return
    
    # Print header
    print("\n" + "=" * 80)
    print(f"MCTS Trader Simulation Test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Simulations per trader: {args.simulations}")
    print(f"Traders: {', '.join(trader_names)}")
    print("=" * 80)
    
    # Run simulations
    results = run_simulations(trader_names, args.simulations, args.verbose)
    
    # Print summary
    print("\nSimulation completed.")
    print(f"Detailed logs are available in: {log_file}")
    print(f"View formatted logs with: python3 view_trader_decisions.py --trader TRADER_NAME --detailed")


if __name__ == "__main__":
    main()