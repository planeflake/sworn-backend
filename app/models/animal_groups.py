from sqlalchemy import Column, String, Text, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from ..database.connection import Base
import uuid

class AnimalGroup(Base):
    """
    Database model for groups (herds) of animals.
    """
    __tablename__ = 'animal_groups'
    
    group_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    # Optionally, you can store a JSON string with additional data (such as member animal IDs)
    data = Column(JSON, nullable=False, default='{}')
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<AnimalGroup(group_id={self.group_id}, group_name='{self.group_name}')>"
