from sqlalchemy import Column, String, Text, Table, MetaData
from sqlalchemy import select, insert, update, delete
from sqlalchemy.orm import Session
from database import get_db
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Union, Any
import logging as logger
import uuid
import json

from app.models.villagers import VillagerDB
from ..entities.villager import Villager

class VillagerManager:
    def __init__(self):
        """Initialize the VillagerManager."""
        self.villagers = {}  # Dictionary to store loaded villagers by ID
        self._setup_db_metadata()
        logger.info("VillagerManager initialized")
    
    def _setup_db_metadata(self):
        """Set up SQLAlchemy metadata for villagers table."""
        self.metadata = MetaData()
        self.villagers_table = Table(
            'villagers', 
            self.metadata,
            Column('villager_id', String(36), primary_key=True),
            Column('name', String(100)),
            Column('location_id', String(36)),
            Column('data', Text)
        )
    
    def create_villager(self, name: str, description: Optional[str] = None) -> Villager:
        """
        Create a new villager with a unique ID.
        
        Args:
            name (str): The villager's name
            description (str): Optional description for the villager
            
        Returns:
            Villager: The newly created villager instance
        """
        # Generate a unique ID for the new villager
        villager_id = str(uuid.uuid4())
        
        # Create a new Villager instance
        villager = Villager(villager_id)
        villager.set_basic_info(name, description)
        
        # Add the villager to our local cache
        self.villagers[villager_id] = villager
        
        # Save the villager to the database
        self.save_villager(villager)
        
        logger.info(f"Created new villager: {name} (ID: {villager_id})")
        return villager
    
    def load_villager(self, villager_id: str) -> Optional[Villager]:
        """
        Load a villager from the database.
        
        Args:
            villager_id (str): The ID of the villager to load
            
        Returns:
            Villager: The loaded villager instance, or None if not found
        """
        # Check if the villager is already loaded
        if villager_id in self.villagers:
            return self.villagers[villager_id]
        
        # If not, load it from the database
        db = get_db()
        with Session(db) as session:
            stmt = select(self.villagers_table).where(self.villagers_table.c.villager_id == villager_id)
            result = session.execute(stmt).first()
            
            if result is None:
                logger.warning(f"Villager not found: {villager_id}")
                return None
            
            # Deserialize the villager data
            villager_data = json.loads(result.data)
            villager = Villager.from_dict(villager_data)
            
            # Cache the villager
            self.villagers[villager_id] = villager
            
            logger.info(f"Loaded villager: {villager.name} (ID: {villager_id})")
            return villager
    
    def save_villager(self, villager: Villager) -> bool:
        """
        Save a villager to the database.
        
        Args:
            villager (Villager): The villager instance to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not villager.is_dirty():
            # No changes to save
            return True
        
        # Convert the villager to a JSON string
        villager_dict = villager.to_dict()
        villager_data = json.dumps(villager_dict)
        
        # Create a Pydantic model for database operations
        villager_db = VillagerDB(
            villager_id=villager.villager_id,
            name=villager.name,
            location_id=villager.location_id,
            data=villager_data
        )
        
        # Save to database
        db = get_db()
        with Session(db) as session:
            try:
                # Check if the villager already exists
                stmt = select(self.villagers_table).where(self.villagers_table.c.villager_id == villager.villager_id)
                exists = session.execute(stmt).first() is not None
                
                if exists:
                    # Update existing villager
                    stmt = update(self.villagers_table).where(
                        self.villagers_table.c.villager_id == villager.villager_id
                    ).values(
                        name=villager_db.name,
                        location_id=villager_db.location_id,
                        data=villager_db.data
                    )
                    session.execute(stmt)
                else:
                    # Insert new villager
                    stmt = insert(self.villagers_table).values(
                        villager_id=villager_db.villager_id,
                        name=villager_db.name,
                        location_id=villager_db.location_id,
                        data=villager_db.data
                    )
                    session.execute(stmt)
                
                session.commit()
                
                # Mark the villager as clean (no unsaved changes)
                villager.mark_clean()
                
                logger.info(f"Saved villager: {villager.name} (ID: {villager.villager_id})")
                return True
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to save villager {villager.villager_id}: {str(e)}")
                return False
    
    def get_all_villagers(self) -> List[Villager]:
        """
        Get all villagers from the database.
        
        Returns:
            list: List of all villager instances
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.villagers_table.c.villager_id)
            results = session.execute(stmt).fetchall()
            
            villagers = []
            for result in results:
                villager_id = result[0]
                villager = self.load_villager(villager_id)
                if villager:
                    villagers.append(villager)
            
            return villagers
    
    def get_villagers_at_location(self, location_id: str) -> List[Villager]:
        """
        Get all villagers at a specific location.
        
        Args:
            location_id (str): The ID of the location
            
        Returns:
            list: List of villager instances at the location
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.villagers_table.c.villager_id).where(self.villagers_table.c.location_id == location_id)
            results = session.execute(stmt).fetchall()
            
            villagers = []
            for result in results:
                villager_id = result[0]
                villager = self.load_villager(villager_id)
                if villager:
                    villagers.append(villager)
            
            return villagers
    
    def delete_villager(self, villager_id: str) -> bool:
        """
        Delete a villager from the database.
        
        Args:
            villager_id (str): The ID of the villager to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Remove from cache if present
        if villager_id in self.villagers:
            del self.villagers[villager_id]
        
        # Delete from database
        db = get_db()
        with Session(db) as session:
            try:
                stmt = delete(self.villagers_table).where(self.villagers_table.c.villager_id == villager_id)
                session.execute(stmt)
                session.commit()
                logger.info(f"Deleted villager: {villager_id}")
                return True
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to delete villager {villager_id}: {str(e)}")
                return False
    
    def update_villager_location(self, villager_id: str, location_id: str) -> bool:
        """
        Update a villager's current location.
        
        Args:
            villager_id (str): The ID of the villager
            location_id (str): The new location ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        villager = self.load_villager(villager_id)
        if not villager:
            logger.warning(f"Cannot update location: Villager not found: {villager_id}")
            return False
        
        villager.set_location(location_id)
        return self.save_villager(villager)
    
    def get_villager_by_name(self, name: str) -> Optional[Villager]:
        """
        Find a villager by name.
        
        Args:
            name (str): The name to search for
            
        Returns:
            Villager: The villager with the given name, or None if not found
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.villagers_table.c.villager_id).where(self.villagers_table.c.name == name)
            result = session.execute(stmt).first()
            
            if result:
                return self.load_villager(result[0])
            return None
    
    def set_preferred_biome(self, villager_id: str, biome: str) -> bool:
        """
        Set the preferred biome for a villager.
        
        Args:
            villager_id (str): The ID of the villager
            biome (str): The biome ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        villager = self.load_villager(villager_id)
        if not villager:
            logger.warning(f"Cannot set preferred biome: Villager not found: {villager_id}")
            return False
        
        villager.set_preferred_biome(biome)
        return self.save_villager(villager)
    
    def add_unacceptable_biome(self, villager_id: str, biome: str) -> bool:
        """
        Add an unacceptable biome for a villager.
        
        Args:
            villager_id (str): The ID of the villager
            biome (str): The biome ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        villager = self.load_villager(villager_id)
        if not villager:
            logger.warning(f"Cannot add unacceptable biome: Villager not found: {villager_id}")
            return False
        
        villager.add_unacceptable_biome(biome)
        return self.save_villager(villager)
    
    def add_task(self, villager_id: str, task: str) -> bool:
        """
        Add a task for a villager.
        
        Args:
            villager_id (str): The ID of the villager
            task (str): The task ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        villager = self.load_villager(villager_id)
        if not villager:
            logger.warning(f"Cannot add task: Villager not found: {villager_id}")
            return False
        
        villager.add_task(task)
        return self.save_villager(villager)
    
    def complete_task(self, villager_id: str, task: str) -> bool:
        """
        Mark a task as completed for a villager.
        
        Args:
            villager_id (str): The ID of the villager
            task (str): The task ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        villager = self.load_villager(villager_id)
        if not villager:
            logger.warning(f"Cannot complete task: Villager not found: {villager_id}")
            return False
        
        result = villager.complete_task(task)
        if result:
            return self.save_villager(villager)
        return False
    
    def save_all_villagers(self) -> bool:
        """
        Save all loaded villagers to the database.
        
        Returns:
            bool: True if all saves were successful
        """
        success = True
        for villager in self.villagers.values():
            if villager.is_dirty():
                if not self.save_villager(villager):
                    success = False
        
        return success