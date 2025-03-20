from pydantic import BaseModel
from typing import Optional


# Pydantic model for database operations
class VillagerDB(BaseModel):
    """Database model for Villager table"""
    villager_id: str
    name: Optional[str] = None
    location_id: Optional[str] = None
    data: str  # JSON string of villager data