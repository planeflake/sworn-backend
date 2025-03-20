from typing import List, Dict, Optional, Any, Type, Union
from sqlalchemy.orm import Session
from database.connection import get_db
from models.equipment import Equipment  # Assuming you have an Equipment model
import logging
import uuid
import json

logger = logging.getLogger(__name__)

EntityType = Equipment

class EquipmentManager:
    """
    Manager class that handles persistence and lifecycle of Equipment entities.
    
    Managers are responsible for:
    1. Loading entities from the database
    2. Saving entities to the database
    3. Creating new entities
    4. Maintaining a cache of loaded entities
    5. Providing query methods for finding entities
    """
    
    def __init__(self):
        """Initialize the manager."""
        # Cache of loaded entities
        self.entities = {}  # Dictionary to store loaded entities by ID
        
        logger.info(f"{self.__class__.__name__} initialized")
    
    ### Basic Query methods ###

    def create_entity(self, name: str, description: Optional[str] = None) -> Equipment:
        """
        Create a new equipment entity with a unique ID.
        
        Args:
            name (str): The equipment's name
            description (str, optional): Optional description
            
        Returns:
            Equipment: The newly created equipment
        """
        # Create a new equipment instance
        equipment = Equipment(
            name=name,
            description=description or f"An equipment named {name}",
        )
        
        # Save to database
        self.save_entity(equipment)
        
        logger.info(f"Created new equipment: {name} (ID: {equipment.equipment_id})")
        return equipment
    
    def save_entity(self, entity: Equipment) -> None:
        """
        Save an equipment entity to the database.
        
        Args:
            entity (Equipment): The equipment entity to save
        """
        db = get_db()
        with Session(db) as session:
            session.add(entity)
            session.commit()
            logger.info(f"Saved equipment to database: {entity.name} (ID: {entity.equipment_id})")
    
    def load_entity(self, entity_id: str) -> Optional[Equipment]:
        """
        Load an equipment from the database.
        
        Args:
            entity_id (str): The ID of the equipment to load
            
        Returns:
            Equipment: The loaded equipment, or None if not found
        """
        # Check if already loaded in cache
        if entity_id in self.entities:
            return self.entities[entity_id]
            
        db = get_db()
        with Session(db) as session:
            equipment = session.query(Equipment).filter(Equipment.equipment_id == entity_id).first()
            if not equipment:
                logger.warning(f"Equipment not found: {entity_id}")
                return None
            # Cache the loaded entity
            self.entities[entity_id] = equipment
            return equipment
    
    def delete_entity(self, entity_id: str) -> None:
        """
        Delete an equipment from the database.
        
        Args:
            entity_id (str): The ID of the equipment to delete
        """
        db = get_db()
        with Session(db) as session:
            equipment = session.query(Equipment).filter(Equipment.equipment_id == entity_id).first()
            if equipment:
                session.delete(equipment)
                session.commit()
                logger.info(f"Deleted equipment from database: {entity_id}")
                # Remove from cache
                self.entities.pop(entity_id, None)
            else:
                logger.warning(f"Attempted to delete non-existent equipment: {entity_id}")

    ### Advanced Query methods ###

    def find_equipment_by_name(self, name: str) -> List[Equipment]:
        """
        Find equipment by name.
        
        Args:
            name (str): The name to search for
            
        Returns:
            List[Equipment]: A list of equipment with the given name
        """
        db = get_db()
        with Session(db) as session:
            items = session.query(Equipment).filter(Equipment.name == name).all()
            return items
        
    def find_equipment_by_type(self, equipment_type: str) -> List[Equipment]:
        """
        Find equipment by type.
        
        Args:
            equipment_type (str): The type to search for
            
        Returns:
            List[Equipment]: A list of equipment with the given type
        """
        db = get_db()
        with Session(db) as session:
            items = session.query(Equipment).filter(Equipment.equipment_type == equipment_type).all()
            return items
        
    def find_equipment_by_property(self, key: str, value: Any) -> List[Equipment]:
        """
        Find equipment by property.
        
        Args:
            key (str): The property key to search
            value (Any): The property value to match
        """
        db = get_db()
        with Session(db) as session:
            items = session.query(Equipment).filter(Equipment.properties[key] == value).all()
            return items
    
    def find_equipment_by_location(self, location_id: str) -> List[Equipment]:
        """
        Find equipment by location.
        
        Args:
            location_id (str): The ID of the location to search
            
        Returns:
            List[Equipment]: A list of equipment at the given location
        """
        db = get_db()
        with Session(db) as session:
            items = session.query(Equipment).filter(Equipment.location_id == location_id).all()
            return items

    def get_all_entities(self) -> List[Equipment]:
        """
        Get all equipment from the database.
        
        Returns:
            List[Equipment]: List of all equipment
        """
        db = get_db()
        with Session(db) as session:
            return session.query(Equipment).all()

    ### Update Methods ###

    def update_entity(self, entity_id: str, **kwargs) -> Optional[Equipment]:
        """
        Update an equipment's attributes.
        
        Args:
            entity_id (str): The ID of the equipment to update
            **kwargs: Key-value pairs of attributes to update
            
        Returns:
            Equipment: The updated equipment, or None if not found
        """
        db = get_db()
        with Session(db) as session:
            equipment = session.query(Equipment).filter(Equipment.equipment_id == entity_id).first()
            if not equipment:
                logger.warning(f"Equipment not found for update: {entity_id}")
                return None
            
            for key, value in kwargs.items():
                if hasattr(equipment, key):
                    setattr(equipment, key, value)
                else:
                    logger.warning(f"Invalid attribute '{key}' for equipment update")
            
            session.commit()
            logger.info(f"Updated equipment: {entity_id}")
            # Update cache
            self.entities[entity_id] = equipment
            return equipment

    ### Bulk Operations ###

    def load_entities(self, entity_ids: List[str]) -> List[Equipment]:
        """
        Load multiple equipment from the database.
        
        Args:
            entity_ids (List[str]): A list of equipment IDs to load
            
        Returns:
            List[Equipment]: A list of loaded equipment
        """
        db = get_db()
        with Session(db) as session:
            items = session.query(Equipment).filter(Equipment.equipment_id.in_(entity_ids)).all()
            for item in items:
                self.entities[item.equipment_id] = item
            return items

    ### Cache Management ###

    def clear_cache(self) -> None:
        """
        Clear the cache of loaded entities.
        """
        self.entities.clear()
        logger.info("Cache cleared")

    def refresh_cache(self, entity_id: str) -> Optional[Equipment]:
        """
        Refresh a specific equipment in the cache.
        
        Args:
            entity_id (str): The ID of the equipment to refresh
            
        Returns:
            Equipment: The refreshed equipment, or None if not found
        """
        self.entities.pop(entity_id, None)  # Remove from cache if present
        equipment = self.load_entity(entity_id)
        if equipment:
            self.entities[entity_id] = equipment
        return equipment

    ### Pagination ###

    def find_equipment_paginated(self, page: int, page_size: int) -> List[Equipment]:
        """
        Retrieve equipment with pagination.
        
        Args:
            page (int): The page number (1-based index)
            page_size (int): The number of items per page
            
        Returns:
            List[Equipment]: A list of equipment for the given page
        """
        db = get_db()
        with Session(db) as session:
            items = session.query(Equipment).offset((page - 1) * page_size).limit(page_size).all()
            return items

    ### Soft Delete ###

    def soft_delete_entity(self, entity_id: str) -> None:
        """
        Soft delete an equipment by marking it as inactive.
        
        Args:
            entity_id (str): The ID of the equipment to soft delete
        """
        db = get_db()
        with Session(db) as session:
            equipment = session.query(Equipment).filter(Equipment.equipment_id == entity_id).first()
            if equipment:
                equipment.is_active = False
                session.commit()
                logger.info(f"Soft deleted equipment: {entity_id}")
                self.entities.pop(entity_id, None)
            else:
                logger.warning(f"Attempted to soft delete non-existent equipment: {entity_id}")

    ### Export/Import ###

    def export_items(self, file_path: str) -> None:
        """
        Export all equipment to a JSON file.
        
        Args:
            file_path (str): The file path to save the equipment
        """
        with open(file_path, 'w') as file:
            json.dump([item.to_dict() for item in self.entities.values()], file)
        logger.info(f"Exported equipment to {file_path}")

    def import_items(self, file_path: str) -> None:
        """
        Import equipment from a JSON file.
        
        Args:
            file_path (str): The file path to load the equipment from
        """
        with open(file_path, 'r') as file:
            items = json.load(file)
            for item_data in items:
                equipment = Equipment.from_dict(item_data)
                self.save_entity(equipment)
        logger.info(f"Imported equipment from {file_path}")

    ### Audit Logging ###

    def log_equipment_changes(self, entity_id: str, changes: Dict[str, Any]) -> None:
        """
        Log changes made to an equipment.
        
        Args:
            entity_id (str): The ID of the equipment
            changes (Dict[str, Any]): A dictionary of changes
        """
        logger.info(f"Changes to equipment {entity_id}: {changes}")