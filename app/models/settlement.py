from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, Text, Boolean, JSON

Base = declarative_base()

class SettlementModel(Base):
    __tablename__ = 'settlements'

    # Unique identifier for the settlement
    settlement_id = Column(String(36), primary_key=True, index=True)
    
    # Basic information
    settlement_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    location_id = Column(String(36), nullable=True)
    
    # Relationships stored as JSON (dictionary)
    relations = Column(JSON, default=dict, nullable=True)
    
    # Settlement-specific status flags
    is_repairable = Column(Boolean, default=False)
    is_damaged = Column(Boolean, default=False)
    has_started_building = Column(Boolean, default=False)
    is_under_repair = Column(Boolean, default=False)
    is_built = Column(Boolean, default=False)
    
    # Additional properties not covered by direct columns
    properties = Column(JSON, default=dict, nullable=True)

    def to_dict(self) -> dict:
        """Convert the SQLAlchemy model to a dictionary."""
        return {
            "id": self.settlement_id,
            "name": self.settlement_name,
            "description": self.description,
            "location_id": self.location_id,
            "relations": self.relations,
            "is_repairable": self.is_repairable,
            "is_damaged": self.is_damaged,
            "has_started_building": self.has_started_building,
            "is_under_repair": self.is_under_repair,
            "is_built": self.is_built,
            "properties": self.properties,
        }
