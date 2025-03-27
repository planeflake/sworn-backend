from typing import Dict, Optional, List, Any
from app.game_state.managers.equipment_manager import EquipmentManager
from app.game_state.managers.item_manager import ItemManager
from app.game_state.entities.equipment import Equipment
from sqlalchemy.orm import Session
from database.connection import get_db
import logging

logger = logging.getLogger(__name__)

class EquipmentService:
    """
    Service for managing character equipment operations.
    
    This service focuses exclusively on equipment operations:
    - Equipping/unequipping items
    - Getting equipped items for a character
    - Checking equipment status
    """
    
    def __init__(self, db_session=None):
        """
        Initialize the service with required managers.
        
        Args:
            db_session (Session, optional): Database session to use.
                                          If not provided, a new one will be created.
        """
        self.db = db_session
        self.equipment_manager = EquipmentManager(db_session)
        self.item_manager = ItemManager(db_session)
        logger.info("EquipmentService initialized")
    
    def get_character_equipment(self, character_id: str) -> Dict[str, Any]:
        """
        Get a character's equipment loadout, creating it if it doesn't exist.
        
        Args:
            character_id (str): The character ID
            
        Returns:
            Dict[str, Any]: Result containing equipment data or error message
        """
        logger.info(f"Getting equipment for character {character_id}")
        
        try:
            equipment_id = f"eq_{character_id}" 
            equipment = self.equipment_manager.load_entity(equipment_id)
            
            if not equipment:
                # Create new equipment loadout for character
                equipment = Equipment(character_id)
                self.equipment_manager.save_entity(equipment)
                logger.info(f"Created new equipment for character {character_id}")
                
            # Get equipped items
            equipped_items = self.get_equipped_items(character_id)
            
            return {
                "status": "success",
                "character_id": character_id,
                "equipment_id": equipment.equipment_id,
                "equipped_items": equipped_items
            }
            
        except Exception as e:
            logger.exception(f"Error getting equipment for character {character_id}: {e}")
            return {
                "status": "error",
                "character_id": character_id,
                "message": f"Error: {str(e)}"
            }
        
    def equip_item(self, character_id: str, item_id: str, slot: str) -> Dict[str, Any]:
        """
        Equip an item in a character's equipment slot.
        
        Args:
            character_id (str): The character ID
            item_id (str): The item ID to equip
            slot (str): The slot to equip the item in
            
        Returns:
            Dict[str, Any]: Result of the equip operation
        """
        logger.info(f"Equipping item {item_id} to slot {slot} for character {character_id}")
        
        try:
            # Get equipment for character
            equipment_result = self.get_character_equipment(character_id)
            if equipment_result["status"] == "error":
                return equipment_result
                
            equipment_id = equipment_result["equipment_id"]
            equipment = self.equipment_manager.load_entity(equipment_id)
            
            # Get item
            item = self.item_manager.load_entity(item_id)
            if not item:
                logger.warning(f"Item not found: {item_id}")
                return {
                    "status": "error",
                    "character_id": character_id,
                    "item_id": item_id,
                    "message": f"Item not found: {item_id}"
                }
                
            # Equip item
            success = equipment.equip_item(slot, item)
            if not success:
                return {
                    "status": "error",
                    "character_id": character_id,
                    "item_id": item_id,
                    "slot": slot,
                    "message": f"Failed to equip item {item_id} to slot {slot}"
                }
                
            # Save equipment
            self.equipment_manager.save_entity(equipment)
            
            return {
                "status": "success",
                "character_id": character_id,
                "equipment_id": equipment.equipment_id,
                "item_id": item_id,
                "slot": slot,
                "message": f"Item {item.name} equipped to slot {slot}"
            }
            
        except Exception as e:
            logger.exception(f"Error equipping item {item_id} to slot {slot} for character {character_id}: {e}")
            return {
                "status": "error",
                "character_id": character_id,
                "item_id": item_id,
                "slot": slot,
                "message": f"Error: {str(e)}"
            }
        
    def unequip_item(self, character_id: str, slot: str) -> Dict[str, Any]:
        """
        Unequip an item from a character's equipment slot.
        
        Args:
            character_id (str): The character ID
            slot (str): The slot to unequip
            
        Returns:
            Dict[str, Any]: Result of the unequip operation
        """
        logger.info(f"Unequipping item from slot {slot} for character {character_id}")
        
        try:
            # Get equipment for character
            equipment_result = self.get_character_equipment(character_id)
            if equipment_result["status"] == "error":
                return equipment_result
                
            equipment_id = equipment_result["equipment_id"]
            equipment = self.equipment_manager.load_entity(equipment_id)
            
            # Unequip item
            item_id = equipment.unequip_item(slot)
            if not item_id:
                return {
                    "status": "error",
                    "character_id": character_id,
                    "slot": slot,
                    "message": f"No item equipped in slot {slot}"
                }
                
            # Save equipment
            self.equipment_manager.save_entity(equipment)
            
            # Get item details
            item = self.item_manager.load_entity(item_id)
            item_name = item.name if item else "Unknown Item"
            
            return {
                "status": "success",
                "character_id": character_id,
                "equipment_id": equipment.equipment_id,
                "item_id": item_id,
                "item_name": item_name,
                "slot": slot,
                "message": f"Item {item_name} unequipped from slot {slot}"
            }
            
        except Exception as e:
            logger.exception(f"Error unequipping item from slot {slot} for character {character_id}: {e}")
            return {
                "status": "error",
                "character_id": character_id,
                "slot": slot,
                "message": f"Error: {str(e)}"
            }
        
    def get_equipped_items(self, character_id: str) -> Dict[str, Dict]:
        """
        Get all equipped items for a character with details.
        
        Args:
            character_id (str): The character ID
            
        Returns:
            Dict[str, Dict]: Dictionary mapping slots to item details
        """
        equipment_id = f"eq_{character_id}" 
        equipment = self.equipment_manager.load_entity(equipment_id)
        
        if not equipment:
            return {}
            
        equipped_item_ids = equipment.get_equipped_item_ids()
        
        result = {}
        for slot, item_id in equipped_item_ids.items():
            item = self.item_manager.load_entity(item_id)
            if item:
                result[slot] = item.to_dict()
                
        return result
        
    def inspect_item(self, item_id: str) -> Dict[str, Any]:
        """
        Inspect an item to view its details.
        
        Args:
            item_id (str): The ID of the item to inspect
            
        Returns:
            Dict[str, Any]: Item details
        """
        logger.info(f"Inspecting item {item_id}")
        
        try:
            # Load the item
            item = self.item_manager.load_entity(item_id)
            
            if not item:
                return {
                    "status": "error",
                    "item_id": item_id,
                    "message": f"Item not found: {item_id}"
                }
                
            return {
                "status": "success",
                "item_id": item_id,
                "item": item.to_dict()
            }
            
        except Exception as e:
            logger.exception(f"Error inspecting item {item_id}: {e}")
            return {
                "status": "error",
                "item_id": item_id,
                "message": f"Error: {str(e)}"
            }