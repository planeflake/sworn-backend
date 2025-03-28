from typing import List, Dict, Optional, Any, Type, Union
from sqlalchemy.orm import Session
from database.connection import get_db
from app.models.item import Item
import logging
import uuid
import json

logger = logging.getLogger(__name__)

EntityType = Item

class ItemManager:
    """
    Template for entity managers that handle persistence and lifecycle.
    
    Managers are responsible for:
    1. Loading entities from the database
    2. Saving entities to the database
    3. Creating new entities
    4. Maintaining a cache of loaded entities
    5. Providing query methods for finding entities
    
    Each entity type should have its own manager class.
    """
    
    def __init__(self, db=None):
        """
        Initialize the manager.
        
        Args:
            db: Database session (optional)
        """
        # Cache of loaded entities
        self.entities = {}  # Dictionary to store loaded entities by ID
        self.db = db
        
        logger.info(f"{self.__class__.__name__} initialized")
    
    ### Basic Query methods ###

    def create_entity(self, name: str, description: Optional[str] = None) -> Item:
        """
        Create a new item entity with a unique ID.
        
        Args:
            name (str): The item's name
            description (str, optional): Optional description
            
        Returns:
            Item: The newly created item
        """
        # Create a new item instance
        item = Item(
            name=name,
            description=description or f"An item named {name}",
        )
        
        # Save to database
        self.save_entity(item)
        
        logger.info(f"Created new item: {name} (ID: {item.item_id})")
        return item
    
    def save_entity(self, entity: Item) -> None:
        """
        Save an item entity to the database.
        
        Args:
            entity (Item): The item entity to save
        """
        db = get_db()
        with Session(db) as session:
            session.add(entity)
            session.commit()
            logger.info(f"Saved item to database: {entity.name} (ID: {entity.item_id})")
    
    def load_entity(self, entity_id: str) -> Optional[Item]:
        """
        Load an item from the database.
        
        Args:
            entity_id (str): The ID of the item to load
            
        Returns:
            Item: The loaded item, or None if not found
        """
        db = get_db()
        with Session(db) as session:
            item = session.query(Item).filter(Item.item_id == entity_id).first()
            if not item:
                logger.warning(f"Item not found: {entity_id}")
                return None
            # Cache the loaded entity
            self.entities[entity_id] = item
            return item
    
    def delete_entity(self, entity_id: str) -> None:
        """
        Delete an item from the database.
        
        Args:
            entity_id (str): The ID of the item to delete
        """
        db = get_db()
        with Session(db) as session:
            item = session.query(Item).filter(Item.item_id == entity_id).first()
            if item:
                session.delete(item)
                session.commit()
                logger.info(f"Deleted item from database: {entity_id}")
                # Remove from cache
                self.entities.pop(entity_id, None)
            else:
                logger.warning(f"Attempted to delete non-existent item: {entity_id}")

    ### Advanced Query methods ###

    def find_items_by_name(self, name: str) -> List[Item]:
        """
        Find items by name.
        
        Args:
            name (str): The name to search for
            
        Returns:
            List[Item]: A list of items with the given name
        """
        db = get_db()
        with Session(db) as session:
            items = session.query(Item).filter(Item.name == name).all()
            return items
        
    def find_items_by_type(self, item_type: str) -> List[Item]:
        """
        Find items by type.
        
        Args:
            item_type (str): The type to search for
            
        Returns:
            List[Item]: A list of items with the given type
        """
        db = get_db()
        with Session(db) as session:
            items = session.query(Item).filter(Item.item_type == item_type).all()
            return items
        
    def find_items_by_property(self, key: str, value: Any) -> List[Item]:
        """
        Find items by property.
        
        Args:
            key (str): The property key to search
            value (Any): The property value to match"
            """
        db = get_db()
        with Session(db) as session:
            items = session.query(Item).filter(Item.properties[key] == value).all()
            return items
    
    def find_items_by_location(self, location_id: str) -> List[Item]:
        """
        Find items by location.
        
        Args:
            location_id (str): The ID of the location to search
            
        Returns:
            List[Item]: A list of items at the given location
        """
        db = get_db()
        with Session(db) as session:
            items = session.query(Item).filter(Item.location_id == location_id).all()
            return items

    ### Update Methods ###

    def update_entity(self, entity_id: str, **kwargs) -> Optional[Item]:
        """
        Update an item's attributes.
        
        Args:
            entity_id (str): The ID of the item to update
            **kwargs: Key-value pairs of attributes to update
            
        Returns:
            Item: The updated item, or None if not found
        """
        db = get_db()
        with Session(db) as session:
            item = session.query(Item).filter(Item.item_id == entity_id).first()
            if not item:
                logger.warning(f"Item not found for update: {entity_id}")
                return None
            
            for key, value in kwargs.items():
                if hasattr(item, key):
                    setattr(item, key, value)
                else:
                    logger.warning(f"Invalid attribute '{key}' for item update")
            
            session.commit()
            logger.info(f"Updated item: {entity_id}")
            # Update cache
            self.entities[entity_id] = item
            return item

    ### Bulk Operations ###

    def load_entities(self, entity_ids: List[str]) -> List[Item]:
        """
        Load multiple items from the database.
        
        Args:
            entity_ids (List[str]): A list of item IDs to load
            
        Returns:
            List[Item]: A list of loaded items
        """
        db = get_db()
        with Session(db) as session:
            items = session.query(Item).filter(Item.item_id.in_(entity_ids)).all()
            for item in items:
                self.entities[item.item_id] = item
            return items

    ### Cache Management ###

    def clear_cache(self) -> None:
        """
        Clear the cache of loaded entities.
        """
        self.entities.clear()
        logger.info("Cache cleared")

    def refresh_cache(self, entity_id: str) -> Optional[Item]:
        """
        Refresh a specific item in the cache.
        
        Args:
            entity_id (str): The ID of the item to refresh
            
        Returns:
            Item: The refreshed item, or None if not found
        """
        item = self.load_entity(entity_id)
        if item:
            self.entities[entity_id] = item
        return item

    ### Pagination ###

    def find_items_paginated(self, page: int, page_size: int) -> List[Item]:
        """
        Retrieve items with pagination.
        
        Args:
            page (int): The page number (1-based index)
            page_size (int): The number of items per page
            
        Returns:
            List[Item]: A list of items for the given page
        """
        db = get_db()
        with Session(db) as session:
            items = session.query(Item).offset((page - 1) * page_size).limit(page_size).all()
            return items

    ### Soft Delete ###

    def soft_delete_entity(self, entity_id: str) -> None:
        """
        Soft delete an item by marking it as inactive.
        
        Args:
            entity_id (str): The ID of the item to soft delete
        """
        db = get_db()
        with Session(db) as session:
            item = session.query(Item).filter(Item.item_id == entity_id).first()
            if item:
                item.is_active = False
                session.commit()
                logger.info(f"Soft deleted item: {entity_id}")
                self.entities.pop(entity_id, None)
            else:
                logger.warning(f"Attempted to soft delete non-existent item: {entity_id}")

    ### Export/Import ###

    def export_items(self, file_path: str) -> None:
        """
        Export all items to a JSON file.
        
        Args:
            file_path (str): The file path to save the items
        """
        with open(file_path, 'w') as file:
            json.dump([item.to_dict() for item in self.entities.values()], file)
        logger.info(f"Exported items to {file_path}")

    def import_items(self, file_path: str) -> None:
        """
        Import items from a JSON file.
        
        Args:
            file_path (str): The file path to load the items from
        """
        with open(file_path, 'r') as file:
            items = json.load(file)
            for item_data in items:
                item = Item.from_dict(item_data)
                self.save_entity(item)
        logger.info(f"Imported items from {file_path}")

    ### Audit Logging ###

    def log_item_changes(self, entity_id: str, changes: Dict[str, Any]) -> None:
        """
        Log changes made to an item.
        
        Args:
            entity_id (str): The ID of the item
            changes (Dict[str, Any]): A dictionary of changes
        """
        logger.info(f"Changes to item {entity_id}: {changes}")