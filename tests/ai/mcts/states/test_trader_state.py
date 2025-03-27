import unittest
from unittest.mock import patch, MagicMock
import copy
from app.ai.mcts.states.trader_state import TraderState, TraderAction

class TestTraderState(unittest.TestCase):
    def setUp(self):
        """Set up test data for each test method."""
        self.trader_data = {
            "trader_id": "trader_123",
            "name": "Test Trader",
            "current_location_id": "settlement_1",
            "destination_id": "settlement_3",
            "gold": 500,
            "inventory": {"item_1": 2, "item_2": 1},
            "preferred_settlements": ["settlement_3", "settlement_5"],
            "preferred_biomes": ["forest", "mountains"],
            "visited_settlements": ["settlement_1", "settlement_2"],
            "is_traveling": False,
            "is_settled": False,
            "is_retired": False,
            "has_shop": False,
            "life_goals": [
                {"name": "Explore all settlements", "progress": 20, "is_retirement_goal": False},
                {"name": "Get rich", "progress": 30, "is_retirement_goal": True}
            ]
        }
        
        self.world_data = {
            "settlements": {
                "settlement_1": {
                    "name": "Riverdale",
                    "biome": "plains",
                    "connections": [
                        {
                            "destination_id": "settlement_2",
                            "destination": "Oakville",
                            "path": ["area_1", "area_2"]
                        },
                        {
                            "destination_id": "settlement_3",
                            "destination": "Pine Forest",
                            "path": ["area_3"]
                        }
                    ]
                },
                "settlement_2": {
                    "name": "Oakville",
                    "biome": "forest",
                    "connections": []
                },
                "settlement_3": {
                    "name": "Pine Forest",
                    "biome": "forest",
                    "connections": []
                },
                "settlement_4": {
                    "name": "Mountain Peak",
                    "biome": "mountains",
                    "connections": []
                },
                "settlement_5": {
                    "name": "Desert Oasis",
                    "biome": "desert",
                    "connections": []
                }
            },
            "markets": {
                "settlement_1": {
                    "selling": {"item_3": 50, "item_4": 100},
                    "buying": {"item_1": 60, "item_2": 80}
                },
                "settlement_2": {
                    "selling": {"item_1": 40, "item_2": 70},
                    "buying": {"item_3": 70, "item_4": 120}
                }
            },
            "items": {
                "item_1": {"base_value": 50, "name": "Wheat"},
                "item_2": {"base_value": 75, "name": "Iron"},
                "item_3": {"base_value": 45, "name": "Wood"},
                "item_4": {"base_value": 90, "name": "Gold Ore"}
            }
        }
        
        self.state = TraderState(self.trader_data, self.world_data)
        
    def test_initialization(self):
        """Test proper initialization of the TraderState."""
        self.assertEqual(self.state.trader_data["trader_id"], "trader_123")
        self.assertEqual(self.state.current_settlement_id, "settlement_1")
        self.assertEqual(self.state.destination_id, "settlement_3")
        self.assertEqual(self.state.gold, 500)
        self.assertEqual(self.state.inventory, {"item_1": 2, "item_2": 1})
        self.assertFalse(self.state.is_traveling)
        self.assertFalse(self.state.is_settled)
        self.assertFalse(self.state.is_retired)
        self.assertFalse(self.state.has_shop)
        
    def test_get_legal_actions(self):
        """Test that all expected legal actions are generated."""
        actions = self.state.get_legal_actions()
        
        # Verify we get the expected number of actions (2 move actions, 2 sell actions, 
        # 2 buy actions, and 1 rest action)
        self.assertEqual(len(actions), 7)
        
        # Check for move actions
        move_actions = [a for a in actions if a.action_type == "move"]
        self.assertEqual(len(move_actions), 2)
        
        # Check destinations of move actions
        move_destinations = set(a.destination_id for a in move_actions)
        self.assertIn("settlement_2", move_destinations)
        self.assertIn("settlement_3", move_destinations)
        
        # Check for buy actions
        buy_actions = [a for a in actions if a.action_type == "buy"]
        self.assertEqual(len(buy_actions), 2)
        
        # Check items being bought
        buy_items = set(a.item_id for a in buy_actions)
        self.assertIn("item_3", buy_items)
        self.assertIn("item_4", buy_items)
        
        # Check for sell actions
        sell_actions = [a for a in actions if a.action_type == "sell"]
        self.assertEqual(len(sell_actions), 2)
        
        # Check items being sold
        sell_items = set(a.item_id for a in sell_actions)
        self.assertIn("item_1", sell_items)
        self.assertIn("item_2", sell_items)
        
        # Check for rest action
        rest_actions = [a for a in actions if a.action_type == "rest"]
        self.assertEqual(len(rest_actions), 1)
        
    def test_apply_action_move(self):
        """Test applying a move action."""
        # Create a move action to settlement_3 (Pine Forest)
        move_action = TraderAction(
            action_type="move",
            destination_id="settlement_3",
            destination_name="Pine Forest",
            area_path=["area_3"]
        )
        
        # Apply the action
        new_state = self.state.apply_action(move_action)
        
        # Check the new state is updated correctly
        self.assertEqual(new_state.current_settlement_id, "settlement_3")
        self.assertIn("settlement_3", new_state.visited_settlements)
        
        # The destination_id should be cleared because we reached it
        self.assertIsNone(new_state.trader_data.get("destination_id"))
        
        # Check traveling status
        self.assertTrue(new_state.is_traveling)
        
        # Ensure the original state was not modified (immutability)
        self.assertEqual(self.state.current_settlement_id, "settlement_1")
        self.assertEqual(self.state.destination_id, "settlement_3")
        
    def test_apply_action_buy(self):
        """Test applying a buy action."""
        # Create a buy action for item_3 (Wood)
        buy_action = TraderAction(
            action_type="buy",
            item_id="item_3",
            price=50
        )
        
        # Apply the action
        new_state = self.state.apply_action(buy_action)
        
        # Check the new state is updated correctly
        self.assertEqual(new_state.gold, 450)  # 500 - 50
        self.assertEqual(new_state.inventory.get("item_3", 0), 1)
        
        # Ensure the original state was not modified (immutability)
        self.assertEqual(self.state.gold, 500)
        self.assertNotIn("item_3", self.state.inventory)
        
    def test_apply_action_sell(self):
        """Test applying a sell action."""
        # Create a sell action for item_1 (Wheat)
        sell_action = TraderAction(
            action_type="sell",
            item_id="item_1",
            price=60
        )
        
        # Apply the action
        new_state = self.state.apply_action(sell_action)
        
        # Check the new state is updated correctly
        self.assertEqual(new_state.gold, 560)  # 500 + 60
        
        # Should have one less item_1
        self.assertEqual(new_state.inventory.get("item_1", 0), 1)
        
        # Ensure the original state was not modified (immutability)
        self.assertEqual(self.state.gold, 500)
        self.assertEqual(self.state.inventory.get("item_1"), 2)
        
    def test_apply_action_settle(self):
        """Test applying a settle action."""
        # Create a settle action
        settle_action = TraderAction(
            action_type="settle",
            destination_id="settlement_1"
        )
        
        # Apply the action
        new_state = self.state.apply_action(settle_action)
        
        # Check the new state is updated correctly
        self.assertTrue(new_state.is_settled)
        self.assertFalse(new_state.is_traveling)
        
        # Ensure the original state was not modified (immutability)
        self.assertFalse(self.state.is_settled)
        
    def test_apply_action_open_shop(self):
        """Test applying an open shop action."""
        # Create an open shop action
        shop_action = TraderAction(
            action_type="open_shop",
            destination_id="settlement_1",
            destination_name="Riverdale"
        )
        
        # Apply the action
        new_state = self.state.apply_action(shop_action)
        
        # Check the new state is updated correctly
        self.assertTrue(new_state.has_shop)
        self.assertTrue(new_state.is_settled)
        self.assertFalse(new_state.is_traveling)
        self.assertEqual(new_state.gold, 0)  # 500 - 500 (shop cost)
        
        # Ensure the original state was not modified (immutability)
        self.assertFalse(self.state.has_shop)
        self.assertEqual(self.state.gold, 500)
        
    def test_apply_action_retire(self):
        """Test applying a retire action."""
        # Create a retire action
        retire_action = TraderAction(action_type="retire")
        
        # Apply the action
        new_state = self.state.apply_action(retire_action)
        
        # Check the new state is updated correctly
        self.assertTrue(new_state.is_retired)
        self.assertFalse(new_state.is_traveling)
        
        # Ensure the original state was not modified (immutability)
        self.assertFalse(self.state.is_retired)
        
    def test_is_terminal(self):
        """Test terminal state conditions."""
        # Standard state is not terminal
        self.assertFalse(self.state.is_terminal())
        
        # Retired state is terminal
        retired_data = copy.deepcopy(self.trader_data)
        retired_data["is_retired"] = True
        retired_state = TraderState(retired_data, self.world_data)
        self.assertTrue(retired_state.is_terminal())
        
        # Shop owner state is terminal
        shop_data = copy.deepcopy(self.trader_data)
        shop_data["has_shop"] = True
        shop_state = TraderState(shop_data, self.world_data)
        self.assertTrue(shop_state.is_terminal())
        
        # Visited all settlements
        all_visited_data = copy.deepcopy(self.trader_data)
        all_visited_data["visited_settlements"] = ["settlement_1", "settlement_2", "settlement_3", 
                                                   "settlement_4", "settlement_5"]
        all_visited_state = TraderState(all_visited_data, self.world_data)
        self.assertTrue(all_visited_state.is_terminal())
        
        # Long simulation days
        long_sim_state = TraderState(self.trader_data, self.world_data)
        long_sim_state.simulation_days = 101
        self.assertTrue(long_sim_state.is_terminal())
        
    def test_get_reward(self):
        """Test reward calculation."""
        # Base state reward calculation
        base_reward = self.state.get_reward()
        self.assertGreater(base_reward, 0.0)
        
        # Retired trader should have a higher reward
        retired_data = copy.deepcopy(self.trader_data)
        retired_data["is_retired"] = True
        retired_state = TraderState(retired_data, self.world_data)
        retired_reward = retired_state.get_reward()
        self.assertGreater(retired_reward, base_reward)
        
        # Shop owner should have a higher reward than base
        shop_data = copy.deepcopy(self.trader_data)
        shop_data["has_shop"] = True
        shop_data["shop_location_id"] = "settlement_3"  # A preferred forest settlement
        shop_state = TraderState(shop_data, self.world_data)
        shop_reward = shop_state.get_reward()
        self.assertGreater(shop_reward, base_reward)
        
        # Rich trader should have a higher reward
        rich_data = copy.deepcopy(self.trader_data)
        rich_data["gold"] = 2000
        rich_state = TraderState(rich_data, self.world_data)
        rich_reward = rich_state.get_reward()
        self.assertGreater(rich_reward, base_reward)
        
    def test_from_trader_entity(self):
        """Test creating state from trader entity."""
        # Create a mock trader entity with get_property method
        mock_trader = MagicMock()
        mock_trader.trader_id = "trader_123"
        # Make to_dict return empty to force using get_property path
        mock_trader.to_dict.return_value = {}
        
        properties = {
            "name": "Test Trader",
            "current_location_id": "settlement_1",
            "destination_id": "settlement_3",
            "gold": 500,
            "inventory": {"item_1": 2, "item_2": 1},
            "preferred_settlements": ["settlement_3", "settlement_5"],
            "preferred_biomes": ["forest", "mountains"],
            "visited_settlements": ["settlement_1", "settlement_2"],
            "is_traveling": False,
            "is_settled": False,
            "is_retired": False,
            "has_shop": False,
        }
        
        mock_trader.get_property.side_effect = lambda key, default=None: properties.get(key, default)
        
        # Create state from entity
        state = TraderState.from_trader_entity(mock_trader)
        
        # Verify the state was created correctly using get_property path
        self.assertEqual(state.trader_data["trader_id"], "trader_123")
        self.assertEqual(state.current_settlement_id, "settlement_1")
        self.assertEqual(state.destination_id, "settlement_3")
        self.assertEqual(state.gold, 500)
        
        # Test with entity that has a working to_dict method
        mock_dict_trader = MagicMock()
        mock_dict_trader.to_dict.return_value = self.trader_data
        
        state_from_dict = TraderState.from_trader_entity(mock_dict_trader)
        
        # Check that trader_data was set correctly from the dict
        self.assertEqual(state_from_dict.trader_data["trader_id"], "trader_123")
        
    def test_action_serialization(self):
        """Test TraderAction serialization and deserialization."""
        # Create an action
        action = TraderAction(
            action_type="move",
            destination_id="settlement_3",
            destination_name="Pine Forest",
            area_path=["area_3"]
        )
        action.risk_level = 0.2
        action.estimated_profit = 100.0
        
        # Convert to dict
        action_dict = action.to_dict()
        
        # Create new action from dict
        new_action = TraderAction.from_dict(action_dict)
        
        # Verify the new action matches the original
        self.assertEqual(new_action.action_type, "move")
        self.assertEqual(new_action.destination_id, "settlement_3")
        self.assertEqual(new_action.destination_name, "Pine Forest")
        self.assertEqual(new_action.area_path, ["area_3"])
        self.assertEqual(new_action.risk_level, 0.2)
        self.assertEqual(new_action.estimated_profit, 100.0)
        
    def test_string_representation(self):
        """Test string representation of state and action."""
        # Action string representation
        move_action = TraderAction(
            action_type="move",
            destination_id="settlement_3",
            destination_name="Pine Forest"
        )
        self.assertEqual(str(move_action), "Move to Pine Forest")
        
        buy_action = TraderAction(
            action_type="buy",
            item_id="item_3",
            price=50
        )
        self.assertEqual(str(buy_action), "Buy item_3 for 50")
        
        # State string representation
        state_str = str(self.state)
        self.assertIn("Test Trader", state_str)
        self.assertIn("Riverdale", state_str)
        self.assertIn("500 gold", state_str)

if __name__ == "__main__":
    unittest.main()