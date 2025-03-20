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
               num_simulations: int) -> A:
        """Run MCTS search to find the best action."""
        root_node = MCTSNode(root_state)
        
        for _ in range(num_simulations):
            node = root_node
            state = root_state
            
            # Selection
            while not node.is_fully_expanded() and not is_terminal_fn(state):
                action = random.choice(node.untried_actions)
                state = apply_action_fn(state, action)
                if action not in node.untried_actions:
                    node.untried_actions.append(action)
                node = node.expand(action, state)
            
            # Expansion
            if not is_terminal_fn(state):
                action = random.choice(node.untried_actions)
                state = apply_action_fn(state, action)
                node = node.expand(action, state)
            
            # Simulation
            while not is_terminal_fn(state):
                action = random.choice(get_legal_actions_fn(state))
                state = apply_action_fn(state, action)
            
            # Backpropagation
            reward = get_reward_fn(state)
            while node is not None:
                node.update(reward)
                node = node.parent
        
        # Get the best action
        best_child = max(root_node.children, key=lambda n: n.visits)
        best_action = best_child.action
        self.decision_stats = {
            "best_action": best_action,
            "visits": root_node.visits,
            "value": root_node.value,
            "children": len(root_node.children)
        }
        
        return best_action