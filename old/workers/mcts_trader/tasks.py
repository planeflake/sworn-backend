import os
import json
import random
import logging
import datetime
import numpy as np
from workers.celery_app import app
from .trader_state import TraderState, TraderAction
from .mcts import MCTS
from .neural_network import (
    load_model, save_model, 
    create_trader_nn_model, 
    load_experience_buffer, save_experience_buffer,
    train_model_from_buffer
)

# Set up logging
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger('mcts_trader')
logger.setLevel(logging.INFO)

# Create a file handler
log_file = os.path.join(LOG_DIR, 'mcts_trader_decisions.log')
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.INFO)

# Create a console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Create a formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add the handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)


@app.task
def update_trader_location_mcts(trader_name, simulation_count=100):
    """Use MCTS to determine optimal trader movement."""
    # Load trader data
    trader_data = get_trader_data(trader_name)
    if not trader_data:
        logger.error(f"Trader {trader_name} not found")
        return {"error": f"Trader {trader_name} not found"}
    
    logger.info(f"Starting MCTS decision for trader {trader_name}")
    
    # Load settlements data
    settlements_data = get_settlements_data()
    
    # Create initial state
    current_location = trader_data.get("current_location") or trader_data["home_settlement"]
    state = TraderState(trader_data, settlements_data, current_location)
    
    # Load neural network if available
    try:
        nn_model = load_model()
        using_nn = nn_model is not None
        logger.info(f"Neural network model {'found and loaded' if using_nn else 'not found, using random simulations'}")
    except Exception as e:
        logger.error(f"Error loading neural network model: {e}")
        nn_model = None
        using_nn = False
        logger.info("Using random simulations due to error")
    
    # Initialize MCTS
    mcts = MCTS(exploration_weight=1.5)
    
    # Search for best action
    best_action = mcts.search(state, simulation_count, nn_model)
    
    # Log detailed decision information
    decision_log = {
        "timestamp": datetime.datetime.now().isoformat(),
        "trader": trader_name,
        "current_location": current_location,
        "gold": trader_data["status"]["gold"],
        "cart_health": trader_data["logistics"]["cart_health"],
        "wares": {k: v["quantity"] for k, v in trader_data["wares"].items()},
        "mcts_stats": mcts.decision_stats
    }
    
    logger.info(f"MCTS decision details: {json.dumps(decision_log, indent=2)}")
    
    if not best_action:
        logger.info(f"No viable destinations found for {trader_name}, staying at {current_location}")
        return {
            "trader": trader_name,
            "stayed_at": current_location,
            "reason": "No viable destinations found"
        }
    
    # Log the decision reasoning
    if best_action.destination in mcts.decision_stats["action_stats"]:
        stats = mcts.decision_stats["action_stats"][best_action.destination]
        logger.info(f"Chosen action for {trader_name}: Move to {best_action.destination}")
        logger.info(f"  - Visits: {stats['visits']}/{mcts.decision_stats['simulations']} simulations")
        logger.info(f"  - Average value: {stats['average_value']:.2f}")
        
        # Compare to other options
        other_options = []
        for dest, stats in mcts.decision_stats["action_stats"].items():
            if dest != best_action.destination:
                other_options.append(f"{dest} (visits: {stats['visits']}, avg value: {stats['average_value']:.2f})")
        
        if other_options:
            logger.info(f"  - Other options: {', '.join(other_options)}")
    
    # Apply the chosen action
    new_state = state.apply_action(best_action)
    
    # Log the projected outcome
    logger.info(f"Projected outcome after moving to {best_action.destination}:")
    logger.info(f"  - Gold change: {trader_data['status']['gold']} -> {new_state.trader['status']['gold']}")
    logger.info(f"  - Cart health: {trader_data['logistics']['cart_health']} -> {new_state.trader['logistics']['cart_health']}")
    
    # Log trading impact
    old_wares = {k: v["quantity"] for k, v in trader_data["wares"].items()}
    new_wares = {k: v["quantity"] for k, v in new_state.trader["wares"].items()}
    
    # Items sold
    for item, qty in old_wares.items():
        if item in new_wares:
            if new_wares[item] < qty:
                logger.info(f"  - Sold {qty - new_wares[item]} units of {item}")
        else:
            logger.info(f"  - Sold all {qty} units of {item}")
    
    # Items bought
    for item, qty in new_wares.items():
        if item not in old_wares:
            logger.info(f"  - Bought {qty} units of {item}")
        elif new_wares[item] > old_wares[item]:
            logger.info(f"  - Bought {new_wares[item] - old_wares[item]} units of {item}")
    
    # Update trader data in storage
    update_trader_in_storage(trader_name, new_state.trader)
    
    # Record this experience
    experience_buffer = load_experience_buffer()
    experience_buffer.add(state, new_state.get_reward())
    save_experience_buffer(experience_buffer)
    
    return {
        "trader": trader_name,
        "moved_to": best_action.destination,
        "current_gold": new_state.trader["status"]["gold"],
        "cart_health": new_state.trader["logistics"]["cart_health"]
    }


