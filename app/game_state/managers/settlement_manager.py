# Template for creating manager classes in the game state architecture
# Copy this file to app/game_state/managers/ and customize for each entity type

import json
import uuid
import logging
from typing import List, Dict, Optional, Any, Type, Union
from sqlalchemy import Column, String, Text, Table, MetaData
from sqlalchemy import select, insert, update, delete
from sqlalchemy.orm import Session
from database.connection import get_db

# Import your entity class
# from app.game_state.entities.entity_template import EntityTemplate

logger = logging.getLogger(__name__)

# This is a type placeholder - replace with your actual entity class
EntityType = Any  # Should be your entity class like 'EntityTemplate'

class SettlementManager:
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
    
    def __init__(self):
        """Initialize the manager."""
        # Cache of loaded entities
        self.entities = {}  # Dictionary to store loaded entities by ID
        
        # Set up database metadata
        self._setup_db_metadata()
        
        logger.info(f"{self.__class__.__name__} initialized")
    
    def _setup_db_metadata(self):
        """Set up SQLAlchemy metadata for the entity table."""
        self.metadata = MetaData()
        
        # Define the table structure for this entity type
        # Modify these columns to match your database schema
        self.entity_table = Table(
            'entities',  # Replace with your actual table name
            self.metadata,
            Column('entity_id', String(36), primary_key=True),
            Column('name', String(100)),
            Column('location_id', String(36)),
            Column('data', Text)  # JSON data column
        )
    
    def create_entity(self, name: str, description: Optional[str] = None) -> EntityType:
        """
        Create a new entity with a unique ID.
        
        Args:
            name (str): The entity's name
            description (str, optional): Optional description
            
        Returns:
            EntityType: The newly created entity
        """
        # Generate a unique ID
        entity_id = str(uuid.uuid4())
        
        # Create a new entity instance
        # Replace with your actual entity class
        # entity = EntityTemplate(entity_id)
        entity = None  # Replace with your actual entity instantiation
        
        # Set basic information
        entity.set_basic_info(name, description or f"An entity named {name}")
        
        # Add to cache
        self.entities[entity_id] = entity
        
        # Save to database
        self.save_entity(entity)
        
        logger.info(f"Created new entity: {name} (ID: {entity_id})")
        return entity
    
    def load_settlement(self, settlement_id: str) -> Optional[EntityType]:
        """
        Load an entity from the database or cache.
        
        Args:
            entity_id (str): The ID of the entity to load
            
        Returns:
            EntityType: The loaded entity, or None if not found
        """
        # Check if already loaded in cache
        if settlement_id in self.entities:
            return self.entities[settlement_id]
        
        # Load from database
        db = get_db()
        with Session(db) as session:
            stmt = select(self.entity_table).where(
                self.entity_table.c.entity_id == settlement_id
            )
            result = session.execute(stmt).first()
            
            if result is None:
                logger.warning(f"Entity not found: {settlement_id}")
                return None
            
            # Deserialize entity data
            try:
                entity_data = json.loads(result.data)
                # Replace with your actual entity class
                # entity = EntityTemplate.from_dict(entity_data)
                entity = None  # Replace with your actual deserialization
                
                # Cache the entity
                self.entities[settlement_id] = entity
                
                logger.info(f"Loaded entity: {entity.name} (ID: {settlement_id})")
                return entity
                
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Error deserializing entity {settlement_id}: {e}")
                return None
    
    def save_settlement(self, settlement: EntityType) -> bool:
        """
        Save an entity to the database.
        
        Args:
            entity (EntityType): The entity to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Skip if no changes to save
        if not settlement.is_dirty():
            return True
        
        # Convert entity to JSON
        try:
            settlement_dict = settlement.to_dict()
            settlement_data = json.dumps(settlement_dict)
            
            # Save to database
            db = get_db()
            with Session(db) as session:
                try:
                    # Check if entity already exists
                    stmt = select(self.entity_table).where(
                        self.entity_table.c.entity_id == settlement.settlement_id
                    )
                    exists = session.execute(stmt).first() is not None
                    
                    if exists:
                        # Update existing entity
                        stmt = update(self.entity_table).where(
                            self.entity_table.c.entity_id == settlement.entity_id
                        ).values(
                            name=settlement.name,
                            location_id=settlement.location_id,
                            data=settlement_data
                        )
                        session.execute(stmt)
                    else:
                        # Insert new entity
                        stmt = insert(self.entity_table).values(
                            entity_id=settlement.entity_id,
                            name=settlement.name,
                            location_id=settlement.location_id,
                            data=settlement_data
                        )
                        session.execute(stmt)
                    
                    session.commit()
                    
                    # Mark entity as clean (no unsaved changes)
                    settlement.mark_clean()
                    
                    logger.info(f"Saved entity: {settlement.name} (ID: {settlement.settlement_id})")
                    return True
                    
                except Exception as e:
                    session.rollback()
                    logger.error(f"Failed to save entity {settlement.entity_id}: {str(e)}")
                    return False
        
        except Exception as e:
            logger.error(f"Error serializing entity {settlement.entity_id}: {str(e)}")
            return False
    
    def find_settlements_by_area(self, area_id: str) -> List[EntityType]:
        """
        Find all entities in a specific area.
        
        Args:
            area_id (str): The ID of the area to search
            
        Returns:
            List[EntityType]: List of entities in the area
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.entity_table.c.entity_id).where(
                self.entity_table.c.location_id == area_id
            )
            results = session.execute(stmt).fetchall()
            
            entities = []
            for result in results:
                entity_id = result[0]
                entity = self.load_entity(entity_id)
                if entity:
                    entities.append(entity)
            return entities

    def delete_entity(self, settlement_id: str) -> bool:
        """
        Delete an entity from the database.
        
        Args:
            entity_id (str): The ID of the entity to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Remove from cache if present
        if settlement_id in self.entities:
            del self.entities[settlement_id]
        
        # Delete from database
        db = get_db()
        with Session(db) as session:
            try:
                stmt = delete(self.entity_table).where(
                    self.entity_table.c.entity_id == settlement_id
                )
                session.execute(stmt)
                session.commit()
                
                logger.info(f"Deleted entity: {settlement_id}")
                return True
                
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to delete entity {settlement_id}: {str(e)}")
                return False
    
    def get_all_entities(self) -> List[EntityType]:
        """
        Get all entities from the database.
        
        Returns:
            List[EntityType]: List of all entities
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.entity_table.c.entity_id)
            results = session.execute(stmt).fetchall()
            
            entities = []
            for result in results:
                entity_id = result[0]
                entity = self.load_entity(entity_id)
                if entity:
                    entities.append(entity)
            
            return entities
    
    def get_entities_at_location(self, location_id: str) -> List[EntityType]:
        """
        Get all entities at a specific location.
        
        Args:
            location_id (str): The location ID
            
        Returns:
            List[EntityType]: List of entities at the location
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.entity_table.c.entity_id).where(
                self.entity_table.c.location_id == location_id
            )
            results = session.execute(stmt).fetchall()
            
            entities = []
            for result in results:
                entity_id = result[0]
                entity = self.load_entity(entity_id)
                if entity:
                    entities.append(entity)
            
            return entities
    
    def get_entity_by_name(self, name: str) -> Optional[EntityType]:
        """
        Find an entity by name.
        
        Args:
            name (str): The name to search for
            
        Returns:
            EntityType: The entity with the given name, or None if not found
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.entity_table.c.entity_id).where(
                self.entity_table.c.name == name
            )
            result = session.execute(stmt).first()
            
            if result:
                return self.load_entity(result[0])
            
            return None
    
    def update_entity_location(self, settlement_id: str, location_id: str) -> bool:
        """
        Update an entity's location.
        
        Args:
            entity_id (str): The entity ID
            location_id (str): The new location ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        entity = self.load_entity(settlement_id)
        if not entity:
            logger.warning(f"Cannot update location: Entity not found: {settlement_id}")
            return False
        
        entity.set_location(location_id)
        return self.save_entity(entity)
    
    def save_all_entities(self) -> bool:
        """
        Save all loaded entities to the database.
        
        Returns:
            bool: True if all saves were successful
        """
        success = True
        for entity in self.entities.values():
            if entity.is_dirty():
                if not self.save_entity(entity):
                    success = False
        
        return success
    
    def get_entity_count(self) -> int:
        """
        Get the total number of entities.
        
        Returns:
            int: The total count of entities
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.entity_table)
            result = session.execute(stmt).all()
            return len(result)

    ### entity unique methods ###

    def start_building(self,building_type: str, location_id: str):
        """
        Start building a new building at a location.
        
        Args:
            building_type (str): The type of building to construct
            location_id (str): The ID of the location to build at
        """
        # Perform building construction logic
        logger.info(f"Building {building_type} at location {location_id}")
        self.set_relation(location_id, "building", building_type)

    def complete__building(self, building_type: str, location_id: str):
        """
        Complete a new building at a location.
        
        Args:
            building_type (str): The type of building to construct
            location_id (str): The ID of the location to build at
        """
        # Perform building construction logic
        logger.info(f"Building {building_type} at location {location_id}")
        self.set_relation(location_id, "building", building_type)

    def repair_building(self, building_type: str, location_id: str):
        """
        Repair a building at a location.
        
        Args:
            building_type (str): The type of building to repair
            location_id (str): The ID of the location to repair
        """
        # Perform building repair logic
        logger.info(f"Repairing {building_type} at location {location_id}")
        self.set_relation(location_id, "building", building_type)

    def destroy_building(self, building_type: str, location_id: str):
        """
        Destroy a building at a location.
        """
        # Perform building destruction logic
        logger.info(f"Destroying {building_type} at location {location_id}")
        self.set_relation(location_id, "building", building_type)

    ### Update Methods ###

    def update_entity(self, entity_id: str, **kwargs) -> Optional[EntityType]:
        """
        Update an entity's attributes.
        
        Args:
            entity_id (str): The ID of the entity to update
            **kwargs: Key-value pairs of attributes to update
            
        Returns:
            EntityType: The updated entity, or None if not found
        """
        entity = self.load_entity(entity_id)
        if not entity:
            logger.warning(f"Entity not found for update: {entity_id}")
            return None

        for key, value in kwargs.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
            else:
                logger.warning(f"Invalid attribute '{key}' for entity update")
        
        if self.save_entity(entity):
            logger.info(f"Updated entity: {entity_id}")
            return entity
        return None

    ### Bulk Operations ###

    def load_entities(self, entity_ids: List[str]) -> List[EntityType]:
        """
        Load multiple entities from the database.
        
        Args:
            entity_ids (List[str]): A list of entity IDs to load
            
        Returns:
            List[EntityType]: A list of loaded entities
        """
        entities = []
        for entity_id in entity_ids:
            entity = self.load_entity(entity_id)
            if entity:
                entities.append(entity)
        return entities

    ### Cache Management ###

    def clear_cache(self) -> None:
        """
        Clear the cache of loaded entities.
        """
        self.entities.clear()
        logger.info("Cache cleared")

    def refresh_cache(self, entity_id: str) -> Optional[EntityType]:
        """
        Refresh a specific entity in the cache.
        
        Args:
            entity_id (str): The ID of the entity to refresh
            
        Returns:
            EntityType: The refreshed entity, or None if not found
        """
        entity = self.load_entity(entity_id)
        if entity:
            self.entities[entity_id] = entity
        return entity

    ### Pagination ###

    def find_entities_paginated(self, page: int, page_size: int) -> List[EntityType]:
        """
        Retrieve entities with pagination.
        
        Args:
            page (int): The page number (1-based index)
            page_size (int): The number of entities per page
            
        Returns:
            List[EntityType]: A list of entities for the given page
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.entity_table.c.entity_id).offset((page - 1) * page_size).limit(page_size)
            results = session.execute(stmt).fetchall()
            
            entities = []
            for result in results:
                entity_id = result[0]
                entity = self.load_entity(entity_id)
                if entity:
                    entities.append(entity)
            return entities

    ### Soft Delete ###

    def soft_delete_entity(self, entity_id: str) -> bool:
        """
        Soft delete an entity by marking it as inactive.
        
        Args:
            entity_id (str): The ID of the entity to soft delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        entity = self.load_entity(entity_id)
        if not entity:
            logger.warning(f"Attempted to soft delete non-existent entity: {entity_id}")
            return False
        
        entity.is_active = False
        return self.save_entity(entity)

    ### Export/Import ###

    def export_entities(self, file_path: str) -> None:
        """
        Export all entities to a JSON file.
        
        Args:
            file_path (str): The file path to save the entities
        """
        with open(file_path, 'w') as file:
            json.dump([entity.to_dict() for entity in self.entities.values()], file)
        logger.info(f"Exported entities to {file_path}")

    def import_entities(self, file_path: str) -> None:
        """
        Import entities from a JSON file.
        
        Args:
            file_path (str): The file path to load the entities from
        """
        with open(file_path, 'r') as file:
            entities = json.load(file)
            for entity_data in entities:
                # Replace with your actual entity class instantiation
                # entity = EntityTemplate.from_dict(entity_data)
                entity = None  # Replace with actual deserialization
                self.save_entity(entity)
        logger.info(f"Imported entities from {file_path}")

    ### Audit Logging ###

    def log_entity_changes(self, entity_id: str, changes: Dict[str, Any]) -> None:
        """
        Log changes made to an entity.
        
        Args:
            entity_id (str): The ID of the entity
            changes (Dict[str, Any]): A dictionary of changes
        """
        logger.info(f"Changes to entity {entity_id}: {changes}")