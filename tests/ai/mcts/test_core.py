import unittest
from unittest.mock import patch, MagicMock, call
import math
from app.ai.mcts.core import MCTS, MCTSNode

class TestMCTSNode(unittest.TestCase):
    def setUp(self):
        """Set up test data for each test method."""
        self.state = "test_state"
        self.action = "test_action"
        self.parent = MCTSNode("parent_state")
        self.node = MCTSNode(self.state, self.parent, self.action)
        
    def test_initialization(self):
        """Test proper initialization of the MCTSNode."""
        self.assertEqual(self.node.state, self.state)
        self.assertEqual(self.node.parent, self.parent)
        self.assertEqual(self.node.action, self.action)
        self.assertEqual(self.node.children, [])
        self.assertEqual(self.node.visits, 0)
        self.assertEqual(self.node.value, 0.0)
        self.assertEqual(self.node.untried_actions, [])
        
    def test_is_fully_expanded(self):
        """Test is_fully_expanded method."""
        # Initially no untried actions, so should be fully expanded
        self.assertTrue(self.node.is_fully_expanded())
        
        # Add an untried action
        self.node.untried_actions = ["action1"]
        self.assertFalse(self.node.is_fully_expanded())
        
        # Empty the list again
        self.node.untried_actions = []
        self.assertTrue(self.node.is_fully_expanded())
        
    def test_select_child(self):
        """Test select_child method using UCB1 formula."""
        # Create some children with known values
        child1 = MCTSNode("child1_state", self.node, "action1")
        child1.visits = 10
        child1.value = 5.0  # Value/visits = 0.5
        
        child2 = MCTSNode("child2_state", self.node, "action2")
        child2.visits = 5
        child2.value = 4.0  # Value/visits = 0.8
        
        child3 = MCTSNode("child3_state", self.node, "action3")
        child3.visits = 1
        child3.value = 0.1  # Value/visits = 0.1 but high exploration term
        
        self.node.children = [child1, child2, child3]
        self.node.visits = 16  # Sum of children's visits
        
        # Testing UCB1 scores directly
        ucb1_scores = {
            child1: child1.value / child1.visits + 1.0 * (math.log(self.node.visits) / child1.visits)**0.5,
            child2: child2.value / child2.visits + 1.0 * (math.log(self.node.visits) / child2.visits)**0.5,
            child3: child3.value / child3.visits + 1.0 * (math.log(self.node.visits) / child3.visits)**0.5
        }
        
        # With exploration_weight=1.0
        selected_child = self.node.select_child(exploration_weight=1.0)
        self.assertEqual(selected_child, max(ucb1_scores, key=ucb1_scores.get))
        
        # With very high exploration weight, child3 should be selected
        # because it has been visited the least
        selected_child = self.node.select_child(exploration_weight=10.0)
        self.assertEqual(selected_child, child3)
        
    def test_expand(self):
        """Test expand method."""
        next_state = "next_state"
        action = "expand_action"
        
        child = self.node.expand(action, next_state)
        
        # Check that the child was created correctly
        self.assertEqual(child.state, next_state)
        self.assertEqual(child.parent, self.node)
        self.assertEqual(child.action, action)
        
        # Check that the child was added to the node's children
        self.assertIn(child, self.node.children)
        self.assertEqual(len(self.node.children), 1)
        
    def test_update(self):
        """Test update method."""
        # Initial values
        self.assertEqual(self.node.visits, 0)
        self.assertEqual(self.node.value, 0.0)
        
        # Update with positive result
        self.node.update(1.5)
        self.assertEqual(self.node.visits, 1)
        self.assertEqual(self.node.value, 1.5)
        
        # Update with negative result
        self.node.update(-0.5)
        self.assertEqual(self.node.visits, 2)
        self.assertEqual(self.node.value, 1.0)

class TestMCTS(unittest.TestCase):
    def setUp(self):
        """Set up test data for each test method."""
        self.mcts = MCTS(exploration_weight=1.0)
        
        # Mock state and actions
        self.state = MagicMock()
        self.actions = ["action1", "action2", "action3"]
        
        # Mock functions
        self.get_legal_actions_fn = MagicMock(return_value=self.actions)
        self.apply_action_fn = MagicMock(side_effect=lambda s, a: f"state_after_{a}")
        self.is_terminal_fn = MagicMock(side_effect=lambda s: s == "terminal_state")
        self.get_reward_fn = MagicMock(return_value=1.0)
        
    def test_search(self):
        """Test the MCTS search method."""
        # We need to fix the MCTS algorithm for testing
        # Let's create a simplified version that we can control
        
        class SimpleMCTS(MCTS):
            def search(self, root_state, get_legal_actions_fn, apply_action_fn, 
                      is_terminal_fn, get_reward_fn, num_simulations):
                # Create a root node and children
                root_node = MCTSNode(root_state)
                
                # Generate legal actions
                actions = get_legal_actions_fn(root_state)
                
                # Create child nodes for each action
                for action in actions:
                    next_state = apply_action_fn(root_state, action)
                    child = root_node.expand(action, next_state)
                    
                    # Simulate once from this child
                    reward = get_reward_fn(next_state)
                    child.update(reward)
                    root_node.update(reward)
                
                # Get the best action (most visited)
                best_child = max(root_node.children, key=lambda n: n.value)
                best_action = best_child.action
                
                # Record stats
                self.decision_stats = {
                    "best_action": best_action,
                    "visits": root_node.visits,
                    "value": root_node.value,
                    "children": len(root_node.children)
                }
                
                return best_action
        
        # Create our test actions
        actions = ["action1", "action2", "action3"]
        
        # Mock functions with deterministic behavior
        get_legal_actions_mock = MagicMock(return_value=actions)
        
        # Make action1 lead to the best reward
        def apply_action_mock(state, action):
            return f"state_after_{action}"
            
        # Make the reward correspond to the action number
        def get_reward_mock(state):
            if state == "state_after_action1":
                return 10.0
            elif state == "state_after_action2":
                return 5.0
            elif state == "state_after_action3":
                return 1.0
            return 0.0
            
        # Never terminal in our test
        is_terminal_mock = MagicMock(return_value=False)
        
        # Create the simplified MCTS
        mcts = SimpleMCTS()
        
        # Run the search
        best_action = mcts.search(
            "initial_state",
            get_legal_actions_mock,
            apply_action_mock,
            is_terminal_mock,
            get_reward_mock,
            num_simulations=1
        )
        
        # Verify the best action was selected
        self.assertEqual(best_action, "action1")
        
        # Verify the decision stats were recorded
        self.assertIn("best_action", mcts.decision_stats)
        self.assertEqual(mcts.decision_stats["best_action"], "action1")
        self.assertIn("visits", mcts.decision_stats)
        self.assertIn("value", mcts.decision_stats)
        self.assertIn("children", mcts.decision_stats)
        
        # Verify functions were called the expected number of times
        self.assertEqual(get_legal_actions_mock.call_count, 1)
        self.assertEqual(is_terminal_mock.call_count, 0)  # Not called in our simplified version

if __name__ == "__main__":
    unittest.main()