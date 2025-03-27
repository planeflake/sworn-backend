# app/game_state/managers/task_manager.py
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.tasks import Tasks, TaskTypes
from app.models.core import Characters, Worlds
from app.game_state.entities.task import Task

logger = logging.getLogger(__name__)

class TaskManager:
    """
    Manager class for task-related operations.
    Handles CRUD operations and state management for tasks.
    """
    
    def __init__(self, db: Session):
        """
        Initialize with a database session.
        
        Args:
            db (Session): SQLAlchemy database session
        """
        self.db = db
    
    async def create_task(self, 
                   title: str, 
                   description: str, 
                   task_type_code: str,
                   world_id: str,
                   location_id: Optional[str] = None,
                   target_id: Optional[str] = None,
                   difficulty: int = 1,
                   duration_minutes: int = 0,
                   requirements: Dict[str, Any] = None,
                   rewards: Dict[str, Any] = None,
                   task_data: Dict[str, Any] = None,
                   repeatable: bool = False) -> Optional[Task]:
        """
        Create a new task in the database and return a Task entity.
        
        Args:
            title: Task title
            description: Task description
            task_type_code: Type of task (must match a code in TaskTypes table)
            world_id: World this task belongs to
            location_id: Optional location ID where task takes place
            target_id: Optional ID of the target entity (trader, settlement, etc.)
            difficulty: Task difficulty (1-10)
            duration_minutes: Estimated time to complete in minutes
            requirements: Dict of requirements to complete the task
            rewards: Dict of rewards for completing the task
            task_data: Additional task-specific data
            repeatable: Whether the task can be repeated
            
        Returns:
            Task entity if created successfully, None otherwise
        """
        # Get the task type ID from the code
        task_type = self.db.query(TaskTypes).filter(TaskTypes.code == task_type_code).first()
        if not task_type:
            logger.error(f"Task type with code {task_type_code} not found")
            return None
        
        # Validate the world exists
        world = self.db.query(Worlds).filter(Worlds.world_id == world_id).first()
        if not world:
            logger.error(f"World with ID {world_id} not found")
            return None
        
        # Set default values for dictionaries
        if requirements is None:
            requirements = {}
        if rewards is None:
            rewards = {}
        if task_data is None:
            task_data = {}
            
        # Add base rewards from the task type
        if 'xp' not in rewards:
            rewards['xp'] = task_type.base_xp
        if 'gold' not in rewards and task_type.base_gold > 0:
            rewards['gold'] = task_type.base_gold
        
        # Create the task record
        try:
            task_id = str(uuid.uuid4())
            new_task = Tasks(
                task_id=task_id,
                title=title,
                description=description,
                task_type_id=task_type.task_type_id,
                world_id=world_id,
                location_id=location_id,
                target_id=target_id,
                difficulty=difficulty,
                duration_minutes=duration_minutes,
                requirements=requirements,
                rewards=rewards,
                task_data=task_data,
                repeatable=repeatable,
                status='available',
                is_active=True,
                created_at=datetime.utcnow()
            )
            
            self.db.add(new_task)
            self.db.commit()
            self.db.refresh(new_task)
            
            # Create and return a Task entity
            return await self.load_task(task_id)
            
        except Exception as e:
            logger.exception(f"Error creating task: {e}")
            self.db.rollback()
            return None
    
    async def load_task(self, task_id: str) -> Optional[Task]:
        """
        Load a task from the database into a Task entity.
        
        Args:
            task_id: ID of the task to load
            
        Returns:
            Task entity if found, None otherwise
        """
        try:
            task_record = self.db.query(Tasks).filter(Tasks.task_id == task_id).first()
            if not task_record:
                logger.warning(f"Task with ID {task_id} not found")
                return None
            
            # Get the task type
            task_type = self.db.query(TaskTypes).filter(
                TaskTypes.task_type_id == task_record.task_type_id
            ).first()
            
            # Create a Task entity
            task = Task(
                task_id=str(task_record.task_id),
                title=task_record.title,
                description=task_record.description,
                task_type_id=str(task_record.task_type_id),
                task_type_code=task_type.code if task_type else None,
                world_id=str(task_record.world_id),
                location_id=task_record.location_id,
                target_id=task_record.target_id,
                character_id=str(task_record.character_id) if task_record.character_id else None,
                status=task_record.status,
                progress=task_record.progress,
                created_at=task_record.created_at,
                start_time=task_record.start_time,
                deadline=task_record.deadline,
                completion_time=task_record.completion_time,
                requirements=task_record.requirements,
                rewards=task_record.rewards,
                task_data=task_record.task_data,
                difficulty=task_record.difficulty,
                duration_minutes=task_record.duration_minutes,
                repeatable=task_record.repeatable,
                is_active=task_record.is_active
            )
            
            return task
            
        except Exception as e:
            logger.exception(f"Error loading task: {e}")
            return None
    
    async def save_task(self, task: Task) -> bool:
        """
        Save changes to a Task entity back to the database.
        
        Args:
            task: Task entity to save
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            task_record = self.db.query(Tasks).filter(Tasks.task_id == task.task_id).first()
            if not task_record:
                logger.warning(f"Task with ID {task.task_id} not found for update")
                return False
            
            # Update fields from the entity
            task_record.title = task.title
            task_record.description = task.description
            task_record.location_id = task.location_id
            task_record.target_id = task.target_id
            task_record.character_id = task.character_id
            task_record.status = task.status
            task_record.progress = task.progress
            task_record.is_active = task.is_active
            task_record.start_time = task.start_time
            task_record.deadline = task.deadline
            task_record.completion_time = task.completion_time
            task_record.requirements = task.requirements
            task_record.rewards = task.rewards
            task_record.task_data = task.task_data
            task_record.difficulty = task.difficulty
            task_record.duration_minutes = task.duration_minutes
            task_record.repeatable = task.repeatable
            
            # Commit changes
            self.db.commit()
            return True
            
        except Exception as e:
            logger.exception(f"Error saving task: {e}")
            self.db.rollback()
            return False
    
    async def get_available_tasks(self, 
                           world_id: str, 
                           location_id: Optional[str] = None,
                           character_id: Optional[str] = None,
                           task_type_code: Optional[str] = None) -> List[Task]:
        """
        Get available tasks for a given world, optionally filtered by location, character, or type.
        
        Args:
            world_id: World to get tasks for
            location_id: Optional location to filter by
            character_id: Optional character to filter by (for character-specific tasks)
            task_type_code: Optional task type code to filter by
            
        Returns:
            List of available Task entities
        """
        try:
            # Start with base query - available and active tasks
            query = self.db.query(Tasks).filter(
                and_(
                    Tasks.world_id == world_id,
                    Tasks.status == 'available',
                    Tasks.is_active == True
                )
            )
            
            # Apply filters if provided
            if location_id:
                query = query.filter(Tasks.location_id == location_id)
                
            if character_id:
                # Tasks with no character_id (available to all) OR specifically for this character
                query = query.filter(
                    or_(
                        Tasks.character_id == None,
                        Tasks.character_id == character_id
                    )
                )
                
            if task_type_code:
                # Join with TaskTypes to filter by code
                task_type = self.db.query(TaskTypes).filter(TaskTypes.code == task_type_code).first()
                if task_type:
                    query = query.filter(Tasks.task_type_id == task_type.task_type_id)
            
            # Execute query and convert to Task entities
            task_records = query.all()
            tasks = []
            
            for record in task_records:
                task = await self.load_task(str(record.task_id))
                if task:
                    tasks.append(task)
            
            return tasks
            
        except Exception as e:
            logger.exception(f"Error getting available tasks: {e}")
            return []
    
    async def get_character_tasks(self, character_id: str, status: Optional[str] = None) -> List[Task]:
        """
        Get tasks assigned to a specific character, optionally filtered by status.
        
        Args:
            character_id: Character to get tasks for
            status: Optional status to filter by
            
        Returns:
            List of Task entities assigned to the character
        """
        try:
            # Start with base query - tasks assigned to this character
            query = self.db.query(Tasks).filter(Tasks.character_id == character_id)
            
            # Apply status filter if provided
            if status:
                query = query.filter(Tasks.status == status)
            
            # Execute query and convert to Task entities
            task_records = query.all()
            tasks = []
            
            for record in task_records:
                task = await self.load_task(str(record.task_id))
                if task:
                    tasks.append(task)
            
            return tasks
            
        except Exception as e:
            logger.exception(f"Error getting character tasks: {e}")
            return []
    
    async def accept_task(self, task_id: str, character_id: str) -> Optional[Task]:
        """
        Assign a task to a character and mark it as accepted.
        
        Args:
            task_id: ID of the task to accept
            character_id: ID of the character accepting the task
            
        Returns:
            Updated Task entity if successful, None otherwise
        """
        try:
            # Check if the task exists and is available
            task_record = self.db.query(Tasks).filter(
                Tasks.task_id == task_id,
                Tasks.status == 'available',
                Tasks.is_active == True
            ).first()
            
            if not task_record:
                logger.warning(f"Task {task_id} not found or not available")
                return None
            
            # Check if the character exists
            character = self.db.query(Characters).filter(Characters.character_id == character_id).first()
            if not character:
                logger.warning(f"Character {character_id} not found")
                return None
            
            # Update the task record
            task_record.character_id = character_id
            task_record.status = 'accepted'
            task_record.start_time = datetime.utcnow()
            
            self.db.commit()
            
            # Reload and return the updated task
            return await self.load_task(task_id)
            
        except Exception as e:
            logger.exception(f"Error accepting task: {e}")
            self.db.rollback()
            return None
    
    async def complete_task(self, task_id: str, character_id: str) -> Dict[str, Any]:
        """
        Mark a task as completed by a character and process rewards.
        
        Args:
            task_id: ID of the task to complete
            character_id: ID of the character completing the task
            
        Returns:
            Dictionary with completion results and rewards
        """
        try:
            # Check if the task exists and is assigned to this character
            task_record = self.db.query(Tasks).filter(
                Tasks.task_id == task_id,
                Tasks.character_id == character_id,
                Tasks.status.in_(['accepted', 'in_progress']),
                Tasks.is_active == True
            ).first()
            
            if not task_record:
                logger.warning(f"Task {task_id} not found, not assigned to character {character_id}, or not in progress")
                return {
                    "status": "error",
                    "message": "Task not found or not assigned to your character",
                    "task_id": task_id,
                    "rewards": {}
                }
            
            # Get the rewards from the task
            rewards = task_record.rewards or {}
            
            # TODO: Process rewards - give items, XP, gold, etc. to the character
            # This would involve updating the character's inventory, XP, etc.
            # For now, we'll just return the rewards
            
            # Update the task record
            task_record.status = 'completed'
            task_record.progress = 100.0
            task_record.completion_time = datetime.utcnow()
            
            self.db.commit()
            
            return {
                "status": "success",
                "message": "Task completed successfully",
                "task_id": task_id,
                "rewards": rewards,
                "xp_gained": rewards.get("xp", 0)
            }
            
        except Exception as e:
            logger.exception(f"Error completing task: {e}")
            self.db.rollback()
            return {
                "status": "error",
                "message": f"Error completing task: {str(e)}",
                "task_id": task_id,
                "rewards": {}
            }
    
    async def fail_task(self, task_id: str, reason: str = "Failed to complete") -> bool:
        """
        Mark a task as failed.
        
        Args:
            task_id: ID of the task to fail
            reason: Reason for failure
            
        Returns:
            True if marked as failed successfully, False otherwise
        """
        try:
            task_record = self.db.query(Tasks).filter(Tasks.task_id == task_id).first()
            if not task_record:
                logger.warning(f"Task {task_id} not found")
                return False
            
            task_record.status = 'failed'
            task_record.completion_time = datetime.utcnow()
            task_record.task_data = {
                **task_record.task_data,
                "failure_reason": reason
            }
            
            self.db.commit()
            return True
            
        except Exception as e:
            logger.exception(f"Error failing task: {e}")
            self.db.rollback()
            return False
    
    async def get_tasks_by_target(self, target_id: str, status: Optional[str] = None) -> List[Task]:
        """
        Get tasks associated with a specific target entity (e.g., a trader).
        
        Args:
            target_id: ID of the target entity
            status: Optional status to filter by
            
        Returns:
            List of Task entities targeting the entity
        """
        try:
            # Start with base query - tasks targeting this entity
            query = self.db.query(Tasks).filter(Tasks.target_id == target_id)
            
            # Apply status filter if provided
            if status:
                query = query.filter(Tasks.status == status)
            
            # Execute query and convert to Task entities
            task_records = query.all()
            tasks = []
            
            for record in task_records:
                task = await self.load_task(str(record.task_id))
                if task:
                    tasks.append(task)
            
            return tasks
            
        except Exception as e:
            logger.exception(f"Error getting tasks by target: {e}")
            return []