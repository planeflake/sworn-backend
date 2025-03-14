import math
import random
import numpy as np
from .trader_state import TraderState, TraderAction

class MCTSNode:
    """Node in the MCTS tree."""
    
    def __init__(self, state, parent=None, action=None):
        self.state = state
        self.parent = parent
        self.action = action  # Action that led to this state
        self.children = []
        self.visits = 0
        self.value = 0
        self.untried_actions = state.get_legal_actions()
        
    def is_fully_expanded(self):
        """Check if all possible actions have been tried."""
        return len(self.untried_actions) == 0
    
    def select_child(self, exploration_weight=1.0):
        """Select the best child node using UCB1 formula."""
        # UCB1 = value/visits + exploration_weight * sqrt(ln(parent visits)/visits)
        log_visits = math.log(self.visits) if self.visits > 0 else 0
        
        def ucb_score(child):
            exploitation = child.value / child.visits if child.visits > 0 else 0
            exploration = exploration_weight * math.sqrt(log_visits / child.visits) if child.visits > 0 else float('inf')
            return exploitation + exploration
        
        return max(self.children, key=ucb_score)
    
    def expand(self):
        """Expand the tree by adding a child node."""
        action = self.untried_actions.pop()
        next_state = self.state.apply_action(action)
        child = MCTSNode(next_state, self, action)
        self.children.append(child)
        return child
    
    def update(self, result):
        """Update node statistics."""
        self.visits += 1
        self.value += result
        
    def is_terminal(self):
        """Check if this node represents a terminal state."""
        return self.state.is_terminal()


class MCTS:
    """Monte Carlo Tree Search implementation."""
    
    def __init__(self, exploration_weight=1.0):
        self.exploration_weight = exploration_weight
        self.decision_stats = {}
        
    def search(self, state, num_simulations=1000, neural_network=None):
        """Run MCTS search from the given state."""
        root = MCTSNode(state)
        self.decision_stats = {
            "simulations": num_simulations,
            "actions_evaluated": 0,
            "exploration_weight": self.exploration_weight,
            "action_stats": {},
            "neural_network_used": neural_network is not None
        }
        
        for _ in range(num_simulations):
            # Selection
            node = root
            while not node.is_terminal() and node.is_fully_expanded():
                node = node.select_child(self.exploration_weight)
            
            # Expansion
            if not node.is_terminal() and not node.is_fully_expanded():
                node = node.expand()
            
            # Simulation
            if neural_network:
                # Use neural network for evaluation
                reward = self._simulate_with_nn(node.state, neural_network)
            else:
                # Use random simulation
                reward = self._simulate(node.state)
            
            # Backpropagation
            while node is not None:
                node.update(reward)
                node = node.parent
        
        # Collect statistics for all actions
        self.decision_stats["actions_evaluated"] = len(root.children)
        
        for child in root.children:
            if child.action:
                action_key = child.action.destination
                self.decision_stats["action_stats"][action_key] = {
                    "visits": child.visits,
                    "value": child.value,
                    "average_value": child.value / child.visits if child.visits > 0 else 0,
                    "ucb_score": (child.value / child.visits if child.visits > 0 else 0) + 
                                self.exploration_weight * math.sqrt(math.log(root.visits) / child.visits if child.visits > 0 else float('inf'))
                }
        
        # Return the best action
        if not root.children:
            return None
            
        best_child = max(root.children, key=lambda n: n.visits)
        self.decision_stats["best_action"] = best_child.action.destination if best_child.action else None
        self.decision_stats["best_action_visits"] = best_child.visits
        self.decision_stats["best_action_value"] = best_child.value
        
        return best_child.action
    
    def _simulate(self, state):
        """Run a random simulation from this state until terminal."""
        current_state = state
        depth = 0
        max_depth = 10  # Limit simulation depth
        
        while not current_state.is_terminal() and depth < max_depth:
            actions = current_state.get_legal_actions()
            if not actions:
                break
                
            action = random.choice(actions)
            current_state = current_state.apply_action(action)
            depth += 1
        
        return current_state.get_reward()
    
    def _simulate_with_nn(self, state, neural_network):
        """Use neural network to evaluate the state."""
        # Extract features
        features = np.array([state.get_state_features()])
        
        # Get predicted value from neural network - different API for scikit-learn
        if neural_network:
            # Transform features
            features_scaled = neural_network['scaler'].transform(features)
            
            # Get predicted value
            value = neural_network['model'].predict(features_scaled)[0]
            return value
        else:
            # Fallback to random simulation if model is not available
            return self._simulate(state)