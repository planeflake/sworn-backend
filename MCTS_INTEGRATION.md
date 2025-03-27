# MCTS Integration Guide

This document explains how the Monte Carlo Tree Search (MCTS) algorithm is integrated with the backend services for intelligent decision-making.

## Components

### 1. Core MCTS Algorithm (`app/ai/mcts/core.py`)
- Generic implementation of the MCTS algorithm
- `MCTS` class that manages the search process
- `MCTSNode` class that represents nodes in the search tree
- Functions for selection, expansion, simulation, and backpropagation

### 2. Trader Entity (`app/game_state/entities/trader.py`)
- Representation of trader data using property dictionary pattern
- Methods for manipulating trader state (inventory, location, etc.)
- Serialization methods for converting between entity and dictionary

### 3. Trader State (`app/game_state/states/trader_state.py`)
- MCTS state representation for traders
- Implements action generation, state transitions, reward calculation
- Provides methods like `get_possible_actions()`, `apply_action()`, `get_reward()`
- Essential for the MCTS algorithm to simulate different decision paths

### 4. Trader Service (`app/game_state/services/trader_service.py`)
- Orchestrates trader operations and connects to MCTS
- Extracts data from database models to create MCTS states
- Uses MCTS algorithm to make movement decisions
- Applies decisions back to the trader entity and database

### 5. Trader Worker (`app/workers/trader_worker_new.py`)
- Celery task implementation that uses TraderService
- Provides Celery-compatible interface for background processing
- Manages database sessions and async execution

## Integration Flow

1. **Task Triggered**: Celery scheduler or manual call triggers the `process_trader_movement` task
2. **Service Initialization**: `TraderService` is created with a database session
3. **Entity Loading**: Trader entity is loaded from the database via TraderManager
4. **World Data Preparation**: Settlement, area, and world data is queried from the database
5. **MCTS State Creation**: A `TraderState` object is created with trader entity and world data
6. **MCTS Search**: The MCTS algorithm searches through possible actions and states
7. **Decision Application**: The best action is applied to the trader entity and database
8. **Results Processing**: Results are returned to the caller and logged

## Trader Decision Process

1. Trader service extracts data needed for decision-making:
   - Trader's current location, inventory, and preferences
   - Available destinations and connections
   - Market data for buy/sell opportunities
   - World state (time, season, etc.)

2. This data is used to create a `TraderState` object that can:
   - Generate possible actions (move, buy, sell, etc.)
   - Apply actions to produce new states
   - Evaluate state quality through a reward function
   - Determine when a simulation should end (terminal state)

3. MCTS algorithm simulates many possible futures by:
   - Selecting promising actions based on exploration/exploitation balance
   - Expanding the search tree by trying new actions
   - Simulating random play to estimate outcome value
   - Propagating results back up the tree

4. The action with the best estimated value is chosen

5. This decision is applied to the actual trader entity and database

## Example Test

A test script is provided in `utils/test_mcts_trader.py` that demonstrates:
- Creating test trader data
- Setting up a simulated world with settlements and connections
- Running the MCTS search to find the best action
- Explaining the reasoning behind decisions
- Testing with real database data (optional)

## Usage in Celery Worker

The trader worker in `app/workers/trader_worker_new.py` is registered with Celery and scheduled to run every 30 seconds in the beat schedule defined in `app/workers/celery_app.py`.

To manually trigger trader movement:
```python
from workers.trader_worker_new import process_trader_movement
result = process_trader_movement.delay('trader_id_here')
```

## Additional Features

1. **Path Finding**: Trader service includes a breadth-first search algorithm to find paths between settlements through area networks.

2. **Encounter Generation**: Traders can encounter random events when traveling through areas, with risks and rewards.

3. **Intelligent Decision Explanation**: The system can provide insights into why a particular decision was made, based on market opportunities, location preferences, and other factors.

## Future Improvements

1. **Neural Network Guidance**: Add neural network guidance to the MCTS algorithm for better initial action evaluation.

2. **More Decision Types**: Expand beyond movement to other decisions like:
   - Setting up shops
   - Hiring guards
   - Forming caravans
   - Specializing in goods

3. **Learning from History**: Incorporate past trade history to improve decision quality over time.

4. **Performance Optimization**: Optimize the MCTS implementation for larger action spaces and deeper searches.