# app/game_state/managers/resource_manager.py
from typing import List, Dict, Optional, Any, Union
from sqlalchemy import Column, String, Text, Table, MetaData
from sqlalchemy import select, insert, update, delete
from sqlalchemy.orm import Session
from database.connection import get_db
import logging
import json
import uuid

# Import the Resource entity and its enums
from app.game_state.entities.resource import (
    Resource, ResourceType, ResourceRarity, ResourceQuality, 
    MaterialState, ElementalAffinity, UsageCategory
)

logger = logging.getLogger(__name__)

class ResourceManager:
    """
    Manager for Resource entities that handles persistence and lifecycle.
    
    Responsible for:
    1. Loading resources from the database
    2. Saving resources to the database
    3. Creating new resources
    4. Maintaining a cache of loaded resources
    5. Providing query methods for finding resources
    """
    
    def __init__(self):
        """Initialize the ResourceManager."""
        # Cache of loaded resources
        self.resources = {}  # Dictionary to store loaded resources by ID
        
        # Set up database metadata
        self._setup_db_metadata()
        
        logger.info(f"{self.__class__.__name__} initialized")
    
    def _setup_db_metadata(self):
        """Set up SQLAlchemy metadata for the resources table."""
        self.metadata = MetaData()
        
        # Define the table structure for resources
        self.resources_table = Table(
            'resources',  # Using the actual resources table name
            self.metadata,
            Column('id', String(36), primary_key=True),
            Column('name', String(100)),
            Column('resource_type', String(50)),
            Column('rarity', String(20)),
            Column('quality', String(20)),
            Column('location_id', String(36)),
            Column('owner_id', String(36)),
            Column('data', Text)  # JSON data column
        )
    
    def create_resource(self, name: str, description: Optional[str] = None,
                       resource_type: Optional[ResourceType] = None) -> Resource:
        """
        Create a new resource with a unique ID.
        
        Args:
            name: The resource's name
            description: Optional description
            resource_type: Optional resource type
            
        Returns:
            Resource: The newly created resource
        """
        # Create a new resource instance
        resource = Resource(name=name, description=description)
        
        # Set resource type if provided
        if resource_type:
            resource.resource_type = resource_type
        
        # Add to cache
        self.resources[resource.id] = resource
        
        # Save to database
        self.save_resource(resource)
        
        logger.info(f"Created new resource: {name} (ID: {resource.id})")
        return resource
    
    def load_resource(self, resource_id: str) -> Optional[Resource]:
        """
        Load a resource from the database or cache.
        
        Args:
            resource_id: The ID of the resource to load
            
        Returns:
            Resource: The loaded resource, or None if not found
        """
        # Check if already loaded in cache
        if resource_id in self.resources:
            return self.resources[resource_id]
        
        # Load from database
        db = get_db()
        with Session(db) as session:
            stmt = select(self.resources_table).where(
                self.resources_table.c.id == resource_id
            )
            result = session.execute(stmt).first()
            
            if result is None:
                logger.warning(f"Resource not found: {resource_id}")
                return None
            
            # Deserialize resource data
            try:
                resource_data = json.loads(result.data)
                resource = Resource.from_dict(resource_data)
                
                # Cache the resource
                self.resources[resource_id] = resource
                
                logger.info(f"Loaded resource: {resource.name} (ID: {resource_id})")
                return resource
                
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Error deserializing resource {resource_id}: {e}")
                return None
    
    def save_resource(self, resource: Resource) -> bool:
        """
        Save a resource to the database.
        
        Args:
            resource: The resource to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Skip if no changes to save
        if not resource.is_dirty:
            return True
        
        # Convert resource to JSON
        try:
            resource_dict = resource.to_dict()
            resource_data = json.dumps(resource_dict)
            
            # Save to database
            db = get_db()
            with Session(db) as session:
                try:
                    # Check if resource already exists
                    stmt = select(self.resources_table).where(
                        self.resources_table.c.id == resource.id
                    )
                    exists = session.execute(stmt).first() is not None
                    
                    if exists:
                        # Update existing resource
                        stmt = update(self.resources_table).where(
                            self.resources_table.c.id == resource.id
                        ).values(
                            name=resource.name,
                            resource_type=resource.resource_type.value if resource.resource_type else None,
                            rarity=str(resource.rarity.value) if resource.rarity else None,
                            quality=str(resource.quality.value) if resource.quality else None,
                            location_id=resource.location_id,
                            owner_id=resource.owner_id,
                            data=resource_data
                        )
                        session.execute(stmt)
                    else:
                        # Insert new resource
                        stmt = insert(self.resources_table).values(
                            id=resource.id,
                            name=resource.name,
                            resource_type=resource.resource_type.value if resource.resource_type else None,
                            rarity=str(resource.rarity.value) if resource.rarity else None,
                            quality=str(resource.quality.value) if resource.quality else None,
                            location_id=resource.location_id,
                            owner_id=resource.owner_id,
                            data=resource_data
                        )
                        session.execute(stmt)
                    
                    session.commit()
                    
                    # Mark resource as clean (no unsaved changes)
                    resource.clean()
                    
                    logger.info(f"Saved resource: {resource.name} (ID: {resource.id})")
                    return True
                    
                except Exception as e:
                    session.rollback()
                    logger.error(f"Failed to save resource {resource.id}: {str(e)}")
                    return False
        
        except Exception as e:
            logger.error(f"Error serializing resource {resource.id}: {str(e)}")
            return False
    
    def delete_resource(self, resource_id: str) -> bool:
        """
        Delete a resource from the database.
        
        Args:
            resource_id: The ID of the resource to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Remove from cache if present
        if resource_id in self.resources:
            del self.resources[resource_id]
        
        # Delete from database
        db = get_db()
        with Session(db) as session:
            try:
                stmt = delete(self.resources_table).where(
                    self.resources_table.c.id == resource_id
                )
                session.execute(stmt)
                session.commit()
                
                logger.info(f"Deleted resource: {resource_id}")
                return True
                
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to delete resource {resource_id}: {str(e)}")
                return False
    
    def get_all_resources(self) -> List[Resource]:
        """
        Get all resources from the database.
        
        Returns:
            List[Resource]: List of all resources
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.resources_table.c.id)
            results = session.execute(stmt).fetchall()
            
            resources = []
            for result in results:
                resource_id = result[0]
                resource = self.load_resource(resource_id)
                if resource:
                    resources.append(resource)
            
            return resources
    
    def get_resources_at_location(self, location_id: str) -> List[Resource]:
        """
        Get all resources at a specific location.
        
        Args:
            location_id: The location ID
            
        Returns:
            List[Resource]: List of resources at the location
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.resources_table.c.id).where(
                self.resources_table.c.location_id == location_id
            )
            results = session.execute(stmt).fetchall()
            
            resources = []
            for result in results:
                resource_id = result[0]
                resource = self.load_resource(resource_id)
                if resource:
                    resources.append(resource)
            
            return resources
    
    def get_resources_by_owner(self, owner_id: str) -> List[Resource]:
        """
        Get all resources owned by a specific entity.
        
        Args:
            owner_id: The owner ID
            
        Returns:
            List[Resource]: List of resources owned by the entity
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.resources_table.c.id).where(
                self.resources_table.c.owner_id == owner_id
            )
            results = session.execute(stmt).fetchall()
            
            resources = []
            for result in results:
                resource_id = result[0]
                resource = self.load_resource(resource_id)
                if resource:
                    resources.append(resource)
            
            return resources
    
    def get_resource_by_name(self, name: str) -> Optional[Resource]:
        """
        Find a resource by name.
        
        Args:
            name: The name to search for
            
        Returns:
            Resource: The resource with the given name, or None if not found
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.resources_table.c.id).where(
                self.resources_table.c.name == name
            )
            result = session.execute(stmt).first()
            
            if result:
                return self.load_resource(result[0])
            
            return None
    
    def get_resources_by_type(self, resource_type: ResourceType) -> List[Resource]:
        """
        Get all resources of a specific type.
        
        Args:
            resource_type: The type of resource to find
            
        Returns:
            List[Resource]: List of resources of the specified type
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.resources_table.c.id).where(
                self.resources_table.c.resource_type == resource_type.value
            )
            results = session.execute(stmt).fetchall()
            
            resources = []
            for result in results:
                resource_id = result[0]
                resource = self.load_resource(resource_id)
                if resource:
                    resources.append(resource)
            
            return resources
    
    def update_resource_location(self, resource_id: str, location_id: str) -> bool:
        """
        Update a resource's location.
        
        Args:
            resource_id: The resource ID
            location_id: The new location ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        resource = self.load_resource(resource_id)
        if not resource:
            logger.warning(f"Cannot update location: Resource not found: {resource_id}")
            return False
        
        resource.set_location(location_id)
        return self.save_resource(resource)
    
    def save_all_resources(self) -> bool:
        """
        Save all loaded resources to the database.
        
        Returns:
            bool: True if all saves were successful
        """
        success = True
        for resource in self.resources.values():
            if resource.is_dirty:
                if not self.save_resource(resource):
                    success = False
        
        return success
    
    def get_resource_count(self) -> int:
        """
        Get the total number of resources.
        
        Returns:
            int: The total count of resources
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.resources_table)
            result = session.execute(stmt).all()
            return len(result)

    def update_resource(self, resource_id: str, **kwargs) -> Optional[Resource]:
        """
        Update a resource's attributes.
        
        Args:
            resource_id: The ID of the resource to update
            **kwargs: Key-value pairs of attributes to update
            
        Returns:
            Resource: The updated resource, or None if not found
        """
        resource = self.load_resource(resource_id)
        if not resource:
            logger.warning(f"Resource not found for update: {resource_id}")
            return None

        for key, value in kwargs.items():
            if hasattr(resource, key):
                setattr(resource, key, value)
            else:
                resource.set_property(key, value)
        
        if self.save_resource(resource):
            logger.info(f"Updated resource: {resource_id}")
            return resource
        return None

    def load_resources(self, resource_ids: List[str]) -> List[Resource]:
        """
        Load multiple resources from the database.
        
        Args:
            resource_ids: A list of resource IDs to load
            
        Returns:
            List[Resource]: A list of loaded resources
        """
        resources = []
        for resource_id in resource_ids:
            resource = self.load_resource(resource_id)
            if resource:
                resources.append(resource)
        return resources

    def clear_cache(self) -> None:
        """
        Clear the cache of loaded resources.
        """
        self.resources.clear()
        logger.info("Resource cache cleared")

    def refresh_cache(self, resource_id: str) -> Optional[Resource]:
        """
        Refresh a specific resource in the cache.
        
        Args:
            resource_id: The ID of the resource to refresh
            
        Returns:
            Resource: The refreshed resource, or None if not found
        """
        # Remove from cache if present
        if resource_id in self.resources:
            del self.resources[resource_id]
            
        # Reload from database
        return self.load_resource(resource_id)

    def get_resources_by_quality(self, quality: ResourceQuality) -> List[Resource]:
        """
        Get all resources of a specific quality.
        
        Args:
            quality: The quality level to search for
            
        Returns:
            List[Resource]: List of resources with the specified quality
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.resources_table.c.id).where(
                self.resources_table.c.quality == str(quality.value)
            )
            results = session.execute(stmt).fetchall()
            
            resources = []
            for result in results:
                resource_id = result[0]
                resource = self.load_resource(resource_id)
                if resource:
                    resources.append(resource)
            
            return resources
    
    def get_resources_by_rarity(self, rarity: ResourceRarity) -> List[Resource]:
        """
        Get all resources of a specific rarity.
        
        Args:
            rarity: The rarity level to search for
            
        Returns:
            List[Resource]: List of resources with the specified rarity
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.resources_table.c.id).where(
                self.resources_table.c.rarity == str(rarity.value)
            )
            results = session.execute(stmt).fetchall()
            
            resources = []
            for result in results:
                resource_id = result[0]
                resource = self.load_resource(resource_id)
                if resource:
                    resources.append(resource)
            
            return resources
    
    def get_resources_paginated(self, page: int, page_size: int) -> List[Resource]:
        """
        Retrieve resources with pagination.
        
        Args:
            page: The page number (1-based index)
            page_size: The number of resources per page
            
        Returns:
            List[Resource]: A list of resources for the given page
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.resources_table.c.id).offset((page - 1) * page_size).limit(page_size)
            results = session.execute(stmt).fetchall()
            
            resources = []
            for result in results:
                resource_id = result[0]
                resource = self.load_resource(resource_id)
                if resource:
                    resources.append(resource)
            return resources