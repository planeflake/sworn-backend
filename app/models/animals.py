from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ARRAY, Boolean
from sqlalchemy.dialects.postgresql import JSONB, UUID
from database.connection import Base
from sqlalchemy.sql import func
import uuid

class Animal(Base):
    """
    Animal configuration for the game world.
    Defines characteristics of different wildlife types.
    """
    __tablename__ = 'animal'
    
    animal_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(30), nullable=False, unique=True, index=True)
    can_be_ridden = Column(Boolean, nullable=False, default=False)
    can_be_adopted = Column(Boolean, nullable=False, default=False)
    description = Column(Text, nullable=False)
    base_movement = Column(Float, nullable=False, default=1.0)
    actions = Column(JSONB, nullable=False, default=dict)
    danger_level_base = Column(Integer, nullable=False, default=1)
    food_types = Column(JSONB, nullable=False, default=dict)
    natural_enemies = Column(ARRAY(UUID(as_uuid=True)), nullable=False, default=list)
    fears = Column(String(255), nullable=True)
    likes = Column(String(255), nullable=True)
    dislikes = Column(String(255), nullable=True)
    health = Column(Integer, nullable=False, default=100)
    status_effects = Column(JSONB, nullable=False, default=list)
    inventory = Column(JSONB, nullable=False, default=list)
    
    # New ecological properties for predator-prey dynamics
    ecological_role = Column(String(20), nullable=False, default='prey')  # 'predator', 'prey', or 'omnivore'
    size = Column(String(10), nullable=False, default='medium')            # e.g., 'small', 'medium', 'large'
    reproduction_rate = Column(Float, nullable=False, default=1.0)          # Rate of reproduction or population growth factor
    attack_power = Column(Integer, nullable=False, default=5)               # Basic damage value for predator interactions

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<Animal(animal_id={self.animal_id}, name='{self.name}', role='{self.ecological_role}')>"
