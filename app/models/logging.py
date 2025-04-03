# app/models/logging.py
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.models.core import Base
import uuid
from datetime import datetime

class EntityActionLog(Base):
    """Table for logging entity actions including trader movements"""
    __tablename__ = 'entity_action_log'
    
    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Entity information
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    entity_type = Column(String(50), nullable=False)  # 'trader', 'player', 'npc', etc.
    entity_name = Column(String(255))
    
    # Action details
    action_type = Column(String(50), nullable=False)  # 'movement', 'trade', 'task', etc.
    action_subtype = Column(String(50))  # More specific action like 'depart', 'arrive', 'buy', 'sell', etc.
    
    # Locations
    from_location_id = Column(UUID(as_uuid=True))
    from_location_type = Column(String(50))  # 'settlement', 'area', etc.
    from_location_name = Column(String(255))
    
    to_location_id = Column(UUID(as_uuid=True))
    to_location_type = Column(String(50))
    to_location_name = Column(String(255))
    
    # Related entities
    related_entity_id = Column(UUID(as_uuid=True))  # Another entity involved in the action
    related_entity_type = Column(String(50))
    related_entity_name = Column(String(255))
    
    # Additional data
    details = Column(JSONB, default={})  # Flexible field for additional context
    
    # Tracking fields
    world_id = Column(UUID(as_uuid=True), nullable=False)
    game_day = Column(Integer)
    game_time = Column(String(50))