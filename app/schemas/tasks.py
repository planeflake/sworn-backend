# app/schemas/tasks.py
from pydantic import BaseModel, UUID4, Field, validator
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime

from app.schemas.base import TimeStampModel

class TaskTypeEnum(str, Enum):
    RESOURCE_GATHERING = "resource_gathering"
    BUILDING_CONSTRUCTION = "building_construction"
    EXPLORATION = "exploration"
    CRAFTING = "crafting"
    TRADING = "trading"
    TRADER_ASSISTANCE = "trader_assistance"

class TaskStatusEnum(str, Enum):
    AVAILABLE = "available"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskTypeBase(BaseModel):
    code: str = Field(..., min_length=3, max_length=50)
    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = None
    base_xp: int = 10
    base_gold: int = 0
    icon: Optional[str] = None
    color_hex: Optional[str] = "#FFFFFF"

class TaskTypeCreate(TaskTypeBase):
    pass

class TaskTypeResponse(TaskTypeBase):
    task_type_id: UUID4
    
    class Config:
        from_attributes = True

class TaskBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    description: str = Field(..., min_length=10)
    task_type_code: str  # Code reference instead of ID for ease of use
    location_id: Optional[str] = None
    target_id: Optional[str] = None
    difficulty: int = Field(1, ge=1, le=10)
    duration_minutes: int = 0
    requirements: Dict[str, Any] = Field(default_factory=dict)
    rewards: Dict[str, Any] = Field(default_factory=dict)
    task_data: Dict[str, Any] = Field(default_factory=dict)
    repeatable: bool = False

class TaskCreate(TaskBase):
    world_id: UUID4

class TaskUpdate(BaseModel):
    status: Optional[TaskStatusEnum] = None
    progress: Optional[float] = None
    character_id: Optional[UUID4] = None
    is_active: Optional[bool] = None
    
    @validator('progress')
    def progress_range(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError('Progress must be between 0 and 100')
        return v

class TaskResponse(TaskBase, TimeStampModel):
    task_id: UUID4
    world_id: UUID4
    task_type_id: UUID4
    status: TaskStatusEnum
    progress: float = 0.0
    character_id: Optional[UUID4] = None
    start_time: Optional[datetime] = None
    deadline: Optional[datetime] = None
    completion_time: Optional[datetime] = None
    is_active: bool = True
    
    class Config:
        from_attributes = True

class TaskListResponse(BaseModel):
    tasks: List[TaskResponse]
    count: int
    
    class Config:
        from_attributes = True

class TaskCompleteRequest(BaseModel):
    character_id: UUID4
    
class TaskAcceptRequest(BaseModel):
    character_id: UUID4

class TaskCompleteResponse(BaseModel):
    status: str
    message: str
    task_id: UUID4
    rewards: Dict[str, Any]
    xp_gained: int = 0