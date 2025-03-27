# app/game_state/entities/task.py
from typing import Dict, Optional, Any
from datetime import datetime

class Task:
    """
    Entity class representing a task in the game.
    Tasks can be assigned to players and completed to earn rewards.
    """
    
    def __init__(self, 
                task_id: str,
                title: str,
                description: str,
                task_type_id: str,
                task_type_code: Optional[str],
                world_id: str,
                location_id: Optional[str] = None,
                target_id: Optional[str] = None,
                character_id: Optional[str] = None,
                status: str = "available",
                progress: float = 0.0,
                created_at: Optional[datetime] = None,
                start_time: Optional[datetime] = None,
                deadline: Optional[datetime] = None,
                completion_time: Optional[datetime] = None,
                requirements: Optional[Dict[str, Any]] = None,
                rewards: Optional[Dict[str, Any]] = None,
                task_data: Optional[Dict[str, Any]] = None,
                difficulty: int = 1,
                duration_minutes: int = 0,
                repeatable: bool = False,
                is_active: bool = True):
        """
        Initialize a Task entity.
        
        Args:
            task_id: Unique identifier for the task
            title: Task title displayed to players
            description: Detailed description of the task
            task_type_id: ID of the task type
            task_type_code: Code identifier of the task type
            world_id: ID of the world this task belongs to
            location_id: Optional ID of the location where task takes place
            target_id: Optional ID of the target entity (e.g., trader)
            character_id: Optional ID of character assigned to the task
            status: Current status of the task (available, accepted, in_progress, completed, failed)
            progress: Progress toward completion (0-100)
            created_at: When the task was created
            start_time: When the task was accepted by a character
            deadline: Optional deadline for the task
            completion_time: When the task was completed or failed
            requirements: Dictionary of requirements to complete the task
            rewards: Dictionary of rewards for completing the task
            task_data: Additional task-specific data
            difficulty: Task difficulty level (1-10)
            duration_minutes: Estimated time to complete in minutes
            repeatable: Whether the task can be repeated after completion
            is_active: Whether the task is active in the game world
        """
        self.task_id = task_id
        self.title = title
        self.description = description
        self.task_type_id = task_type_id
        self.task_type_code = task_type_code
        self.world_id = world_id
        self.location_id = location_id
        self.target_id = target_id
        self.character_id = character_id
        self.status = status
        self.progress = progress
        self.created_at = created_at or datetime.utcnow()
        self.start_time = start_time
        self.deadline = deadline
        self.completion_time = completion_time
        self.requirements = requirements or {}
        self.rewards = rewards or {}
        self.task_data = task_data or {}
        self.difficulty = difficulty
        self.duration_minutes = duration_minutes
        self.repeatable = repeatable
        self.is_active = is_active
        
        # Cached property values
        self._properties = {}
    
    def accept(self, character_id: str) -> bool:
        """
        Mark the task as accepted by a character.
        
        Args:
            character_id: ID of the character accepting the task
            
        Returns:
            True if accepted successfully, False otherwise
        """
        if self.status != "available" or not self.is_active:
            return False
        
        self.character_id = character_id
        self.status = "accepted"
        self.start_time = datetime.utcnow()
        return True
    
    def update_progress(self, progress: float) -> None:
        """
        Update the task progress.
        
        Args:
            progress: New progress value (0-100)
        """
        self.progress = max(0, min(100, progress))
        
        # If progress reaches 100, automatically mark as completed
        if self.progress >= 100 and self.status == "in_progress":
            self.complete()
    
    def complete(self) -> None:
        """Mark the task as completed."""
        if self.status in ["accepted", "in_progress"]:
            self.status = "completed"
            self.progress = 100
            self.completion_time = datetime.utcnow()
    
    def fail(self, reason: Optional[str] = None) -> None:
        """
        Mark the task as failed.
        
        Args:
            reason: Optional reason for failure
        """
        if self.status in ["accepted", "in_progress"]:
            self.status = "failed"
            self.completion_time = datetime.utcnow()
            
            if reason:
                self.task_data["failure_reason"] = reason
    
    def get_property(self, property_name: str, default_value: Any = None) -> Any:
        """
        Get a property value from the task.
        
        Args:
            property_name: Name of the property to get
            default_value: Default value if property doesn't exist
            
        Returns:
            Property value or default
        """
        # First check if property exists as an attribute
        if hasattr(self, property_name):
            return getattr(self, property_name)
            
        # Next check in the task data
        if property_name in self.task_data:
            return self.task_data[property_name]
            
        # Finally check cached properties
        if property_name in self._properties:
            return self._properties[property_name]
            
        return default_value
    
    def set_property(self, property_name: str, value: Any) -> None:
        """
        Set a property value on the task.
        
        Args:
            property_name: Name of the property to set
            value: Value to set
        """
        # If it's a core attribute, set it directly
        if hasattr(self, property_name):
            setattr(self, property_name, value)
        else:
            # Otherwise store in task_data
            self.task_data[property_name] = value
            # Also cache in properties
            self._properties[property_name] = value
    
    def is_available(self) -> bool:
        """Check if the task is available to be accepted."""
        return self.status == "available" and self.is_active
    
    def is_completed(self) -> bool:
        """Check if the task is completed."""
        return self.status == "completed"
    
    def is_failed(self) -> bool:
        """Check if the task is failed."""
        return self.status == "failed"
    
    def is_in_progress(self) -> bool:
        """Check if the task is in progress."""
        return self.status in ["accepted", "in_progress"]
    
    def is_expired(self) -> bool:
        """Check if the task has expired."""
        if not self.deadline:
            return False
        return datetime.utcnow() > self.deadline
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the task to a dictionary.
        
        Returns:
            Dictionary representation of the task
        """
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "task_type_id": self.task_type_id,
            "task_type_code": self.task_type_code,
            "world_id": self.world_id,
            "location_id": self.location_id,
            "target_id": self.target_id,
            "character_id": self.character_id,
            "status": self.status,
            "progress": self.progress,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "completion_time": self.completion_time.isoformat() if self.completion_time else None,
            "requirements": self.requirements,
            "rewards": self.rewards,
            "task_data": self.task_data,
            "difficulty": self.difficulty,
            "duration_minutes": self.duration_minutes,
            "repeatable": self.repeatable,
            "is_active": self.is_active
        }