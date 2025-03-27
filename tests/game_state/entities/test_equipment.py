import unittest
from app.game_state.entities.equipment import Equipment
from app.game_state.entities.item import Item

class TestEquipment(unittest.TestCase):
    def setUp(self):
        # Create a test equipment
        self.character_id = "test_character_123"
        self.equipment = Equipment(character_id=self.character_id)
        
        # Create test items
        self.sword = Item("sword_123")
        self.sword.name = "Test Sword"
        self.sword.is_equippable = True
        
        self.helmet = Item("helmet_123")
        self.helmet.name = "Test Helmet"
        self.helmet.is_equippable = True
        
        self.potion = Item("potion_123")
        self.potion.name = "Test Potion"
        self.potion.is_equippable = False
    
    def test_equip_item(self):
        # Test equipping a valid item to a valid slot
        result = self.equipment.equip_item("weapon", self.sword)
        self.assertTrue(result)
        self.assertEqual(self.equipment.slots["weapon"], self.sword.item_id)
        
        # Test equipping to the head slot
        result = self.equipment.equip_item("head", self.helmet)
        self.assertTrue(result)
        self.assertEqual(self.equipment.slots["head"], self.helmet.item_id)
    
    def test_equip_non_equippable_item(self):
        # Test equipping an item that can't be equipped
        result = self.equipment.equip_item("weapon", self.potion)
        self.assertFalse(result)
        self.assertIsNone(self.equipment.slots["weapon"])
    
    def test_equip_invalid_slot(self):
        # Test equipping to an invalid slot
        result = self.equipment.equip_item("invalid_slot", self.sword)
        self.assertFalse(result)
    
    def test_unequip_item(self):
        # Equip an item first
        self.equipment.equip_item("weapon", self.sword)
        
        # Test unequipping it
        item_id = self.equipment.unequip_item("weapon")
        self.assertEqual(item_id, self.sword.item_id)
        self.assertIsNone(self.equipment.slots["weapon"])
    
    def test_unequip_empty_slot(self):
        # Test unequipping an empty slot
        item_id = self.equipment.unequip_item("weapon")
        self.assertIsNone(item_id)
    
    def test_unequip_invalid_slot(self):
        # Test unequipping an invalid slot
        item_id = self.equipment.unequip_item("invalid_slot")
        self.assertIsNone(item_id)
    
    def test_is_slot_equipped(self):
        # Test empty slot
        self.assertFalse(self.equipment.is_slot_equipped("weapon"))
        
        # Equip an item
        self.equipment.equip_item("weapon", self.sword)
        
        # Test equipped slot
        self.assertTrue(self.equipment.is_slot_equipped("weapon"))
        
        # Test invalid slot
        self.assertFalse(self.equipment.is_slot_equipped("invalid_slot"))
    
    def test_get_equipped_item_ids(self):
        # Initially no equipped items
        equipped_items = self.equipment.get_equipped_item_ids()
        self.assertEqual(equipped_items, {})
        
        # Equip two items
        self.equipment.equip_item("weapon", self.sword)
        self.equipment.equip_item("head", self.helmet)
        
        # Test get_equipped_item_ids
        equipped_items = self.equipment.get_equipped_item_ids()
        self.assertEqual(len(equipped_items), 2)
        self.assertEqual(equipped_items["weapon"], self.sword.item_id)
        self.assertEqual(equipped_items["head"], self.helmet.item_id)
    
    def test_serialization(self):
        # Equip items
        self.equipment.equip_item("weapon", self.sword)
        self.equipment.equip_item("head", self.helmet)
        
        # Test to_dict
        data = self.equipment.to_dict()
        self.assertEqual(data["character_id"], self.character_id)
        self.assertEqual(data["equipment_id"], f"eq_{self.character_id}")
        self.assertEqual(data["slots"]["weapon"], self.sword.item_id)
        self.assertEqual(data["slots"]["head"], self.helmet.item_id)
        
        # Test from_dict
        new_equipment = Equipment.from_dict(data)
        self.assertEqual(new_equipment.character_id, self.character_id)
        self.assertEqual(new_equipment.equipment_id, f"eq_{self.character_id}")
        self.assertEqual(new_equipment.slots["weapon"], self.sword.item_id)
        self.assertEqual(new_equipment.slots["head"], self.helmet.item_id)

if __name__ == "__main__":
    unittest.main()