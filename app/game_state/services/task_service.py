# app/game_state/services/task_service.py
import logging
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime

from sqlalchemy.orm import Session

from app.game_state.managers.task_manager import TaskManager
from app.game_state.entities.task import Task
from app.models.tasks import TaskTypes, Tasks

logger = logging.getLogger(__name__)

class TaskService:
    """
    Service layer that orchestrates task-related operations.
    Acts as a bridge between the API routes, Celery workers, and the TaskManager.
    """
    
    def __init__(self, db: Session):
        """
        Initialize with a database session.
        
        Args:
            db (Session): SQLAlchemy database session
        """
        self.db = db
        self.task_manager = TaskManager(db)
    
    async def create_task(self,
                   task_type: str,
                   title: str,
                   description: str,
                   world_id: str,
                   location_id: Optional[str] = None,
                   target_id: Optional[str] = None,
                   requirements: Dict[str, Any] = None,
                   rewards: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create a new task.
        
        Args:
            task_type: Type of task (must match a TaskTypeEnum value)
            title: Task title
            description: Task description
            world_id: World this task belongs to
            location_id: Optional location ID where task takes place
            target_id: Optional ID of the target entity (trader, settlement, etc.)
            requirements: Dict of requirements to complete the task
            rewards: Dict of rewards for completing the task
            
        Returns:
            Dictionary with task creation result
        """
        try:
            # Map task_type to task_type_code (snake_case)
            task_type_code = task_type.lower()
            
            # Set default values
            if requirements is None:
                requirements = {}
            if rewards is None:
                rewards = {}
                
            # Set task difficulty based on rewards or other factors
            # For now, simple scaling based on gold reward
            gold_reward = rewards.get('gold', 0)
            difficulty = max(1, min(10, 1 + gold_reward // 10))
            
            # Estimate duration in minutes based on difficulty
            duration_minutes = difficulty * 5  # Simple 5 min per difficulty level
            
            # Create task data specific to the task type
            task_data = {
                "task_type_display": task_type.replace('_', ' ').title()
            }
            
            # Create the task using the manager
            task = await self.task_manager.create_task(
                title=title,
                description=description,
                task_type_code=task_type_code,
                world_id=world_id,
                location_id=location_id,
                target_id=target_id,
                difficulty=difficulty,
                duration_minutes=duration_minutes,
                requirements=requirements,
                rewards=rewards,
                task_data=task_data
            )
            
            if not task:
                return {
                    "status": "error",
                    "message": "Failed to create task",
                    "task_id": None
                }
            
            return {
                "status": "success",
                "message": "Task created successfully",
                "task_id": task.task_id,
                "task": task.to_dict()
            }
            
        except Exception as e:
            logger.exception(f"Error creating task: {e}")
            return {
                "status": "error",
                "message": f"Error creating task: {str(e)}",
                "task_id": None
            }
    
    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a task by ID.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Dictionary representation of the task or None if not found
        """
        task = await self.task_manager.load_task(task_id)
        if not task:
            return None
            
        return task.to_dict()
    
    async def get_available_tasks(self, 
                           world_id: str,
                           location_id: Optional[str] = None,
                           character_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get available tasks for a given world, optionally filtered by location or character.
        
        Args:
            world_id: World to get tasks for
            location_id: Optional location to filter by
            character_id: Optional character to filter by
            
        Returns:
            List of available tasks as dictionaries
        """
        tasks = await self.task_manager.get_available_tasks(
            world_id=world_id,
            location_id=location_id,
            character_id=character_id
        )
        
        return [task.to_dict() for task in tasks]
    
    async def get_character_tasks(self, character_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get tasks assigned to a specific character.
        
        Args:
            character_id: Character to get tasks for
            status: Optional status to filter by
            
        Returns:
            List of tasks assigned to the character
        """
        tasks = await self.task_manager.get_character_tasks(
            character_id=character_id,
            status=status
        )
        
        return [task.to_dict() for task in tasks]
    
    async def accept_task(self, task_id: str, character_id: str) -> Dict[str, Any]:
        """
        Assign a task to a character.
        
        Args:
            task_id: ID of the task to accept
            character_id: ID of the character accepting the task
            
        Returns:
            Dictionary with result of task acceptance
        """
        task = await self.task_manager.accept_task(task_id, character_id)
        
        if not task:
            return {
                "status": "error",
                "message": "Failed to accept task. It may already be assigned or unavailable.",
                "task_id": task_id
            }
            
        return {
            "status": "success",
            "message": "Task accepted successfully",
            "task_id": task_id,
            "task": task.to_dict()
        }
    
    async def complete_task(self, task_id: str, character_id: str) -> Dict[str, Any]:
        """
        Mark a task as completed by a character and process rewards.
        
        Args:
            task_id: ID of the task to complete
            character_id: ID of the character completing the task
            
        Returns:
            Dictionary with completion results
        """
        return await self.task_manager.complete_task(task_id, character_id)
    
    async def fail_task(self, task_id: str, reason: str = "Failed to complete") -> Dict[str, Any]:
        """
        Mark a task as failed.
        
        Args:
            task_id: ID of the task to fail
            reason: Reason for failure
            
        Returns:
            Dictionary with result of task failure
        """
        result = await self.task_manager.fail_task(task_id, reason)
        
        if not result:
            return {
                "status": "error",
                "message": "Failed to mark task as failed",
                "task_id": task_id
            }
            
        return {
            "status": "success",
            "message": "Task marked as failed",
            "task_id": task_id,
            "reason": reason
        }
    
    async def get_trader_tasks(self, trader_id: str) -> List[Dict[str, Any]]:
        """
        Get tasks related to a specific trader.
        
        Args:
            trader_id: ID of the trader
            
        Returns:
            List of tasks targeting the trader
        """
        tasks = await self.task_manager.get_tasks_by_target(trader_id)
        return [task.to_dict() for task in tasks]
    
    async def check_expired_tasks(self) -> Dict[str, Any]:
        """
        Check for expired tasks and mark them as failed.
        This would typically be called by a Celery worker on a schedule.
        
        Returns:
            Dictionary with results of expired task check
        """
        # TODO: Implement logic to check for and expire tasks past their deadline
        # This is a placeholder implementation
        return {
            "status": "success",
            "message": "Expired task check not yet implemented",
            "expired_count": 0
        }