# workers/item_worker.py
from app.workers.celery_app import app
from database.connection import SessionLocal, get_db
import logging
from typing import Dict, List, Optional, Any

# Import the service that contains the actual implementation
from app.game_state.services.item_service import ItemService
from app.game_state.managers.item_manager import ItemManager
from app.game_state.managers.player_manager import PlayerManager
from app.game_state.managers.world_manager import WorldManager

logger = logging.getLogger(__name__)

def get_services():
    """Get the services needed for item operations"""
    item_manager = ItemManager()
    player_manager = PlayerManager()
    world_manager = WorldManager()
    return ItemService(item_manager, player_manager, world_manager)

@app.task
def process_item_durability(item_id: str):
    """
    Process durability for an item.
    
    Args:
        item_id (str): The ID of the item to process
    """
    logger.info(f"Processing durability for item {item_id}")
    
    try:
        service = get_services()
        result = service.process_item_durability(item_id)
        
        if result["status"] == "success":
            logger.info(f"Successfully processed durability for item {item_id}")
        else:
            logger.warning(f"Failed to process durability for item {item_id}: {result.get('message', 'Unknown error')}")
        
        return result
    except Exception as e:
        logger.exception(f"Error in process_item_durability task: {e}")
        return {"status": "error", "message": f"Task error: {str(e)}"}

@app.task
def change_item_owner(item_id: str, new_owner_id: str):
    """
    Change the owner of an item.
    
    Args:
        item_id (str): The ID of the item
        new_owner_id (str): The ID of the new owner
    """
    logger.info(f"Changing owner of item {item_id} to {new_owner_id}")
    
    try:
        service = get_services()
        result = service.change_item_owner(item_id, new_owner_id)
        
        if result["status"] == "success":
            logger.info(f"Successfully changed owner of item {item_id} to {new_owner_id}")
        else:
            logger.warning(f"Failed to change owner of item {item_id}: {result.get('message', 'Unknown error')}")
        
        return result
    except Exception as e:
        logger.exception(f"Error in change_item_owner task: {e}")
        return {"status": "error", "message": f"Task error: {str(e)}"}

@app.task
def create_item(item_data: Dict[str, Any]):
    """
    Create a new item.
    
    Args:
        item_data (Dict[str, Any]): Data for the new item
    """
    logger.info(f"Creating new item with data: {item_data}")
    
    try:
        service = get_services()
        result = service.create_item(item_data)
        
        if result["status"] == "success":
            logger.info(f"Successfully created item {result.get('item_id')}")
        else:
            logger.warning(f"Failed to create item: {result.get('message', 'Unknown error')}")
        
        return result
    except Exception as e:
        logger.exception(f"Error in create_item task: {e}")
        return {"status": "error", "message": f"Task error: {str(e)}"}

@app.task
def delete_item(item_id: str):
    """
    Delete an item.
    
    Args:
        item_id (str): The ID of the item to delete
    """
    logger.info(f"Deleting item {item_id}")
    
    try:
        service = get_services()
        result = service.delete_item(item_id)
        
        if result["status"] == "success":
            logger.info(f"Successfully deleted item {item_id}")
        else:
            logger.warning(f"Failed to delete item {item_id}: {result.get('message', 'Unknown error')}")
        
        return result
    except Exception as e:
        logger.exception(f"Error in delete_item task: {e}")
        return {"status": "error", "message": f"Task error: {str(e)}"}

@app.task
def break_item(item_id: str):
    """
    Break an item, rendering it unusable.
    
    Args:
        item_id (str): The ID of the item to break
    """
    logger.info(f"Breaking item {item_id}")
    
    try:
        service = get_services()
        result = service.break_item(item_id)
        
        if result["status"] == "success":
            logger.info(f"Successfully broke item {item_id}")
        else:
            logger.warning(f"Failed to break item {item_id}: {result.get('message', 'Unknown error')}")
        
        return result
    except Exception as e:
        logger.exception(f"Error in break_item task: {e}")
        return {"status": "error", "message": f"Task error: {str(e)}"}

@app.task
def repair_item(player_id: str, item_id: str):
    """
    Repair a damaged item.
    
    Args:
        player_id (str): The ID of the player repairing the item
        item_id (str): The ID of the item to repair
    """
    logger.info(f"Repairing item {item_id} for player {player_id}")
    
    try:
        service = get_services()
        result = service.repair_item(player_id, item_id)
        
        if result["status"] == "success":
            logger.info(f"Successfully repaired item {item_id}")
        else:
            logger.warning(f"Failed to repair item {item_id}: {result.get('message', 'Unknown error')}")
        
        return result
    except Exception as e:
        logger.exception(f"Error in repair_item task: {e}")
        return {"status": "error", "message": f"Task error: {str(e)}"}

@app.task
def equip_item(player_id: str, item_id: str):
    """
    Equip an item on a player.
    
    Args:
        player_id (str): The ID of the player
        item_id (str): The ID of the item to equip
    """
    logger.info(f"Equipping item {item_id} on player {player_id}")
    
    try:
        service = get_services()
        result = service.equip_item(player_id, item_id)
        
        if result["status"] == "success":
            logger.info(f"Successfully equipped item {item_id} on player {player_id}")
        else:
            logger.warning(f"Failed to equip item {item_id}: {result.get('message', 'Unknown error')}")
        
        return result
    except Exception as e:
        logger.exception(f"Error in equip_item task: {e}")
        return {"status": "error", "message": f"Task error: {str(e)}"}

@app.task
def unequip_item(player_id: str, slot: str):
    """
    Unequip an item from a player.
    
    Args:
        player_id (str): The ID of the player
        slot (str): The equipment slot to unequip
    """
    logger.info(f"Unequipping item from slot {slot} on player {player_id}")
    
    try:
        service = get_services()
        result = service.unequip_item(player_id, slot)
        
        if result["status"] == "success":
            logger.info(f"Successfully unequipped item from slot {slot} on player {player_id}")
        else:
            logger.warning(f"Failed to unequip item: {result.get('message', 'Unknown error')}")
        
        return result
    except Exception as e:
        logger.exception(f"Error in unequip_item task: {e}")
        return {"status": "error", "message": f"Task error: {str(e)}"}

@app.task
def initialize_world_equipment(count: int = 10):
    """
    Initialize the world with random equipment.
    
    Args:
        count (int): Number of equipment items to create
    """
    logger.info(f"Initializing world with {count} random equipment items")
    
    try:
        service = get_services()
        result = service.initialize_world_equipment(count)
        
        if result["status"] == "success":
            logger.info(f"Successfully initialized world equipment: {result.get('message', '')}")
        else:
            logger.warning(f"Failed to initialize world equipment: {result.get('message', 'Unknown error')}")
        
        return result
    except Exception as e:
        logger.exception(f"Error in initialize_world_equipment task: {e}")
        return {"status": "error", "message": f"Task error: {str(e)}"}