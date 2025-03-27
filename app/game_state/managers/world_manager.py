# app/game_state/managers/world_manager.py (extension)

# Template for creating manager classes in the game state architecture
# Copy this file to app/game_state/managers/ and customize for each world type

import json
import uuid
import logging
from typing import List, Dict, Optional, Any, Type, Union
from sqlalchemy import Column, String, Text, Table, MetaData
from sqlalchemy import select, insert, update, delete
from sqlalchemy.orm import Session
from database.connection import get_db
#from app.models.template import Template  # Replace with your actual model class

# Import your world class
from app.game_state.entities.world import World

logger = logging.getLogger(__name__)

class WorldManager:
    """
    Template for world managers that handle persistence and lifecycle.
    
    Managers are responsible for:
    1. Loading entities from the database
    2. Saving entities to the database
    3. Creating new entities
    4. Maintaining a cache of loaded entities
    5. Providing query methods for finding entities
    
    Each world type should have its own manager class.
    """
    
    def __init__(self):
        """Initialize the manager."""
        # Cache of loaded entities
        self.entities = {}  # Dictionary to store loaded entities by ID
        
        # Set up database metadata
        self._setup_db_metadata()
        
        logger.info(f"{self.__class__.__name__} initialized")
    
    def _setup_db_metadata(self):
        """Set up SQLAlchemy metadata for the world table."""
        self.metadata = MetaData()
        
        # Define the table structure for this world type
        # Modify these columns to match your database schema
        self.world_table = Table(
            'entities',  # Replace with your actual table name
            self.metadata,
            Column('world_id', String(36), primary_key=True),
            Column('name', String(100)),
            Column('location_id', String(36)),
            Column('data', Text)  # JSON data column
        )
    
    def create_world(self, name: str, description: Optional[str] = None) -> World:
        """
        Create a new world with a unique ID.
        
        Args:
            name (str): The world's name
            description (str, optional): Optional description
            
        Returns:
            world: The newly created world
        """
        # Generate a unique ID
        world_id = str(uuid.uuid4())
        
        # Create a new world instance
        # Replace with your actual world class
        # world = worldTemplate(world_id)
        world = None  # Replace with your actual world instantiation
        
        # Set basic information
        world.set_basic_info(name, description or f"An world named {name}")
        
        # Add to cache
        self.entities[world_id] = world
        
        # Save to database
        self.save_world(world)
        
        logger.info(f"Created new world: {name} (ID: {world_id})")
        return world
    
    def load_world(self, world_id: str) -> Optional[World]:
        """
        Load an world from the database or cache.
        
        Args:
            world_id (str): The ID of the world to load
            
        Returns:
            world: The loaded world, or None if not found
        """
        # Check if already loaded in cache
        if world_id in self.entities:
            return self.entities[world_id]
        
        # Load from database
        db = get_db()
        with Session(db) as session:
            stmt = select(self.world_table).where(
                self.world_table.c.world_id == world_id
            )
            result = session.execute(stmt).first()
            
            if result is None:
                logger.warning(f"world not found: {world_id}")
                return None
            
            # Deserialize world data
            try:
                world_data = json.loads(result.data)
                # Replace with your actual world class
                # world = worldTemplate.from_dict(world_data)
                world = None  # Replace with your actual deserialization
                
                # Cache the world
                self.entities[world_id] = world
                
                logger.info(f"Loaded world: {world.name} (ID: {world_id})")
                return world
                
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Error deserializing world {world_id}: {e}")
                return None
    
    def save_world(self, world: World) -> bool:
        """
        Save an world to the database.
        
        Args:
            world (world): The world to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Skip if no changes to save
        if not world.is_dirty():
            return True
        
        # Convert world to JSON
        try:
            world_dict = world.to_dict()
            world_data = json.dumps(world_dict)
            
            # Save to database
            db = get_db()
            with Session(db) as session:
                try:
                    # Check if world already exists
                    stmt = select(self.world_table).where(
                        self.world_table.c.world_id == world.world_id
                    )
                    exists = session.execute(stmt).first() is not None
                    
                    if exists:
                        # Update existing world
                        stmt = update(self.world_table).where(
                            self.world_table.c.world_id == world.world_id
                        ).values(
                            name=world.name,
                            location_id=world.location_id,
                            data=world_data
                        )
                        session.execute(stmt)
                    else:
                        # Insert new world
                        stmt = insert(self.world_table).values(
                            world_id=world.world_id,
                            name=world.name,
                            location_id=world.location_id,
                            data=world_data
                        )
                        session.execute(stmt)
                    
                    session.commit()
                    
                    # Mark world as clean (no unsaved changes)
                    world.mark_clean()
                    
                    logger.info(f"Saved world: {world.name} (ID: {world.world_id})")
                    return True
                    
                except Exception as e:
                    session.rollback()
                    logger.error(f"Failed to save world {world.world_id}: {str(e)}")
                    return False
        
        except Exception as e:
            logger.error(f"Error serializing world {world.world_id}: {str(e)}")
            return False
    
    def delete_world(self, world_id: str) -> bool:
        """
        Delete an world from the database.
        
        Args:
            world_id (str): The ID of the world to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Remove from cache if present
        if world_id in self.entities:
            del self.entities[world_id]
        
        # Delete from database
        db = get_db()
        with Session(db) as session:
            try:
                stmt = delete(self.world_table).where(
                    self.world_table.c.world_id == world_id
                )
                session.execute(stmt)
                session.commit()
                
                logger.info(f"Deleted world: {world_id}")
                return True
                
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to delete world {world_id}: {str(e)}")
                return False
    
    def get_all_entities(self) -> List[World]:
        """
        Get all entities from the database.
        
        Returns:
            List[world]: List of all entities
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.world_table.c.world_id)
            results = session.execute(stmt).fetchall()
            
            entities = []
            for result in results:
                world_id = result[0]
                world = self.load_world(world_id)
                if world:
                    entities.append(world)
            
            return entities
    
    def get_entities_at_location(self, location_id: str) -> List[World]:
        """
        Get all entities at a specific location.
        
        Args:
            location_id (str): The location ID
            
        Returns:
            List[world]: List of entities at the location
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.world_table.c.world_id).where(
                self.world_table.c.location_id == location_id
            )
            results = session.execute(stmt).fetchall()
            
            entities = []
            for result in results:
                world_id = result[0]
                world = self.load_world(world_id)
                if world:
                    entities.append(world)
            
            return entities
    
    def get_world_by_name(self, name: str) -> Optional[World]:
        """
        Find an world by name.
        
        Args:
            name (str): The name to search for
            
        Returns:
            world: The world with the given name, or None if not found
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.world_table.c.world_id).where(
                self.world_table.c.name == name
            )
            result = session.execute(stmt).first()
            
            if result:
                return self.load_world(result[0])
            
            return None
    
    def update_world_location(self, world_id: str, location_id: str) -> bool:
        """
        Update an world's location.
        
        Args:
            world_id (str): The world ID
            location_id (str): The new location ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        world = self.load_world(world_id)
        if not world:
            logger.warning(f"Cannot update location: world not found: {world_id}")
            return False
        
        world.set_location(location_id)
        return self.save_world(world)
    
    def set_theme(self, world_id: str, theme: str) -> bool:
        """
        Set the theme for an world.
        
        Args:
            world_id (str): The ID of the world
            theme (str): The theme to set
            
        Returns:
            bool: True if successful, False otherwise
        """
        world = self.load_world(world_id)
        if not world:
            logger.warning(f"Cannot set theme: world not found: {world_id}")
            return False
        
        world.set_theme(theme)
        return self.save_world(world)

    def change_theme(self, world_id: str, new_theme: str) -> bool:
        """
        Change the theme of a world.
        
        Args:
            world_id (str): The ID of the world
            new_theme (str): The new theme to set
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Load the world
        world = self.load_world(world_id)
        if not world:
            logger.warning(f"Cannot change theme: world not found: {world_id}")
            return False

        # Validate the new theme
        if new_theme not in world.themes:
            logger.warning(f"Cannot change theme: invalid theme: {new_theme}. Valid themes: {world.themes}")
            return False

        # Change the theme and save the world
        world.change_theme(new_theme)
        return self.save_world(world)

    def save_all_entities(self) -> bool:
        """
        Save all loaded entities to the database.
        
        Returns:
            bool: True if all saves were successful
        """
        success = True
        for world in self.entities.values():
            if world.is_dirty():
                if not self.save_world(world):
                    success = False
        
        return success
    
    def get_world_count(self) -> int:
        """
        Get the total number of entities.
        
        Returns:
            int: The total count of entities
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.world_table)
            result = session.execute(stmt).all()
            return len(result)

    ### Update Methods ###

    def update_world(self, world_id: str, **kwargs) -> Optional[World]:
        """
        Update an world's attributes.
        
        Args:
            world_id (str): The ID of the world to update
            **kwargs: Key-value pairs of attributes to update
            
        Returns:
            world: The updated world, or None if not found
        """
        world = self.load_world(world_id)
        if not world:
            logger.warning(f"world not found for update: {world_id}")
            return None

        for key, value in kwargs.items():
            if hasattr(world, key):
                setattr(world, key, value)
            else:
                logger.warning(f"Invalid attribute '{key}' for world update")
        
        if self.save_world(world):
            logger.info(f"Updated world: {world_id}")
            return world
        return None

    ### Bulk Operations ###

    def load_entities(self, world_ids: List[str]) -> List[World]:
        """
        Load multiple entities from the database.
        
        Args:
            world_ids (List[str]): A list of world IDs to load
            
        Returns:
            List[world]: A list of loaded entities
        """
        entities = []
        for world_id in world_ids:
            world = self.load_world(world_id)
            if world:
                entities.append(world)
        return entities

    ### Cache Management ###

    def clear_cache(self) -> None:
        """
        Clear the cache of loaded entities.
        """
        self.entities.clear()
        logger.info("Cache cleared")

    def refresh_cache(self, world_id: str) -> Optional[World]:
        """
        Refresh a specific world in the cache.
        
        Args:
            world_id (str): The ID of the world to refresh
            
        Returns:
            world: The refreshed world, or None if not found
        """
        world = self.load_world(world_id)
        if world:
            self.entities[world_id] = world
        return world

    ### Pagination ###

    def find_entities_paginated(self, page: int, page_size: int) -> List[World]:
        """
        Retrieve entities with pagination.
        
        Args:
            page (int): The page number (1-based index)
            page_size (int): The number of entities per page
            
        Returns:
            List[world]: A list of entities for the given page
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.world_table.c.world_id).offset((page - 1) * page_size).limit(page_size)
            results = session.execute(stmt).fetchall()
            
            entities = []
            for result in results:
                world_id = result[0]
                world = self.load_world(world_id)
                if world:
                    entities.append(world)
            return entities

    ### Soft Delete ###

    def soft_delete_world(self, world_id: str) -> bool:
        """
        Soft delete an world by marking it as inactive.
        
        Args:
            world_id (str): The ID of the world to soft delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        world = self.load_world(world_id)
        if not world:
            logger.warning(f"Attempted to soft delete non-existent world: {world_id}")
            return False
        
        world.is_active = False
        return self.save_world(world)

    ### Export/Import ###

    def export_entities(self, file_path: str) -> None:
        """
        Export all entities to a JSON file.
        
        Args:
            file_path (str): The file path to save the entities
        """
        with open(file_path, 'w') as file:
            json.dump([world.to_dict() for world in self.entities.values()], file)
        logger.info(f"Exported entities to {file_path}")

    def import_entities(self, file_path: str) -> None:
        """
        Import entities from a JSON file.
        
        Args:
            file_path (str): The file path to load the entities from
        """
        with open(file_path, 'r') as file:
            entities = json.load(file)
            for world_data in entities:
                # Replace with your actual world class instantiation
                # world = worldTemplate.from_dict(world_data)
                world = None  # Replace with actual deserialization
                self.save_world(world)
        logger.info(f"Imported entities from {file_path}")

    ### Audit Logging ###

    def log_world_changes(self, world_id: str, changes: Dict[str, Any]) -> None:
        """
        Log changes made to an world.
        
        Args:
            world_id (str): The ID of the world
            changes (Dict[str, Any]): A dictionary of changes
        """
        logger.info(f"Changes to world {world_id}: {changes}")
    
    def get_weather_modifiers(self, weather_type: str) -> Dict[str, Dict[str, float]]:
        """
        Get modifier values for different encounter types based on weather.
        
        Args:
            weather_type: Type of weather (clear, rain, storm, etc.)
            
        Returns:
            Dict mapping encounter types to their modifier values
        """
        # Default modifiers (centralized definition)
        weather_modifiers = {
            "clear": {
                "none": 1.2,
                "bandit_attack": 1.0,
                "wildlife_attack": 1.0,
                "natural_hazard": 0.5,
                "cargo_accident": 0.7
            },
            "rain": {
                "none": 0.9,
                "bandit_attack": 0.8,
                "wildlife_attack": 0.9,
                "natural_hazard": 1.5,
                "cargo_accident": 1.3
            },
            "storm": {
                "none": 0.6,
                "bandit_attack": 0.5,
                "wildlife_attack": 0.7,
                "natural_hazard": 2.5,
                "cargo_accident": 2.0
            },
            "fog": {
                "none": 0.8,
                "bandit_attack": 1.2,
                "ambush": 1.8,
                "wildlife_attack": 1.4
            },
            "snow": {
                "none": 0.7,
                "bandit_attack": 0.6,
                "wildlife_attack": 0.8,
                "natural_hazard": 2.0,
                "cargo_accident": 1.7
            }
        }
        
        # Return modifiers for requested weather or empty dict if not found
        return weather_modifiers.get(weather_type, {})
    
    def get_current_weather(self, location_id: str) -> str:
        """
        Get current weather at a location.
        
        Args:
            location_id: Location to check
            
        Returns:
            str: Current weather type
        """
        location_state = self.get_location_state(location_id)
        return location_state.get("weather", "clear")