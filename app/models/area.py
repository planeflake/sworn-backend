from sqlalchemy import Column, String, Text, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class AreaModel(Base):
    __tablename__ = 'areas'
    
    # A unique identifier for the area (matches your area_id)
    area_id = Column(String, primary_key=True, index=True)
    
    # Basic information
    area_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    area_type = Column(String, nullable=True)
    
    # Additional fields based on your domain model
    controlling_faction = Column(String, nullable=True)
    dominant_species = Column(String, nullable=True)
    weather = Column(String, nullable=True)
    
    # Store quests as a JSON list; you could alternatively model this as a separate table
    quests = Column(JSON, default=list)

    @classmethod
    def from_dict(cls, data: dict) -> 'AreaModel':
        """Create an Area instance from a dictionary."""
        return cls(
            area_id=data.get('area_id'),
            area_name=data.get('area_name'),  # Fixed to match field name
            description=data.get('description'),
            area_type=data.get('area_type'),
            controlling_faction=data.get('controlling_faction'),
            dominant_species=data.get('dominant_species'),
            weather=data.get('weather'),
            quests=data.get('quests')
        )

    def to_dict(self) -> dict:
        """Convert the SQLAlchemy model to a dictionary."""
        return {
            "area_id": self.area_id,
            "area_name": self.area_name,  # Changed to match property name in Area entity
            "description": self.description,
            "area_type": self.area_type,
            "controlling_faction": self.controlling_faction,
            "dominant_species": self.dominant_species,
            "weather": self.weather,
            "quests": self.quests,
        }
