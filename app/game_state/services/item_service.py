# app/game_state/services/service_template.py
from sqlalchemy.orm import Session
import logging
from typing import Dict, List, Optional, Any

# Import managers, entities, and other components as needed
from app.game_state.managers.item_manager import ItemManager
from app.game_state.decision_makers.item_decision_maker import ItemDecisionMaker
from app.ai.mcts.states.item_state import ItemState
from app.models.item import Item

from database.connection import SessionLocal, get_db

logger = logging.getLogger(__name__)

class ItemService:
    """
    Service layer template that bridges between Celery tasks and game state components.
    This template provides a starting point for creating new services that orchestrate
    operations between different components of the game_state architecture.
    
    Copy this template and customize it for each specific domain (settlements, factions, etc.).

    ---

    ###  Item Service**
    - **Purpose**: Orchestrates high-level operations and interactions between components (e.g., managers, states, decision-makers).
    - **When to use**:
    - If the functionality spans multiple components (e.g., managers, states, or entities).
    - If the functionality involves **business logic** that coordinates multiple systems (e.g., resolving encounters, processing migrations).
    - If the functionality is **task-oriented** and invoked by external systems (e.g., Celery tasks, API endpoints).
    - **Examples**:
    - Processing all items in the world.
    - Orchestrating item durability.
    - Handling encounters or interactions between items.
    """
    def __init__(self, db, player_manager=None, world_manager=None, item_data=None):
        """
        Initialize the service with a database session.
        
        Args:
            db: Database session.
            player_manager: Manager for player-related operations.
            world_manager: Manager for world-related operations.
            item_data: Data required to initialize ItemState.
        """
        self.db = db
        self.item_manager = ItemManager(db)
        self.player_manager = player_manager
        self.world_manager = world_manager
        self.decision_maker = ItemDecisionMaker(SessionLocal)
        self.state = ItemState(item_data=item_data or {})
    
    def _load_item_or_error(self, item_id: str) -> Optional[Item]:
        item = self.item_manager.load_item(item_id)
        if not item:
            logger.warning(f"Item not found: {item_id}")
            return None
        return item

    def process_item_durability(self, item_id: str) -> Dict[str, Any]:
        """
        Process the durability of a specific item.
        
        Args:
            item_id (str): The ID of the item to process
        """
        logger.info(f"Processing durability for item {item_id}")
        
        try:
            # Load the item
            item = self._load_item_or_error(item_id)
            if not item:
                return {"status": "error", "message": "Item not found"}
            
            # Process durability
            result = self.item_manager.process_item_durability(item)
            return result
        
        except Exception as e:
            logger.exception(f"Error processing item durability: {e}")
            return {"status": "error", "message": f"Error: {str(e)}"}

    def change_item_owner(self, item_id: str, new_owner_id: str) -> Dict[str, Any]:
        """
        Change the owner of an item to a new owner.
        
        Args:
            item_id (str): The ID of the item to transfer
            new_owner_id (str): The ID of the new owner
        """
        logger.info(f"Changing owner of item {item_id} to {new_owner_id}")
        
        def item_and_owner_exists(item_id: str, owner_id: str) -> bool:
            item = self.item_manager.load_item(item_id)
            owner = self.item_manager.load_owner(owner_id)
            return item is None or owner is None

        try:

            if(item_and_owner_exists(item_id, new_owner_id)):
                return {"status": "error", "message": "Item or owner not found"}
            # Load the item
            item = self._load_item_or_error(item_id)
            if not item:
                return {"status": "error", "message": "Item not found"}
            

            # Change the owner
            result = self.item_manager.change_item_owner(item, new_owner_id)
            return result
        
        except Exception as e:
            logger.exception(f"Error changing item owner: {e}")
            return {"status": "error", "message": f"Error: {str(e)}"}

    def initialize_world_equipment(self, count: int = 10) -> Dict[str, Any]:
        """
        Initialize the world with a specified number of random equipment items.

        Args:
            count (int): Number of equipment items to create.

        Returns:
            Dict[str, Any]: Summary of the initialization process.
        """
        logger.info(f"Initializing world with {count} random equipment items")
        
        try:
            equipment_list = self.item_manager.generate_random_equipment(count)
            return {
                "status": "success",
                "message": f"Initialized {len(equipment_list)} equipment items",
                "equipment_ids": [equipment.equipment_id for equipment in equipment_list]
            }
        
        except Exception as e:
            logger.exception("Error initializing world equipment")
            return {"status": "error", "message": f"Error: {str(e)}"}
        
    def create_item(self, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new item with the given data.
        
        Args:
            item_data (Dict[str, Any]): Data for the new item
        
        Returns:
            Dict[str, Any]: Result of the create operation
        """
        logger.info(f"Creating new item: {item_data}")
        
        try:
            item = self.item_manager.create_item(item_data)
            if item:
                return {"status": "success", "message": "Item created", "item_id": item.item_id}
            else:
                return {"status": "error", "message": "Failed to create item"}
        
        except Exception as e:
            logger.exception("Error creating item")
            return {"status": "error", "message": f"Error: {str(e)}"}

    def delete_item(self, item_id: str) -> Dict[str, Any]:
        """
        Delete an item by its ID.
        
        Args:
            item_id (str): The ID of the item to delete
        
        Returns:
            Dict[str, Any]: Result of the delete operation
        """
        logger.info(f"Deleting item: {item_id}")
        
        try:
            result = self.item_manager.delete_item(item_id)
            if result:
                return {"status": "success", "message": "Item deleted"}
            else:
                return {"status": "error", "message": "Failed to delete item"}
        
        except Exception as e:
            logger.exception("Error deleting item")
            return {"status": "error", "message": f"Error: {str(e)}"}

    def break_item(self, item_id: str) -> Dict[str, Any]:
        """
        Break an item, rendering it unusable.
        
        Args:
            item_id (str): The ID of the item to break
        
        Returns:
            Dict[str, Any]: Result of the break operation
        """
        logger.info(f"Breaking item: {item_id}")
        
        try:
            item = self._load_item_or_error(item_id)
            if not item:
                return {"status": "error", "message": "Item not found"}
            
            state = ItemState(item)
            if item.is_broken():
                return {"status": "error", "message": "Item is already broken"}
            
            state.apply_action({"type": "repair"})
            self.item_manager.save_entity(item)
            return {"status": "success", "message": "Item broken"}
        
        except Exception as e:
            logger.exception("Error breaking item")
            return {"status": "error", "message": f"Error: {str(e)}"}

    def steal_item(self, item_id: str, thief_id: str) -> Dict[str, Any]:
        """
        Steal an item from its current owner.
        
        Args:
            item_id (str): The ID of the item to steal
            thief_id (str): The ID of the thief
        
        Returns:
            Dict[str, Any]: Result of the steal operation
        """
        logger.info(f"Stealing item {item_id} by thief {thief_id}")
        
        try:
            result = self.item_manager.steal_item(item_id, thief_id)
            return result
        
        except Exception as e:
            logger.exception("Error stealing item")
            return {"status": "error", "message": f"Error: {str(e)}"}
        
    def attempt_to_steal_item(self, item_id: str, thief_id: str) -> Dict[str, Any]:
        """
        Attempt to steal an item from its current owner.
        
        Args:
            item_id (str): The ID of the item to steal
            thief_id (str): The ID of the thief
        
        Returns:
            Dict[str, Any]: Result of the steal attempt
        """
        logger.info(f"Attempting to steal item {item_id} by thief {thief_id}")
        
        try:
            result = self.item_manager.attempt_to_steal_item(item_id, thief_id)
            return result
        
        except Exception as e:
            logger.exception("Error attempting to steal item")
            return {"status": "error", "message": f"Error: {str(e)}"}

    # Core item operations
    def get_item(self, item_id):
        """Retrieve item details by ID"""
        return self.item_manager.get_item(item_id)
    
    def get_items_by_type(self, item_type, rarity=None, level_range=None):
        """Get filtered items by type, optional rarity and level range"""
        return self.item_manager.get_items_by_filters(item_type, rarity, level_range)
    
    # Inventory operations
    def add_to_inventory(self, player_id, item_id, quantity=1):
        """Add item to player inventory"""
        player = self.player_manager.get_player(player_id)
        item = self.item_manager.get_item(item_id)
        return self.player_manager.add_item_to_inventory(player, item, quantity)
    
    def remove_from_inventory(self, player_id, item_id, quantity=1):
        """Remove item from player inventory"""
        player = self.player_manager.get_player(player_id)
        return self.player_manager.remove_item_from_inventory(player, item_id, quantity)
    
    def transfer_item(self, source_id, target_id, item_id, quantity=1):
        """Transfer item between players or containers"""
        source = self.player_manager.get_player(source_id)
        target = self.player_manager.get_player(target_id)
        return self.player_manager.transfer_item(source, target, item_id, quantity)
    
    # Equipment management
    def equip_item(self, player_id, item_id):
        """Equip item on player"""
        player = self.player_manager.get_player(player_id)
        item = self.item_manager.get_item(item_id)
        return self.player_manager.equip_item(player, item)
    
    def unequip_item(self, player_id, slot):
        """Unequip item from specific slot"""
        player = self.player_manager.get_player(player_id)
        return self.player_manager.unequip_item(player, slot)
    
    # Item interactions
    def use_item(self, player_id, item_id, target_id=None):
        """Use consumable or usable item, optionally on target"""
        player = self.player_manager.get_player(player_id)
        item = self.item_manager.get_item(item_id)
        target = None if target_id is None else self.player_manager.get_player(target_id)
        return self.item_manager.use_item(player, item, target)
    
    def craft_item(self, player_id, recipe_id):
        """Craft item using recipe and ingredients from inventory"""
        player = self.player_manager.get_player(player_id)
        recipe = self.item_manager.get_recipe(recipe_id)
        return self.item_manager.craft_item(player, recipe)
    
    # Item modifications
    def enhance_item(self, player_id, item_id, enhancement_id):
        """Enhance/upgrade an item using materials"""
        player = self.player_manager.get_player(player_id)
        item = self.item_manager.get_item(item_id)
        enhancement = self.item_manager.get_enhancement(enhancement_id)
        return self.item_manager.enhance_item(player, item, enhancement)
    
    def repair_item(self, player_id, item_id):
        """Repair damaged item"""
        player = self.player_manager.get_player(player_id)
        item = self.item_manager.get_item(item_id)
        return self.item_manager.repair_item(player, item)
    
    # World interaction
    def drop_item(self, player_id, item_id, quantity=1, location=None):
        """Drop item to world at optional location or player's location"""
        player = self.player_manager.get_player(player_id)
        item = self.item_manager.get_item(item_id)
        location = location or player.location
        return self.world_manager.spawn_item(item, quantity, location)
    
    def pickup_item(self, player_id, world_item_id):
        """Pick up item from world"""
        player = self.player_manager.get_player(player_id)
        world_item = self.world_manager.get_world_item(world_item_id)
        result = self.player_manager.add_item_to_inventory(player, world_item.item, world_item.quantity)
        if result:
            self.world_manager.remove_world_item(world_item_id)
        return result
    
    # Economy operations
    def sell_item(self, player_id, item_id, quantity=1, vendor_id=None):
        """Sell item to vendor or marketplace"""
        player = self.player_manager.get_player(player_id)
        item = self.item_manager.get_item(item_id)
        return self.item_manager.sell_item(player, item, quantity, vendor_id)
    
    def buy_item(self, player_id, item_id, quantity=1, vendor_id=None):
        """Buy item from vendor or marketplace"""
        player = self.player_manager.get_player(player_id)
        item = self.item_manager.get_item(item_id)
        return self.item_manager.buy_item(player, item, quantity, vendor_id)
    
    # Item discovery/generation
    def generate_loot(self, enemy_type, enemy_level, rarity_modifier=0):
        """Generate random loot based on enemy type and level"""
        return self.item_manager.generate_loot(enemy_type, enemy_level, rarity_modifier)
    
    def generate_treasure(self, chest_tier, area_level):
        """Generate treasure items for chests based on tier and area level"""
        return self.item_manager.generate_treasure(chest_tier, area_level)
        
    def process_all_items(self, world_id: str = None) -> Dict[str, Any]:
        """Process all items in the world, handling durability, effects, etc.
        
        Args:
            world_id: Optional world ID to filter by
            
        Returns:
            Dict with processing results
        """
        logger.info(f"Processing all items" + (f" in world {world_id}" if world_id else ""))
        
        try:
            # Logic for processing all items would go here
            # For now, return a placeholder success message
            return {
                "status": "success",
                "message": "All items processed",
                "processed": 0,
                "results": []
            }
            
        except Exception as e:
            logger.exception(f"Error processing all items: {e}")
            return {
                "status": "error",
                "message": str(e)
            }