@app.task
def train_trader_nn(batch_size=64, epochs=5):
    """Train the neural network from collected experiences."""
    logger.info(f"Starting neural network training with batch_size={batch_size}, epochs={epochs}")
    
    try:
        from .neural_network import SKLEARN_AVAILABLE
        if not SKLEARN_AVAILABLE:
            logger.warning("scikit-learn is not available - skipping neural network training")
            return {"status": "Skipped - scikit-learn not available"}
            
        # Load experience buffer
        buffer = load_experience_buffer()
        
        if len(buffer) < batch_size:
            logger.info(f"Not enough experiences for training (have {len(buffer)}, need {batch_size})")
            return {"status": "Not enough experiences for training", "buffer_size": len(buffer)}
        
        # Load or create model
        model = load_model()
        if model is None:
            logger.info("No existing model found, creating a new neural network model")
            # Create new model with the right input shape
            sample = buffer.buffer[0][0]
            input_shape = len(sample)
            model = create_trader_nn_model(input_shape)
            
            if model is None:
                logger.warning("Failed to create neural network model")
                return {"status": "Failed to create model"}
        else:
            logger.info("Existing model loaded for additional training")
        
        # Train model
        logger.info(f"Training model on {len(buffer)} experiences")
        
        try:
            # For sklearn, we'll calculate MSE manually for evaluation
            test_sample = buffer.sample(min(len(buffer), 100))
            X_test = np.array([exp[0] for exp in test_sample])
            y_test = np.array([exp[1] for exp in test_sample])
            
            # First make sure the scaler is fitted before trying to transform
            if not model['is_fitted']:
                logger.info("Fitting scaler with test data before evaluation")
                model['scaler'].fit(X_test)
                model['is_fitted'] = True
                # No before_loss calculation possible on first training
                before_loss = float('inf')
            else:
                # Transform features
                X_test_scaled = model['scaler'].transform(X_test)
                
                # Calculate MSE before training
                y_pred_before = model['model'].predict(X_test_scaled)
                before_loss = np.mean((y_pred_before - y_test) ** 2)
            
            # Train the model
            model = train_model_from_buffer(model, buffer, batch_size)
            
            if model is None:
                logger.warning("Training failed - model is None")
                return {"status": "Training failed"}
                
            # Re-run evaluation with the same test data
            X_test_scaled = model['scaler'].transform(X_test)
            y_pred_after = model['model'].predict(X_test_scaled)
            after_loss = np.mean((y_pred_after - y_test) ** 2)
            
            # Save model
            save_model(model)
            
            logger.info(f"Training completed: Loss before={before_loss:.4f}, Loss after={after_loss:.4f}")
            return {
                "status": "Training completed", 
                "buffer_size": len(buffer),
                "loss_before": float(before_loss),
                "loss_after": float(after_loss)
            }
        except Exception as e:
            logger.error(f"Error during model training: {e}")
            return {"status": f"Training error: {str(e)}"}
            
    except Exception as e:
        logger.error(f"Error in train_trader_nn: {e}")
        return {"status": f"Error: {str(e)}"}


@app.task
def update_all_traders_mcts():
    """Update all trader positions using MCTS."""
    logger.info("Starting MCTS update for all traders")
    
    # Get list of all traders
    traders = get_all_traders()
    logger.info(f"Found {len(traders)} traders to update: {', '.join(traders)}")
    
    results = []
    for i, trader_name in enumerate(traders):
        # Stagger task execution to avoid overloading
        countdown = 5 * i  # Stagger by 5 seconds per trader
        logger.info(f"Scheduling update for {trader_name} with {countdown}s delay")
        
        result = update_trader_location_mcts.apply_async(
            args=[trader_name],
            countdown=countdown
        )
        results.append(f"Scheduled MCTS update for {trader_name}")
    
    return {"status": "MCTS trader updates dispatched", "traders": len(traders)}


# ============ HELPER FUNCTIONS ============

def get_trader_data(trader_name):
    """Get trader data from storage."""
    from workers.celery_app import get_traders
    
    traders = get_traders()
    for trader in traders:
        if trader["name"] == trader_name:
            # Convert settlement to current_location if needed for compatibility
            if "current_location" not in trader and "settlement" in trader:
                trader["current_location"] = trader["settlement"]
            return trader
    
    return None


def get_all_traders():
    """Get list of all trader names."""
    from workers.celery_app import get_traders
    traders = get_traders()
    return [trader["name"] for trader in traders]


def update_trader_in_storage(trader_name, updated_trader):
    """Update trader data in the config."""
    # This implementation assumes the trader will be updated in memory by reference
    # In a real implementation, we would need to update the trader in the database or config file
    from workers.celery_app import get_traders
    
    traders = get_traders()
    for i, trader in enumerate(traders):
        if trader["name"] == trader_name:
            # Update trader with new data while preserving the reference
            traders[i].update(updated_trader)
            break


def get_settlements_data():
    """Load all settlement data."""
    from workers.celery_app import get_settlements_config
    return get_settlements_config()