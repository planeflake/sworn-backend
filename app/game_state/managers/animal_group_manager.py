from sqlalchemy import Column, String, Text, Table, MetaData, select, insert, update, delete
from sqlalchemy.orm import Session
from database.connection import get_db
from pydantic import BaseModel
from typing import List, Optional
import logging as logger
import json
import uuid

from ..entities.animal_group import AnimalGroupEntity

# Pydantic model for database operations
class AnimalGroupDB(BaseModel):
    group_id: str
    group_name: Optional[str] = None
    data: str  # JSON string of animal group data

class AnimalGroupManager:
    def __init__(self):
        """Initialize the AnimalGroupManager."""
        self.groups = {}  # Cache groups by group_id
        self._setup_db_metadata()
        logger.info("AnimalGroupManager initialized")
    
    def _setup_db_metadata(self):
        """Set up SQLAlchemy metadata for the animal_groups table."""
        self.metadata = MetaData()
        self.groups_table = Table(
            'animal_groups', 
            self.metadata,
            Column('group_id', String(36), primary_key=True),
            Column('group_name', String(100)),
            Column('data', Text)
        )
    
    def create_group(self, group_name: str, description: Optional[str] = None) -> AnimalGroupEntity:
        """
        Create a new animal group with a unique ID.
        
        Args:
            group_name (str): The name of the group.
            description (Optional[str]): Description of the group.
            
        Returns:
            AnimalGroupEntity: The newly created animal group.
        """
        group = AnimalGroupEntity()
        group.set_group_name(group_name)
        group.set_description(description or f"A group named {group_name}")
        
        self.groups[group.group_id] = group
        self.save_group(group)
        logger.info(f"Created new animal group: {group_name} (ID: {group.group_id})")
        return group

    def load_group(self, group_id: str) -> Optional[AnimalGroupEntity]:
        """
        Load an animal group from the database.
        
        Args:
            group_id (str): The ID of the group.
            
        Returns:
            AnimalGroupEntity: The loaded group, or None if not found.
        """
        if group_id in self.groups:
            return self.groups[group_id]
        
        db = get_db()
        with Session(db) as session:
            stmt = select(self.groups_table).where(self.groups_table.c.group_id == group_id)
            result = session.execute(stmt).first()
            if result is None:
                logger.warning(f"Animal group not found: {group_id}")
                return None
            
            group_data = json.loads(result.data)
            group = AnimalGroupEntity.from_dict(group_data)
            self.groups[group_id] = group
            logger.info(f"Loaded animal group: {group.group_name} (ID: {group_id})")
            return group

    def save_group(self, group: AnimalGroupEntity) -> bool:
        """
        Save an animal group to the database.
        
        Args:
            group (AnimalGroupEntity): The group to save.
            
        Returns:
            bool: True if save was successful, False otherwise.
        """
        if not group.is_dirty():
            return True
        
        group_dict = group.to_dict()
        group_data = json.dumps(group_dict)
        group_db = AnimalGroupDB(
            group_id=group.group_id,
            group_name=group.group_name,
            data=group_data
        )
        
        db = get_db()
        with Session(db) as session:
            try:
                stmt = select(self.groups_table).where(self.groups_table.c.group_id == group.group_id)
                exists = session.execute(stmt).first() is not None
                
                if exists:
                    stmt = update(self.groups_table).where(
                        self.groups_table.c.group_id == group.group_id
                    ).values(
                        group_name=group_db.group_name,
                        data=group_db.data
                    )
                    session.execute(stmt)
                else:
                    stmt = insert(self.groups_table).values(
                        group_id=group_db.group_id,
                        group_name=group_db.group_name,
                        data=group_db.data
                    )
                    session.execute(stmt)
                
                session.commit()
                group.mark_clean()
                logger.info(f"Saved animal group: {group.group_name} (ID: {group.group_id})")
                return True
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to save animal group {group.group_id}: {str(e)}")
                return False

    def get_all_groups(self) -> List[AnimalGroupEntity]:
        """
        Retrieve all animal groups from the database.
        
        Returns:
            list: A list of AnimalGroupEntity instances.
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.groups_table.c.group_id)
            results = session.execute(stmt).fetchall()
            groups_list = []
            for result in results:
                group_id = result[0]
                group = self.load_group(group_id)
                if group:
                    groups_list.append(group)
            return groups_list

    def delete_group(self, group_id: str) -> bool:
        """
        Delete an animal group from the database.
        
        Args:
            group_id (str): The ID of the group to delete.
            
        Returns:
            bool: True if deletion was successful, False otherwise.
        """
        if group_id in self.groups:
            del self.groups[group_id]
        
        db = get_db()
        with Session(db) as session:
            try:
                stmt = delete(self.groups_table).where(self.groups_table.c.group_id == group_id)
                session.execute(stmt)
                session.commit()
                logger.info(f"Deleted animal group: {group_id}")
                return True
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to delete animal group {group_id}: {str(e)}")
                return False

    def add_member_to_group(self, group_id: str, animal_id: str) -> bool:
        """
        Add an animal (by its ID) to a group.
        
        Args:
            group_id (str): The group ID.
            animal_id (str): The animal's ID.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        group = self.load_group(group_id)
        if not group:
            logger.warning(f"Group not found: {group_id}")
            return False
        group.add_member(animal_id)
        return self.save_group(group)

    def remove_member_from_group(self, group_id: str, animal_id: str) -> bool:
        """
        Remove an animal (by its ID) from a group.
        
        Args:
            group_id (str): The group ID.
            animal_id (str): The animal's ID.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        group = self.load_group(group_id)
        if not group:
            logger.warning(f"Group not found: {group_id}")
            return False
        group.remove_member(animal_id)
        return self.save_group(group)

    def get_group_count(self) -> int:
        """
        Get the total number of animal groups.
        
        Returns:
            int: The count of groups.
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.groups_table)
            results = session.execute(stmt).all()
            return len(results)
