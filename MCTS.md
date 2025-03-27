# Monte Carlo Tree Search (MCTS) Implementation Guide

This guide provides a detailed walkthrough for implementing and using Monte Carlo Tree Search (MCTS) in the Sworn backend system. MCTS is a powerful decision-making algorithm that uses random simulations to evaluate possible actions.

## Contents

1. [Understanding MCTS](#understanding-mcts)
2. [Core Components](#core-components)
3. [Creating State Representations](#creating-state-representations)
4. [Implementing Action Generation](#implementing-action-generation)
5. [State Transitions](#state-transitions)
6. [Reward Functions](#reward-functions)
7. [Running MCTS](#running-mcts)
8. [Integration with Game Services](#integration-with-game-services)
9. [Debugging MCTS](#debugging-mcts)
10. [Optimization Techniques](#optimization-techniques)

## Understanding MCTS

Monte Carlo Tree Search works by:

1. **Selection**: Selecting promising nodes in the search tree
2. **Expansion**: Growing the tree by adding child nodes
3. **Simulation**: Running random simulations from the new node
4. **Backpropagation**: Updating node statistics based on simulation results

The power of MCTS comes from balancing exploration (trying new moves) with exploitation (focusing on good moves), making it ideal for complex decision spaces like those in our game.

## Core Components

The MCTS system has three main components:

1. **MCTSNode**: Represents a node in the search tree
2. **MCTS**: The main algorithm implementation
3. **State**: The representation of game state (specific to each entity type)

Here's how they work together:

```python
# Using MCTS
mcts = MCTS(exploration_weight=1.0)
best_action = mcts.search(
    root_state=state,
    get_legal_actions_fn=lambda s: s.get_legal_actions(),
    apply_action_fn=lambda s, a: s.apply_action(a),
    is_terminal_fn=lambda s: s.is_terminal(),
    get_reward_fn=lambda s: s.get_reward(),
    num_simulations=100
)
```

## Creating State Representations

To use MCTS, you must create state representations for your entities. Here's how to implement a state class:

```python
class MyEntityState:
    def __init__(self, entity_data, world_data=None):
        # Store entity properties
        self.entity_data = entity_data
        self.world_data = world_data or {}
        self._cached_actions = None
        
    def get_legal_actions(self):
        """Return list of legal actions"""
        if self._cached_actions is not None:
            return self._cached_actions
            
        actions = []
        # Generate action objects based on entity type
        # For example:
        if self.entity_data.get("can_move"):
            actions.extend(self._generate_movement_actions())
        
        self._cached_actions = actions
        return actions
        
    def apply_action(self, action):
        """Apply action and return new state"""
        # Create new state object
        new_state = MyEntityState(
            copy.deepcopy(self.entity_data),
            copy.deepcopy(self.world_data)
        )
        
        # Modify new state based on action
        if action.action_type == "move":
            new_state.entity_data["location"] = action.destination
        
        # Clear cached actions
        new_state._cached_actions = None
        return new_state
        
    def is_terminal(self):
        """Check if this is a terminal state"""
        # Define conditions for ending simulation
        # Example: entity reached destination, no more resources, etc.
        return False
        
    def get_reward(self):
        """Calculate reward for this state"""
        reward = 0.0
        # Add reward components based on entity goals
        # Example: resources gathered, progress toward goal, etc.
        return reward
```

### Example: Trader State

For a trader entity, the state should track:

- Current location
- Inventory and resources
- Trading goals and preferences
- Path options

```python
class TraderState:
    def __init__(self, trader_data, world_data=None):
        self.trader_data = trader_data  # Dict with trader properties
        self.world_data = world_data or {}
        self._legal_actions = None
        
        # Cache frequently used values
        self.current_location = trader_data.get("current_location_id")
        self.gold = trader_data.get("resources", {}).get("gold", 0)
        self.inventory = trader_data.get("inventory", {})
```

## Implementing Action Generation

Actions represent choices the entity can make. Each entity type will have different actions:

### Trader Actions

```python
class TraderAction:
    def __init__(self, action_type, **kwargs):
        self.action_type = action_type  # "move", "buy", "sell", etc.
        self.__dict__.update(kwargs)

# In TraderState:
def get_legal_actions(self):
    actions = []
    
    # Movement actions
    if self.current_location:
        connections = self._get_connections()
        for conn in connections:
            actions.append(TraderAction(
                action_type="move",
                destination_id=conn["destination_id"],
                destination_name=conn["name"]
            ))
    
    # Buy/sell actions if at a settlement with market
    if self._has_market():
        for item, price in self._get_market_items():
            if self.gold >= price:
                actions.append(TraderAction(
                    action_type="buy",
                    item_id=item,
                    price=price
                ))
    
    return actions
```

### Animal Actions

```python
# In AnimalState:
def get_legal_actions(self):
    actions = []
    
    # Movement actions
    nearby_areas = self._get_nearby_areas()
    for area in nearby_areas:
        actions.append(AnimalAction(
            action_type="move",
            area_id=area["area_id"],
            energy_cost=self._calculate_movement_cost(area)
        ))
    
    # Foraging actions
    if self._can_forage():
        actions.append(AnimalAction(
            action_type="forage",
            success_chance=self._calculate_forage_chance()
        ))
    
    return actions
```

## State Transitions

State transitions define how the state changes after an action:

```python
# In TraderState:
def apply_action(self, action):
    # Create a copy of the current state
    new_trader_data = copy.deepcopy(self.trader_data)
    new_state = TraderState(new_trader_data, copy.deepcopy(self.world_data))
    
    # Apply action effects
    if action.action_type == "move":
        new_state.trader_data["current_location_id"] = action.destination_id
        # Add to visited locations
        if "visited_locations" not in new_state.trader_data:
            new_state.trader_data["visited_locations"] = []
        new_state.trader_data["visited_locations"].append(action.destination_id)
    
    elif action.action_type == "buy":
        # Update gold and inventory
        new_state.trader_data["resources"]["gold"] -= action.price
        if action.item_id not in new_state.trader_data["inventory"]:
            new_state.trader_data["inventory"][action.item_id] = 0
        new_state.trader_data["inventory"][action.item_id] += 1
    
    # Update cached values
    new_state.current_location = new_state.trader_data["current_location_id"]
    new_state.gold = new_state.trader_data["resources"].get("gold", 0)
    new_state.inventory = new_state.trader_data["inventory"]
    
    # Clear cached actions
    new_state._legal_actions = None
    
    return new_state
```

## Reward Functions

The reward function evaluates how good a state is:

```python
# In TraderState:
def get_reward(self):
    reward = 0.0
    
    # Reward for gold (wealth accumulation)
    reward += self.gold * 0.1
    
    # Reward for inventory value
    inventory_value = sum(self._get_item_value(item) * count 
                         for item, count in self.inventory.items())
    reward += inventory_value * 0.05
    
    # Reward for reaching destination
    if self.trader_data.get("destination_id") == self.current_location:
        reward += 20.0
    
    # Reward for visiting preferred locations
    preferred = self.trader_data.get("preferred_locations", [])
    if self.current_location in preferred:
        reward += 10.0
    
    # Penalty for each day traveled (to encourage efficient routes)
    travel_days = self.trader_data.get("travel_days", 0)
    reward -= travel_days * 0.5
    
    return reward
```

## Running MCTS

To use MCTS in a service:

```python
from app.ai.mcts.core import MCTS
from app.ai.mcts.trader_state import TraderState

class TraderService:
    # ...
    
    def get_trader_decision(self, trader_id):
        # Get trader entity
        trader = self.trader_manager.load_trader(trader_id)
        if not trader:
            return {"status": "error", "message": "Trader not found"}
        
        # Prepare trader data
        trader_data = {
            "trader_id": trader.trader_id,
            "name": trader.name,
            "current_location_id": trader.get_property("current_location_id"),
            "destination_id": trader.get_property("destination_id"),
            "resources": trader.get_property("resources", {}),
            "inventory": trader.get_property("inventory", {}),
            # Add other relevant properties
        }
        
        # Prepare world data
        world_data = self._get_world_data(trader.get_property("world_id"))
        
        # Create initial state
        initial_state = TraderState(trader_data, world_data)
        
        # Run MCTS
        mcts = MCTS(exploration_weight=1.0)
        best_action = mcts.search(
            root_state=initial_state,
            get_legal_actions_fn=lambda s: s.get_legal_actions(),
            apply_action_fn=lambda s, a: s.apply_action(a),
            is_terminal_fn=lambda s: s.is_terminal(),
            get_reward_fn=lambda s: s.get_reward(),
            num_simulations=100
        )
        
        # Format and return decision
        return self._format_decision(trader, best_action)
```

## Integration with Game Services

To integrate MCTS with your game services:

1. **Create a decision maker class**:

```python
class TraderDecisionMaker:
    def __init__(self, exploration_weight=1.0, num_simulations=100):
        self.exploration_weight = exploration_weight
        self.num_simulations = num_simulations
        self.world_data = {}
        
    def make_decision(self, trader):
        # Extract trader data
        trader_data = self._extract_trader_data(trader)
        
        # Create state
        state = TraderState(trader_data, self.world_data)
        
        # Run MCTS
        mcts = MCTS(exploration_weight=self.exploration_weight)
        best_action = mcts.search(
            root_state=state,
            get_legal_actions_fn=lambda s: s.get_legal_actions(),
            apply_action_fn=lambda s, a: s.apply_action(a),
            is_terminal_fn=lambda s: s.is_terminal(),
            get_reward_fn=lambda s: s.get_reward(),
            num_simulations=self.num_simulations
        )
        
        return best_action
```

2. **Use in service**:

```python
class TraderService:
    def __init__(self, db):
        self.db = db
        self.trader_manager = TraderManager()
        self.decision_maker = TraderDecisionMaker()
        
    def process_trader_movement(self, trader_id):
        # Load trader
        trader = self.trader_manager.load_trader(trader_id)
        if not trader:
            return {"status": "error", "message": "Trader not found"}
        
        # Update world data in decision maker
        self.decision_maker.world_data = self._get_current_world_data()
        
        # Get decision
        action = self.decision_maker.make_decision(trader)
        
        # Execute action
        if action.action_type == "move":
            # Process movement
            result = self._execute_movement(trader, action)
        elif action.action_type == "buy":
            # Process purchase
            result = self._execute_purchase(trader, action)
        
        return result
```

## Debugging MCTS

To debug MCTS decision making:

1. **Add visualization**:

```python
def visualize_mcts_tree(root_node, max_depth=3):
    """Visualize the MCTS tree"""
    def print_node(node, depth, path):
        indent = "  " * depth
        visits = f"visits={node.visits}"
        value = f"value={node.value:.2f}"
        action = f"action={node.action}" if node.action else ""
        print(f"{indent}{path} [{visits}, {value}] {action}")
        
        if depth < max_depth:
            for i, child in enumerate(node.children):
                print_node(child, depth + 1, f"{path}.{i}")
    
    print_node(root_node, 0, "root")
```

2. **Add logging to state functions**:

```python
def get_legal_actions(self):
    actions = self._generate_actions()
    logger.debug(f"Generated {len(actions)} actions for {self}")
    return actions

def apply_action(self, action):
    new_state = self._create_new_state(action)
    logger.debug(f"Applied {action} -> {new_state}")
    return new_state

def get_reward(self):
    reward = self._calculate_reward()
    logger.debug(f"Reward for {self}: {reward}")
    return reward
```

3. **Capture MCTS statistics**:

```python
class MCTS:
    # ...
    
    def search(self, root_state, get_legal_actions_fn, apply_action_fn, 
              is_terminal_fn, get_reward_fn, num_simulations):
        # ... existing code ...
        
        # Collect statistics
        self.statistics = {
            "root_visits": root.visits,
            "exploration_weight": self.exploration_weight,
            "num_simulations": num_simulations,
            "child_visits": {str(child.action): child.visits for child in root.children},
            "child_values": {str(child.action): child.value for child in root.children}
        }
        
        return best_action
```

## Optimization Techniques

To improve MCTS performance:

1. **Parallelization**:

```python
import concurrent.futures

def parallel_mcts_search(root_state, get_legal_actions_fn, apply_action_fn, 
                        is_terminal_fn, get_reward_fn, num_simulations, 
                        num_workers=4):
    """Run MCTS simulations in parallel"""
    # Split simulations among workers
    simulations_per_worker = num_simulations // num_workers
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
        # Start workers
        futures = []
        for _ in range(num_workers):
            future = executor.submit(
                _run_mcts_worker, 
                root_state, 
                get_legal_actions_fn,
                apply_action_fn,
                is_terminal_fn,
                get_reward_fn,
                simulations_per_worker
            )
            futures.append(future)
        
        # Collect results
        results = [future.result() for future in futures]
    
    # Merge results
    merged_results = _merge_mcts_results(results)
    return _select_best_action(merged_results)
```

2. **Neural network guidance**:

```python
class NeuralMCTS(MCTS):
    def __init__(self, policy_network, value_network, exploration_weight=1.0):
        super().__init__(exploration_weight)
        self.policy_network = policy_network
        self.value_network = value_network
    
    def search(self, root_state, get_legal_actions_fn, apply_action_fn, 
              is_terminal_fn, get_reward_fn, num_simulations):
        # Create root node
        root = MCTSNode(root_state)
        
        # Get policy predictions for legal actions
        legal_actions = get_legal_actions_fn(root_state)
        policy_probs = self.policy_network.predict(root_state, legal_actions)
        
        # Initialize node with policy prior probabilities
        for action, prob in zip(legal_actions, policy_probs):
            root.action_priors[action] = prob
        
        # ... continue with regular MCTS, but use priors for selection
```

3. **Domain-specific heuristics**:

```python
def select_child(self, exploration_weight=1.0):
    """Select child with domain-specific bonuses"""
    log_visits = math.log(self.visits) if self.visits > 0 else 0
    
    def score(child):
        # Standard UCB1 formula
        exploit = child.value / child.visits if child.visits > 0 else 0
        explore = exploration_weight * math.sqrt(log_visits / child.visits) if child.visits > 0 else float('inf')
        
        # Add domain-specific bonus
        bonus = 0
        if hasattr(child.action, 'domain_bonus'):
            bonus = child.action.domain_bonus
            
        return exploit + explore + bonus
    
    return max(self.children, key=score)
```

## Example: Putting It All Together

Here's a complete example of implementing MCTS for a trader:

```python
# In trader_service.py
def get_trader_decision(self, trader_id):
    """Get the next decision for a trader using MCTS"""
    # Load trader
    trader = self.trader_manager.load_trader(trader_id)
    if not trader:
        return {"status": "error", "message": "Trader not found"}
    
    # Prepare world data
    settlements = self._get_settlement_data(trader.get_property("world_id"))
    markets = self._get_market_data(trader.get_property("world_id"))
    
    world_data = {
        "settlements": settlements,
        "markets": markets,
        "current_day": self._get_current_day(trader.get_property("world_id"))
    }
    
    # Create trader data
    trader_data = {
        "trader_id": trader.trader_id,
        "name": trader.get_property("name"),
        "current_location_id": trader.get_property("current_location_id"),
        "destination_id": trader.get_property("destination_id"),
        "home_settlement_id": trader.get_property("home_settlement_id"),
        "resources": trader.get_property("resources", {}),
        "inventory": trader.get_property("inventory", {}),
        "preferred_settlements": trader.get_property("preferred_settlements", []),
        "preferred_biomes": trader.get_property("preferred_biomes", []),
        "visited_settlements": trader.get_property("visited_settlements", [])
    }
    
    # Create initial state
    initial_state = TraderState(trader_data, world_data)
    
    # Run MCTS
    mcts = MCTS(exploration_weight=1.0)
    best_action = mcts.search(
        root_state=initial_state,
        get_legal_actions_fn=lambda s: s.get_legal_actions(),
        apply_action_fn=lambda s, a: s.apply_action(a),
        is_terminal_fn=lambda s: s.is_terminal(),
        get_reward_fn=lambda s: s.get_reward(),
        num_simulations=100
    )
    
    # Format decision
    result = {
        "status": "success",
        "action_type": best_action.action_type,
        "trader_id": trader.trader_id,
        "trader_name": trader.get_property("name")
    }
    
    # Add action details
    if best_action.action_type == "move":
        result.update({
            "next_settlement_id": best_action.destination_id,
            "next_settlement_name": best_action.destination_name
        })
    elif best_action.action_type == "buy":
        result.update({
            "item_id": best_action.item_id,
            "price": best_action.price
        })
    
    return result
```

This should provide a solid foundation for implementing MCTS in your game. Start with a simple state representation, then refine it as you learn more about what makes good decisions for your entities.