# app/models/tasks.py
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.models.core import Base
import uuid
from datetime import datetime

class TaskTypes(Base):
    """Types of tasks that can be assigned to players"""
    __tablename__ = 'task_types'
    
    task_type_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), nullable=False, unique=True)  # e.g., 'trader_assistance'
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    base_xp = Column(Integer, default=10)  # Base XP reward
    base_gold = Column(Integer, default=0)  # Base gold reward
    icon = Column(String(100), nullable=True)  # UI icon reference
    color_hex = Column(String(7), nullable=True, default='#FFFFFF')  # UI color code
    
    tasks = relationship("Tasks", back_populates="task_type")

class Tasks(Base):
    """Tasks that can be assigned to and completed by players"""
    __tablename__ = 'tasks'
    
    task_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    
    # Associations
    task_type_id = Column(UUID(as_uuid=True), ForeignKey('task_types.task_type_id'), nullable=False)
    world_id = Column(UUID(as_uuid=True), ForeignKey('worlds.world_id'), nullable=False)
    character_id = Column(UUID(as_uuid=True), ForeignKey('characters.character_id'), nullable=True)  # If assigned to a character
    location_id = Column(String, nullable=True)  # Generic location reference (could be settlement, area, etc.)
    target_id = Column(String, nullable=True)  # ID of the entity this task references (trader, building, etc.)
    
    # Task state
    status = Column(String(20), nullable=False, default='available')  # available, accepted, in_progress, completed, failed
    is_active = Column(Boolean, default=True)
    progress = Column(Float, default=0.0)  # Progress from 0 to 100
    
    # Time tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    start_time = Column(DateTime, nullable=True)  # When the task was accepted
    deadline = Column(DateTime, nullable=True)  # Optional deadline
    completion_time = Column(DateTime, nullable=True)  # When task was completed or failed
    
    # Requirements and rewards - stored as JSON
    requirements = Column(JSONB, default={})
    rewards = Column(JSONB, default={})
    
    # Additional data for specific task types
    task_data = Column(JSONB, default={})
    
    # Relationships
    task_type = relationship("TaskTypes", back_populates="tasks")
    
    # Additional metadata
    difficulty = Column(Integer, default=1)  # 1-10 scale
    duration_minutes = Column(Integer, default=0)  # Estimated time to complete
    repeatable = Column(Boolean, default=False)  # Can this task be repeated?
