# models/biomes.py
from sqlalchemy import Column, Integer, String, Float, Text, JSON
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from database.connection import Base
import uuid

class Biomes(Base):
    """
    Biome configuration for the game world.
    Defines characteristics of different terrain types.
    """
    __tablename__ = 'biomes'
    
    biome_id = Column(Integer, primary_key=True)
    name = Column(String(30), nullable=False, unique=True)
    display_name = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    base_movement_modifier = Column(Float, nullable=False, default=1.0)
    danger_level_base = Column(Integer, nullable=False, default=1)
    resource_types = Column(JSONB, nullable=False, default={})
    color_hex = Column(String(7), nullable=False, default="#FFFFFF")
    icon_path = Column(String(255), nullable=True)
    
    def __repr__(self):
        return f"<Biome(biome_id={self.biome_id}, name='{self.name}')>"