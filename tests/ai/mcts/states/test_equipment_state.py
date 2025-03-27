import unittest
from unittest.mock import patch, MagicMock
import copy
from app.ai.mcts.states.equipment_state import EquipmentState, EquipmentAction

class TestEquipmentState(unittest.TestCase):
    def setUp(self):
        """Set up test data for each test method."""
        self.equipment_data = {
            "equipment_id": "eq_char_123",
            "character_id": "char_123",
            "slots": {
                "head": "item_1",
                "chest": "item_2",
                "weapon": None,
                "shield": None
            }
        }
        
        self.world_data = {
            "characters": {
                "char_123": {
                    "name": "Test Character",
                    "inventory_items": ["item_3", "item_4", "item_5", "item_6"]
                }
            },
            "items": {
                "item_1": {
                    "id": "item_1",
                    "name": "Steel Helmet",
                    "slot_type": "head",
                    "quality": 80,
                    "durability": 90,
                    "value": 150,
                    "is_equippable": True,
                    "is_equipped": True,
                    "equipment_type": "plate"
                },
                "item_2": {
                    "id": "item_2",
                    "name": "Leather Chest",
                    "slot_type": "chest",
                    "quality": 65,
                    "durability": 70,
                    "value": 120,
                    "is_equippable": True,
                    "is_equipped": True,
                    "equipment_type": "leather"
                },
                "item_3": {
                    "id": "item_3",
                    "name": "Iron Sword",
                    "slot_type": "weapon",
                    "quality": 70,
                    "durability": 85,
                    "value": 180,
                    "is_equippable": True,
                    "is_equipped": False,
                    "equipment_type": "metal"
                },
                "item_4": {
                    "id": "item_4",
                    "name": "Wooden Shield",
                    "slot_type": "shield",
                    "quality": 50,
                    "durability": 60,
                    "value": 90,
                    "is_equippable": True,
                    "is_equipped": False,
                    "equipment_type": "wood"
                },
                "item_5": {
                    "id": "item_5",
                    "name": "Damaged Plate Chest",
                    "slot_type": "chest",
                    "quality": 85,
                    "durability": 30,
                    "value": 200,
                    "is_equippable": True,
                    "is_equipped": False,
                    "equipment_type": "plate"
                },
                "item_6": {
                    "id": "item_6",
                    "name": "Health Potion",
                    "slot_type": None,
                    "quality": 100,
                    "durability": 100,
                    "value": 50,
                    "is_equippable": False,
                    "is_equipped": False
                }
            }
        }
        
        self.state = EquipmentState(self.equipment_data, self.world_data)
        
    def test_initialization(self):
        """Test proper initialization of the EquipmentState."""
        self.assertEqual(self.state.equipment_id, "eq_char_123")
        self.assertEqual(self.state.character_id, "char_123")
        self.assertEqual(self.state.slots, {
            "head": "item_1",
            "chest": "item_2",
            "weapon": None,
            "shield": None
        })
        
    def test_get_legal_actions(self):
        """Test that all expected legal actions are generated."""
        actions = self.state.get_legal_actions()
        
        # We expect actions for:
        # - Unequip head item (item_1)
        # - Unequip chest item (item_2)
        # - Equip weapon (item_3)
        # - Equip shield (item_4)
        # - Swap chest with damaged plate chest (item_5)
        # - Repair chest item (item_2) if durability < 75, which it is (70)
        
        # Check if our action count is correct
        self.assertEqual(len(actions), 6)
        
        # Check for unequip actions
        unequip_actions = [a for a in actions if a.action_type == "unequip"]
        self.assertEqual(len(unequip_actions), 2)
        
        # Check for equip actions (weapon and shield)
        equip_actions = [a for a in actions if a.action_type == "equip"]
        self.assertEqual(len(equip_actions), 2)
        
        # Check for swap actions (chest)
        swap_actions = [a for a in actions if a.action_type == "swap"]
        self.assertEqual(len(swap_actions), 1)
        
        # Check for repair actions
        repair_actions = [a for a in actions if a.action_type == "repair"]
        self.assertEqual(len(repair_actions), 1)
        
        # Verify specific actions
        # Check for equip weapon action
        weapon_actions = [a for a in actions if a.action_type == "equip" and a.slot == "weapon"]
        self.assertEqual(len(weapon_actions), 1)
        self.assertEqual(weapon_actions[0].item_id, "item_3")
        
        # Check for equip shield action
        shield_actions = [a for a in actions if a.action_type == "equip" and a.slot == "shield"]
        self.assertEqual(len(shield_actions), 1)
        self.assertEqual(shield_actions[0].item_id, "item_4")
        
        # Check for swap chest action
        chest_swap_actions = [a for a in actions if a.action_type == "swap" and a.slot == "chest"]
        self.assertEqual(len(chest_swap_actions), 1)
        self.assertEqual(chest_swap_actions[0].item_id, "item_5")
        
    def test_apply_action_equip(self):
        """Test applying an equip action."""
        # Create an equip action for sword
        equip_action = EquipmentAction(
            action_type="equip",
            slot="weapon",
            item_id="item_3"
        )
        
        # Apply the action
        new_state = self.state.apply_action(equip_action)
        
        # Check that the weapon slot has been updated
        self.assertEqual(new_state.slots["weapon"], "item_3")
        
        # Check that the item status has been updated in world data
        self.assertTrue(new_state.world_data["items"]["item_3"]["is_equipped"])
        
        # Durability should be slightly reduced
        self.assertEqual(new_state.world_data["items"]["item_3"]["durability"], 84)  # 85 - 1
        
        # Original state should be unchanged
        self.assertIsNone(self.state.slots["weapon"])
        self.assertFalse(self.world_data["items"]["item_3"]["is_equipped"])
        self.assertEqual(self.world_data["items"]["item_3"]["durability"], 85)
        
    def test_apply_action_unequip(self):
        """Test applying an unequip action."""
        # Create an unequip action for helmet
        unequip_action = EquipmentAction(
            action_type="unequip",
            slot="head",
            item_id="item_1"
        )
        
        # Apply the action
        new_state = self.state.apply_action(unequip_action)
        
        # Check that the head slot has been cleared
        self.assertIsNone(new_state.slots["head"])
        
        # Check that the item status has been updated in world data
        self.assertFalse(new_state.world_data["items"]["item_1"]["is_equipped"])
        
        # Original state should be unchanged
        self.assertEqual(self.state.slots["head"], "item_1")
        self.assertTrue(self.world_data["items"]["item_1"]["is_equipped"])
        
    def test_apply_action_swap(self):
        """Test applying a swap action."""
        # Create a swap action for chest
        swap_action = EquipmentAction(
            action_type="swap",
            slot="chest",
            item_id="item_5"
        )
        
        # Apply the action
        new_state = self.state.apply_action(swap_action)
        
        # Check that the chest slot has the new item
        self.assertEqual(new_state.slots["chest"], "item_5")
        
        # Check that the item statuses have been updated in world data
        self.assertFalse(new_state.world_data["items"]["item_2"]["is_equipped"])
        self.assertTrue(new_state.world_data["items"]["item_5"]["is_equipped"])
        
        # Durability should be slightly reduced on the newly equipped item
        self.assertEqual(new_state.world_data["items"]["item_5"]["durability"], 29)  # 30 - 1
        
        # Original state should be unchanged
        self.assertEqual(self.state.slots["chest"], "item_2")
        self.assertTrue(self.world_data["items"]["item_2"]["is_equipped"])
        self.assertFalse(self.world_data["items"]["item_5"]["is_equipped"])
        self.assertEqual(self.world_data["items"]["item_5"]["durability"], 30)
        
    def test_apply_action_repair(self):
        """Test applying a repair action."""
        # Create a repair action for chest armor
        repair_action = EquipmentAction(
            action_type="repair",
            slot="chest",
            item_id="item_2"
        )
        
        # Apply the action
        new_state = self.state.apply_action(repair_action)
        
        # Check that durability has increased
        self.assertEqual(new_state.world_data["items"]["item_2"]["durability"], 95)  # 70 + 25
        
        # Original state should be unchanged
        self.assertEqual(self.world_data["items"]["item_2"]["durability"], 70)
        
    def test_is_terminal(self):
        """Test terminal state conditions."""
        # Basic state is not terminal
        self.assertFalse(self.state.is_terminal())
        
        # Create a state with perfect equipment in all slots
        perfect_data = copy.deepcopy(self.equipment_data)
        perfect_data["slots"] = {
            "head": "item_1",     # Already good
            "chest": "item_7",    # New perfect chest
            "legs": "item_8",     # New perfect legs
            "hands": "item_9",    # New perfect hands
            "feet": "item_10",    # New perfect feet
            "weapon": "item_11",  # New perfect weapon 
            "shield": "item_12"   # New perfect shield
        }
        
        perfect_world = copy.deepcopy(self.world_data)
        for item_id in ["item_7", "item_8", "item_9", "item_10", "item_11", "item_12"]:
            perfect_world["items"][item_id] = {
                "id": item_id,
                "quality": 90,
                "durability": 95,
                "is_equipped": True
            }
            
        perfect_state = EquipmentState(perfect_data, perfect_world)
        
        # Perfect equipment state should be terminal
        self.assertTrue(perfect_state.is_terminal())
        
    def test_get_reward(self):
        """Test reward calculation."""
        # Basic state reward
        base_reward = self.state.get_reward()
        
        # Create a state with helmet + chest + weapon + shield
        better_data = copy.deepcopy(self.equipment_data)
        better_data["slots"]["weapon"] = "item_3"
        better_data["slots"]["shield"] = "item_4"
        
        better_world = copy.deepcopy(self.world_data)
        better_world["items"]["item_3"]["is_equipped"] = True
        better_world["items"]["item_4"]["is_equipped"] = True
        
        better_state = EquipmentState(better_data, better_world)
        better_reward = better_state.get_reward()
        
        # More equipment should result in higher reward
        self.assertGreater(better_reward, base_reward)
        
        # Create a state with matching equipment (all plate)
        matching_data = copy.deepcopy(self.equipment_data)
        matching_data["slots"] = {
            "head": "item_1",     # Plate
            "chest": "item_5",    # Plate
            "legs": "item_13",    # Plate
            "feet": "item_14",    # Plate
            "weapon": None,
            "shield": None
        }
        
        matching_world = copy.deepcopy(self.world_data)
        matching_world["items"]["item_5"]["is_equipped"] = True
        matching_world["items"]["item_13"] = {
            "id": "item_13",
            "name": "Plate Leggings",
            "slot_type": "legs",
            "quality": 75,
            "durability": 80,
            "value": 130,
            "is_equipped": True,
            "equipment_type": "plate"
        }
        matching_world["items"]["item_14"] = {
            "id": "item_14",
            "name": "Plate Boots",
            "slot_type": "feet",
            "quality": 75,
            "durability": 80,
            "value": 120,
            "is_equipped": True,
            "equipment_type": "plate"
        }
        
        matching_state = EquipmentState(matching_data, matching_world)
        matching_reward = matching_state.get_reward()
        
        # Matching equipment set should have higher reward
        self.assertGreater(matching_reward, base_reward)
        
    def test_from_equipment_entity(self):
        """Test creating state from equipment entity."""
        # Create a mock equipment entity with to_dict
        mock_equipment = MagicMock()
        mock_equipment.to_dict.return_value = self.equipment_data
        
        # Create state from entity
        state = EquipmentState.from_equipment_entity(mock_equipment, self.world_data)
        
        # Verify the state was created correctly
        self.assertEqual(state.equipment_id, "eq_char_123")
        self.assertEqual(state.character_id, "char_123")
        self.assertEqual(state.slots["head"], "item_1")
        
        # Test with entity that has direct properties
        direct_equipment = MagicMock()
        direct_equipment.equipment_id = "eq_char_123"
        direct_equipment.character_id = "char_123"
        direct_equipment.slots = {
            "head": "item_1",
            "chest": "item_2"
        }
        
        # To_dict returns empty
        direct_equipment.to_dict.return_value = {}
        
        direct_state = EquipmentState.from_equipment_entity(direct_equipment, self.world_data)
        
        # Verify the state was created correctly
        self.assertEqual(direct_state.equipment_id, "eq_char_123")
        self.assertEqual(direct_state.character_id, "char_123")
        self.assertEqual(direct_state.slots["head"], "item_1")
        
    def test_action_serialization(self):
        """Test EquipmentAction serialization and deserialization."""
        # Create a complex action
        action = EquipmentAction(
            action_type="swap", 
            slot="chest",
            item_id="item_5"
        )
        action.target_slot = "storage"
        action.score = 1.75
        
        # Convert to dict
        action_dict = action.to_dict()
        
        # Create new action from dict
        new_action = EquipmentAction.from_dict(action_dict)
        
        # Verify properties match
        self.assertEqual(new_action.action_type, "swap")
        self.assertEqual(new_action.slot, "chest")
        self.assertEqual(new_action.item_id, "item_5")
        self.assertEqual(new_action.target_slot, "storage")
        self.assertEqual(new_action.score, 1.75)
        
    def test_string_representation(self):
        """Test string representation of state and action."""
        # Test string representation of action
        equip_action = EquipmentAction(
            action_type="equip",
            slot="weapon",
            item_id="item_3"
        )
        self.assertEqual(str(equip_action), "Equip item item_3 to weapon")
        
        unequip_action = EquipmentAction(
            action_type="unequip",
            slot="head"
        )
        self.assertEqual(str(unequip_action), "Unequip item from head")
        
        # Test string representation of state
        state_str = str(self.state)
        self.assertIn("Equipment for char_123", state_str)
        self.assertIn("2/7 slots filled", state_str)
        
if __name__ == "__main__":
    unittest.main()