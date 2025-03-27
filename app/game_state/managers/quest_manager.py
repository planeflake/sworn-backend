# app/game_state/managers/quest_manager.py

import json
import uuid
import logging
import time
from typing import List, Dict, Optional, Any, Union
from sqlalchemy import Column, String, Text, Table, MetaData
from sqlalchemy import select, insert, update, delete
from sqlalchemy.orm import Session
from database.connection import get_db
from app.game_state.entities.quest import Quest

logger = logging.getLogger(__name__)

class QuestManager:
    """
    Manager for Quest entities that handles persistence and lifecycle.
    
    Responsible for:
    1. Loading quests from the database
    2. Saving quests to the database
    3. Creating new quests
    4. Maintaining a cache of loaded quests
    5. Providing query methods for finding quests
    """
    
    def __init__(self):
        """Initialize the QuestManager."""
        # Cache of loaded quests
        self.quests = {}  # Dictionary to store loaded quests by ID
        
        # Set up database metadata
        self._setup_db_metadata()
        
        logger.info(f"{self.__class__.__name__} initialized")
    
    def _setup_db_metadata(self):
        """Set up SQLAlchemy metadata for quests table."""
        self.metadata = MetaData()
        self.quests_table = Table(
            'quests', 
            self.metadata,
            Column('id', String(36), primary_key=True),
            Column('name', String(100)),
            Column('type', String(50)),
            Column('status', String(20)),
            Column('area', String(36)),
            Column('settlement', String(36)),
            Column('data', Text)
        )
    
    def create_quest(self, name: str, description: str, type: str, area: str, 
                    difficulty: int = 1, rewards: Optional[Dict[str, Any]] = None) -> Quest:
        """
        Create a new quest.
        
        Args:
            name: The quest's name
            description: The quest's description
            type: Type of quest (e.g., "trader_stranded", "monster_sighted")
            area: Area ID where the quest takes place
            difficulty: Quest difficulty (1-5 scale)
            rewards: Optional rewards dictionary
            
        Returns:
            Quest: The newly created quest
        """
        # Create a new quest instance
        quest = Quest(name, description, type, area, difficulty, rewards)
        
        # Add to cache
        self.quests[quest.id] = quest
        
        # Save to database
        self.save_quest(quest)
        
        logger.info(f"Created new quest: {name} (ID: {quest.id})")
        return quest
    
    def get_player_quests(self, player_id: str) -> List[Quest]:
        """
        Get all quests assigned to a player.
        
        Args:
            player_id: The ID of the player
            
        Returns:
            List[Quest]: List of quests assigned to the player
        """
        return [quest for quest in self.quests.values() 
                if quest.get_property("assigned_player") == player_id]

    def load_quest(self, quest_id: str) -> Optional[Quest]:
        """
        Load a quest from the database or cache.
        
        Args:
            quest_id: The ID of the quest to load
            
        Returns:
            Quest: The loaded quest, or None if not found
        """
        # Check if already loaded in cache
        if quest_id in self.quests:
            return self.quests[quest_id]
        
        # Load from database
        db = get_db()
        with Session(db) as session:
            stmt = select(self.quests_table).where(
                self.quests_table.c.id == quest_id
            )
            result = session.execute(stmt).first()
            
            if result is None:
                logger.warning(f"Quest not found: {quest_id}")
                return None
            
            # Deserialize quest data
            try:
                quest_data = json.loads(result.data)
                
                # Create a quest from the data
                name = quest_data.get("name", "Unknown Quest")
                description = quest_data.get("description", "")
                type = quest_data.get("type", "generic")
                area = quest_data.get("area", "")
                difficulty = quest_data.get("difficulty", 1)
                rewards = quest_data.get("rewards", {})
                
                # Create the quest with the existing ID
                quest = Quest(name, description, type, area, difficulty, rewards)
                quest.id = quest_id
                quest.status = quest_data.get("status", "inactive")
                quest.objectives = quest_data.get("objectives", [])
                quest.prerequisites = quest_data.get("prerequisites", [])
                quest.settlement = quest_data.get("settlement")
                quest.quest_giver = quest_data.get("quest_giver")
                quest._properties = quest_data.get("properties", {})
                
                # Cache the quest
                self.quests[quest_id] = quest
                
                logger.info(f"Loaded quest: {quest.name} (ID: {quest_id})")
                return quest
                
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Error deserializing quest {quest_id}: {e}")
                return None
    
    def save_quest(self, quest: Quest) -> bool:
        """
        Save a quest to the database.
        
        Args:
            quest: The quest to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Skip if no changes to save
        if not quest.is_dirty:
            return True
        
        # Convert quest to JSON
        try:
            quest_dict = {
                "id": quest.id,
                "name": quest.name,
                "description": quest.description,
                "type": quest.type,
                "area": quest.area,
                "difficulty": quest.difficulty,
                "rewards": quest.rewards,
                "status": quest.status,
                "objectives": quest.objectives,
                "prerequisites": quest.prerequisites,
                "settlement": quest.settlement,
                "quest_giver": quest.quest_giver,
                "properties": quest._properties
            }
            quest_data = json.dumps(quest_dict)
            
            # Save to database
            db = get_db()
            with Session(db) as session:
                try:
                    # Check if quest already exists
                    stmt = select(self.quests_table).where(
                        self.quests_table.c.id == quest.id
                    )
                    exists = session.execute(stmt).first() is not None
                    
                    if exists:
                        # Update existing quest
                        stmt = update(self.quests_table).where(
                            self.quests_table.c.id == quest.id
                        ).values(
                            name=quest.name,
                            type=quest.type,
                            status=quest.status,
                            area=quest.area,
                            settlement=quest.settlement,
                            data=quest_data
                        )
                        session.execute(stmt)
                    else:
                        # Insert new quest
                        stmt = insert(self.quests_table).values(
                            id=quest.id,
                            name=quest.name,
                            type=quest.type,
                            status=quest.status,
                            area=quest.area,
                            settlement=quest.settlement,
                            data=quest_data
                        )
                        session.execute(stmt)
                    
                    session.commit()
                    
                    # Mark quest as clean (no unsaved changes)
                    quest.clean()
                    
                    logger.info(f"Saved quest: {quest.name} (ID: {quest.id})")
                    return True
                    
                except Exception as e:
                    session.rollback()
                    logger.error(f"Failed to save quest {quest.id}: {str(e)}")
                    return False
        
        except Exception as e:
            logger.error(f"Error serializing quest {quest.id}: {str(e)}")
            return False
    
    def cancel_quest(self, quest_id: str) -> bool:
        """
        Cancel a quest.
        
        Args:
            quest_id: The ID of the quest to cancel
            
        Returns:
            bool: True if successful, False otherwise
        """
        quest = self.load_quest(quest_id)
        if not quest:
            logger.warning(f"Cannot cancel quest: quest not found: {quest_id}")
            return False
        
        if quest.complete("canceled"):
            return self.save_quest(quest)
        return False

    def delete_quest(self, quest_id: str) -> bool:
        """
        Delete a quest from the database.
        
        Args:
            quest_id: The ID of the quest to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Remove from cache if present
        if quest_id in self.quests:
            del self.quests[quest_id]
        
        # Delete from database
        db = get_db()
        with Session(db) as session:
            try:
                stmt = delete(self.quests_table).where(
                    self.quests_table.c.id == quest_id
                )
                session.execute(stmt)
                session.commit()
                
                logger.info(f"Deleted quest: {quest_id}")
                return True
                
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to delete quest {quest_id}: {str(e)}")
                return False
    
    def get_all_quests(self) -> List[Quest]:
        """
        Get all quests from the database.
        
        Returns:
            List[Quest]: List of all quests
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.quests_table.c.id)
            results = session.execute(stmt).fetchall()
            
            quests = []
            for result in results:
                quest_id = result[0]
                quest = self.load_quest(quest_id)
                if quest:
                    quests.append(quest)
            
            return quests
    
    def get_quests_in_area(self, area_id: str) -> List[Quest]:
        """
        Get all quests in a specific area.
        
        Args:
            area_id: The area ID
            
        Returns:
            List[Quest]: List of quests in the area
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.quests_table.c.id).where(
                self.quests_table.c.area == area_id
            )
            results = session.execute(stmt).fetchall()
            
            quests = []
            for result in results:
                quest_id = result[0]
                quest = self.load_quest(quest_id)
                if quest:
                    quests.append(quest)
            
            return quests
    
    def get_quests_in_settlement(self, settlement_id: str) -> List[Quest]:
        """
        Get all quests in a specific settlement.
        
        Args:
            settlement_id: The settlement ID
            
        Returns:
            List[Quest]: List of quests in the settlement
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.quests_table.c.id).where(
                self.quests_table.c.settlement == settlement_id
            )
            results = session.execute(stmt).fetchall()
            
            quests = []
            for result in results:
                quest_id = result[0]
                quest = self.load_quest(quest_id)
                if quest:
                    quests.append(quest)
            
            return quests
    
    def get_quest_by_name(self, name: str) -> Optional[Quest]:
        """
        Find a quest by name.
        
        Args:
            name: The name to search for
            
        Returns:
            Quest: The quest with the given name, or None if not found
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.quests_table.c.id).where(
                self.quests_table.c.name == name
            )
            result = session.execute(stmt).first()
            
            if result:
                return self.load_quest(result[0])
            
            return None
    
    def save_all_quests(self) -> bool:
        """
        Save all loaded quests to the database.
        
        Returns:
            bool: True if all saves were successful
        """
        success = True
        for quest in self.quests.values():
            if quest.is_dirty:
                if not self.save_quest(quest):
                    success = False
        
        return success
    
    def get_quest_count(self) -> int:
        """
        Get the total number of quests.
        
        Returns:
            int: The total count of quests
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.quests_table)
            result = session.execute(stmt).all()
            return len(result)

    def update_quest(self, quest_id: str, **kwargs) -> Optional[Quest]:
        """
        Update a quest's attributes.
        
        Args:
            quest_id: The ID of the quest to update
            **kwargs: Key-value pairs of attributes to update
            
        Returns:
            Quest: The updated quest, or None if not found
        """
        quest = self.load_quest(quest_id)
        if not quest:
            logger.warning(f"Quest not found for update: {quest_id}")
            return None

        for key, value in kwargs.items():
            if hasattr(quest, key):
                setattr(quest, key, value)
            else:
                quest.set_property(key, value)
        
        if self.save_quest(quest):
            logger.info(f"Updated quest: {quest_id}")
            return quest
        return None

    def load_quests(self, quest_ids: List[str]) -> List[Quest]:
        """
        Load multiple quests from the database.
        
        Args:
            quest_ids: A list of quest IDs to load
            
        Returns:
            List[Quest]: A list of loaded quests
        """
        quests = []
        for quest_id in quest_ids:
            quest = self.load_quest(quest_id)
            if quest:
                quests.append(quest)
        return quests

    def clear_cache(self) -> None:
        """
        Clear the cache of loaded quests.
        """
        self.quests.clear()
        logger.info("Quest cache cleared")

    def refresh_cache(self, quest_id: str) -> Optional[Quest]:
        """
        Refresh a specific quest in the cache.
        
        Args:
            quest_id: The ID of the quest to refresh
            
        Returns:
            Quest: The refreshed quest, or None if not found
        """
        # Remove from cache if present
        if quest_id in self.quests:
            del self.quests[quest_id]
            
        # Reload from database
        return self.load_quest(quest_id)

    def get_quests_paginated(self, page: int, page_size: int) -> List[Quest]:
        """
        Retrieve quests with pagination.
        
        Args:
            page: The page number (1-based index)
            page_size: The number of quests per page
            
        Returns:
            List[Quest]: A list of quests for the given page
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.quests_table.c.id).offset((page - 1) * page_size).limit(page_size)
            results = session.execute(stmt).fetchall()
            
            quests = []
            for result in results:
                quest_id = result[0]
                quest = self.load_quest(quest_id)
                if quest:
                    quests.append(quest)
            return quests

    def get_quests_by_type(self, quest_type: str) -> List[Quest]:
        """
        Get all quests of a specific type.
        
        Args:
            quest_type: The type of quest to find
            
        Returns:
            List[Quest]: List of quests of the specified type
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.quests_table.c.id).where(
                self.quests_table.c.type == quest_type
            )
            results = session.execute(stmt).fetchall()
            
            quests = []
            for result in results:
                quest_id = result[0]
                quest = self.load_quest(quest_id)
                if quest:
                    quests.append(quest)
            
            return quests
            
    def get_quests_by_status(self, status: str) -> List[Quest]:
        """
        Get all quests with a specific status.
        
        Args:
            status: The status to filter by
            
        Returns:
            List[Quest]: List of quests with the specified status
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.quests_table.c.id).where(
                self.quests_table.c.status == status
            )
            results = session.execute(stmt).fetchall()
            
            quests = []
            for result in results:
                quest_id = result[0]
                quest = self.load_quest(quest_id)
                if quest:
                    quests.append(quest)
            
            return quests