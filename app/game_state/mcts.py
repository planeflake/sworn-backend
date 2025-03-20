import math
import random
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Generic, TypeVar
import logging

# Type variables for state and action
S = TypeVar('S')  # State type
A = TypeVar('A')  # Action type

class MCTSNode(Generic[S, A]):
    """Node in the Monte Carlo Tree Search"""
    
    def __init__(self, state: S, parent=None, action: Optional[A] = None):
        self.state = state
        self.parent = parent
        self.action = action  # Action that led to this state
        self.children: List['MCTSNode'] = []
        self.visits = 0
        self.value = 0.0
        self.untried_actions: List[A] = []
        
    def is_fully_expanded(self) -> bool:
        """Check if all possible actions have been tried."""
        return len(self.untried_actions) == 0
    
    def select_child(self, exploration_weight: float = 1.0) -> 'MCTSNode':
        """Select the best child node using UCB1 formula."""
        # UCB1 = value/visits + exploration_weight * sqrt(ln(parent visits)/visits)
        log_visits = math.log(self.visits) if self.visits > 0 else 0
        
        def ucb_score(child: 'MCTSNode') -> float:
            exploitation = child.value / child.visits if child.visits > 0 else 0
            exploration = exploration_weight * math.sqrt(log_visits / child.visits) if child.visits > 0 else float('inf')
            return exploitation + exploration
        
        return max(self.children, key=ucb_score)
    
    def expand(self, action: A, next_state: S) -> 'MCTSNode':
        """Expand the tree by adding a child node."""
        child = MCTSNode(next_state, self, action)
        self.children.append(child)
        return child
    
    def update(self, result: float) -> None:
        """Update node statistics."""
        self.visits += 1
        self.value += result

class MCTS(Generic[S, A]):
    """Monte Carlo Tree Search implementation."""
    
    def __init__(self, exploration_weight: float = 1.0):
        self.exploration_weight = exploration_weight
        self.decision_stats: Dict[str, Any] = {}
        
    def search(self, 
               root_state: S, 
               get_legal_actions_fn, 
               apply_action_fn, 
               is_terminal_fn, 
               get_reward_fn,
               num_simulations: int = 1000) -> Optional[A]:
        """
        Run MCTS search from the given state.
        
        Args:
            root_state: The starting state
            get_legal_actions_fn: Function that returns legal actions from a state
            apply_action_fn: Function that applies an action to a state and returns new state
            is_terminal_fn: Function that checks if a state is terminal
            get_reward_fn: Function that returns the reward for a state
            num_simulations: Number of simulations to run
            
        Returns:
            The best action to take, or None if no actions are available
        """
        logger = logging.getLogger(__name__)
        
        logger.info(f"MCTS TRACE: Starting MCTS search with {num_simulations} simulations")
        
        root = MCTSNode(root_state)
        root.untried_actions = get_legal_actions_fn(root_state)
        
        logger.info(f"MCTS TRACE: Root node has {len(root.untried_actions)} untried actions")
        
        self.decision_stats = {
            "simulations": num_simulations,
            "actions_evaluated": 0,
            "exploration_weight": self.exploration_weight,
            "action_stats": {},
        }
        
        for i in range(num_simulations):
            if i % 10 == 0:
                logger.info(f"MCTS TRACE: Running simulation {i+1}/{num_simulations}")
                
            # Selection
            node = root
            selection_path = []
            while not is_terminal_fn(node.state) and node.is_fully_expanded():
                node = node.select_child(self.exploration_weight)
                if node.action:
                    selection_path.append(str(node.action))
            
            if selection_path:
                logger.info(f"MCTS TRACE: Selection path: {' -> '.join(selection_path)}")
            
            # Expansion
            if not is_terminal_fn(node.state) and not node.is_fully_expanded():
                if not node.untried_actions:
                    logger.warning(f"MCTS TRACE: Node has no untried actions but is not fully expanded")
                else:
                    action = node.untried_actions.pop()
                    logger.info(f"MCTS TRACE: Expanding with action: {action}")
                    next_state = apply_action_fn(node.state, action)
                    node = node.expand(action, next_state)
            
            # Simulation
            reward = self._simulate(node.state, get_legal_actions_fn, apply_action_fn, is_terminal_fn, get_reward_fn)
            logger.info(f"MCTS TRACE: Simulation returned reward: {reward}")
            
            # Backpropagation
            while node is not None:
                node.update(reward)
                node = node.parent
        
        logger.info(f"MCTS TRACE: Completed {num_simulations} simulations")
        
        # Collect statistics for all actions
        self.decision_stats["actions_evaluated"] = len(root.children)
        
        for child in root.children:
            if child.action:
                action_key = str(child.action)
                self.decision_stats["action_stats"][action_key] = {
                    "visits": child.visits,
                    "value": child.value,
                    "average_value": child.value / child.visits if child.visits > 0 else 0,
                    "ucb_score": (child.value / child.visits if child.visits > 0 else 0) + 
                                self.exploration_weight * math.sqrt(math.log(root.visits) / child.visits if child.visits > 0 else float('inf'))
                }
        
        # Return the best action
        if not root.children:
            logger.error(f"MCTS TRACE: No children were created during simulation")
            return None
            
        # Log all children and their values
        for i, child in enumerate(root.children):
            logger.info(f"MCTS TRACE: Child {i+1}: visits={child.visits}, value={child.value}, " +
                        f"avg_value={child.value/child.visits if child.visits > 0 else 0}")
        
        best_child = max(root.children, key=lambda n: n.visits)
        logger.info(f"MCTS TRACE: Best child: visits={best_child.visits}, " +
                    f"value={best_child.value}, action={best_child.action}")
        
        return best_child.action
    
    def _simulate(self, 
                  state: S, 
                  get_legal_actions_fn, 
                  apply_action_fn, 
                  is_terminal_fn, 
                  get_reward_fn,
                  max_depth: int = 10) -> float:
        """Run a random simulation from this state until terminal."""
        logger = logging.getLogger(__name__)
        
        current_state = state
        depth = 0
        
        while not is_terminal_fn(current_state) and depth < max_depth:
            actions = get_legal_actions_fn(current_state)
            if not actions:
                logger.warning(f"MCTS TRACE: Simulation reached state with no legal actions at depth {depth}")
                break
                
            action = random.choice(actions)
            logger.info(f"MCTS TRACE: Simulation at depth {depth} chose action: {action}")
            
            current_state = apply_action_fn(current_state, action)
            depth += 1
        
        reward = get_reward_fn(current_state)
        logger.info(f"MCTS TRACE: Simulation ended at depth {depth} with reward {reward}")
        
        return reward