#!/usr/bin/env python3
"""
Script to manually trigger training of the neural network model for MCTS trader decisions.
This helps bootstrap the learning process by collecting experiences and training on them.

Usage:
    python train_neural_network.py [--simulations NUM] [--iterations NUM] [--batch-size NUM]
"""

import os
import sys
import time
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Add the project root to the Python path so we can import from workers
project_root = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

from workers.mcts_trader.tasks import update_trader_location_mcts, train_trader_nn
from workers.celery_app import get_traders
from workers.mcts_trader.neural_network import load_model, load_experience_buffer, SKLEARN_AVAILABLE


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Train neural network model for MCTS trader decisions')
    parser.add_argument('--simulations', type=int, default=50,
                        help='Number of MCTS simulations to run per trader per iteration (default: 50)')
    parser.add_argument('--iterations', type=int, default=5,
                        help='Number of training iterations to run (default: 5)')
    parser.add_argument('--batch-size', type=int, default=64,
                        help='Batch size for training (default: 64)')
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


def collect_experiences(simulations=50):
    """Run MCTS simulations for all traders to collect experiences."""
    trader_names = [trader['name'] for trader in get_traders()]
    
    print(f"\nCollecting experiences from {len(trader_names)} traders with {simulations} simulations each...\n")
    
    for trader_name in trader_names:
        print(f"Running simulations for {trader_name}...")
        update_trader_location_mcts(trader_name, simulations)
    
    # Load the experience buffer to verify data was collected
    buffer = load_experience_buffer()
    print(f"\nCollected {len(buffer)} total experiences in buffer")
    return len(buffer)


def train_network(batch_size=64):
    """Train the neural network using collected experiences."""
    print("\nTraining neural network model...")
    
    start_time = time.time()
    result = train_trader_nn(batch_size=batch_size, epochs=10)
    elapsed_time = time.time() - start_time
    
    if "status" in result and result["status"] == "Training completed":
        print(f"Training successful in {elapsed_time:.2f} seconds!")
        print(f"Buffer size: {result.get('buffer_size', 'unknown')}")
        print(f"Loss before: {result.get('loss_before', 'unknown'):.4f}")
        print(f"Loss after: {result.get('loss_after', 'unknown'):.4f}")
        print(f"Improvement: {result.get('loss_before', 0) - result.get('loss_after', 0):.4f}")
        return True
    else:
        print(f"Training result: {result}")
        return False


def verify_model():
    """Verify that the model exists and can be loaded."""
    print("\nVerifying model...")
    
    model = load_model()
    if model is None:
        print("❌ No model found or model could not be loaded")
        return False
    
    print("✅ Model loaded successfully")
    
    # If using scikit-learn, check more details
    if SKLEARN_AVAILABLE:
        try:
            print(f"Model type: scikit-learn MLPRegressor")
            
            if hasattr(model['model'], 'n_layers_'):
                print(f"Neural network architecture: {model['model'].n_layers_} layers")
                print(f"Hidden layer sizes: {model['model'].hidden_layer_sizes}")
            
            print(f"Scaler: {type(model['scaler']).__name__}")
            print(f"Is fitted: {model['is_fitted']}")
            
            print("\nModel is ready for use in MCTS simulations")
            return True
        except Exception as e:
            print(f"Error examining model: {e}")
            return False
    else:
        print("scikit-learn not available, cannot examine model details")
        return True


def main():
    """Main entry point."""
    args = parse_args()
    setup_logging()
    
    if not SKLEARN_AVAILABLE:
        print("Error: scikit-learn is not available. Cannot train neural network.")
        return
    
    # Print header
    print("\n" + "=" * 80)
    print(f"MCTS Trader Neural Network Training - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Simulations per trader: {args.simulations}")
    print(f"Training iterations: {args.iterations}")
    print(f"Batch size: {args.batch_size}")
    print("=" * 80)
    
    buffer_size = 0
    
    # Run training iterations
    for iteration in range(1, args.iterations + 1):
        print(f"\n\nITERATION {iteration}/{args.iterations}")
        print("-" * 40)
        
        # Collect experiences
        buffer_size = collect_experiences(args.simulations)
        
        if buffer_size < args.batch_size:
            print(f"Warning: Not enough experiences (have {buffer_size}, need {args.batch_size})")
            print("Collecting more experiences...")
            buffer_size = collect_experiences(args.simulations * 2)
            
            if buffer_size < args.batch_size:
                print(f"Still not enough experiences. Try running with more simulations.")
                continue
        
        # Train network
        training_success = train_network(args.batch_size)
        
        if not training_success:
            print("Training failed. Continuing to next iteration.")
            continue
    
    # Verify final model
    verify_model()
    
    print("\nTraining completed.")
    print("\nYou can now run traders with the neural network model using:")
    print(f"python test/trader/run_trader_simulations.py --simulations 50")


if __name__ == "__main__":
    main()