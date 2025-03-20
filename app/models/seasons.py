from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from models.core import Base

class Seasons(Base):
    """
    Season configuration for the game world.
    Defines the effects and characteristics of each season.
    """
    __tablename__ = 'seasons'
    
    season_id = Column(Integer, primary_key=True)
    name = Column(String(10), nullable=False)  # spring, summer, autumn, winter
    display_name = Column(String(30), nullable=False)  # Friendly display name
    next_season = Column(String(10), nullable=False)  # Name of the season that follows
    resource_modifiers = Column(JSONB, nullable=False)  # Production multipliers for resources
    travel_modifier = Column(Float, nullable=False, default=1.0)  # Travel speed multiplier
    description = Column(Text, nullable=False)  # Season description
    color_hex = Column(String(7), nullable=False, default='#FFFFFF')  # Color for UI