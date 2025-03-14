# schemas/world.py
from pydantic import BaseModel, UUID4, validator, Field
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime

from app.schemas.base import TimeStampModel

class ThemeBase(BaseModel):
    theme_name: str = Field(..., min_length=3, max_length=50)
    theme_description: Optional[str] = None

class ThemeCreate(ThemeBase):
    pass

class ThemeResponse(ThemeBase, TimeStampModel):
    theme_id: UUID4
    is_active: bool = True

    class Config:
        from_attributes = True

class WorldBase(BaseModel):
    world_name: str = Field(..., min_length=3, max_length=100)
    theme_id: UUID4
    is_premium: bool = False
    max_players: int = 100
    world_seed: Optional[str] = None

class WorldCreate(WorldBase):
    pass

class WorldResponse(BaseModel):
    world_id: str
    world_name: str
    theme_id: Optional[str] = None
    theme_name: Optional[str] = None  # Add this field
    is_premium: Optional[bool] = None
    max_players: Optional[int] = None
    current_game_day: Optional[int] = None
    world_seed: Optional[str] = None
    creation_date: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    class Config:
        from_attributes = True

class WorldEventBase(BaseModel):
    event_type: str
    event_name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = None
    location_x: float
    location_y: float
    radius: float
    start_day: int
    duration: int
    effects: Dict[str, Any] = {}
    resolution_conditions: Dict[str, Any] = {}

class WorldEventCreate(WorldEventBase):
    world_id: UUID4

class WorldEventResponse(WorldEventBase, TimeStampModel):
    event_id: UUID4
    world_id: UUID4
    is_active: bool = True

    class Config:
        from_attributes = True

class WorldStateResponse(BaseModel):
    world: WorldResponse
    current_day: int
    player_count: int
    settlement_count: int
    #events: List[WorldEventResponse]

    class Config:
        from_attributes = True