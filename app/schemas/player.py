# schemas/player.py
from pydantic import BaseModel, UUID4, validator, Field, EmailStr
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime

from app.schemas.base import TimeStampModel

class PlayerBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr

class PlayerCreate(PlayerBase):
    password: str = Field(..., min_length=8)

class PlayerResponse(PlayerBase, TimeStampModel):
    player_id: UUID4
    is_premium: bool = False
    last_login: Optional[datetime] = None

    class Config:
        has_attributes = True

class CharacterBase(BaseModel):
    character_name: str = Field(..., min_length=2, max_length=50)
    location_x: float
    location_y: float

class CharacterCreate(CharacterBase):
    world_id: UUID4

class CharacterResponse(CharacterBase, TimeStampModel):
    character_id: UUID4
    player_id: UUID4
    health: int = 100
    energy: int = 100

    class Config:
        has_attributes = True

class ResourceItemBase(BaseModel):
    resource_type_id: UUID4
    quantity: int = Field(..., ge=0)

class InventoryItemCreate(ResourceItemBase):
    pass

class InventoryResponse(ResourceItemBase, TimeStampModel):
    inventory_id: UUID4
    character_id: UUID4
    resource_name: str  # This would be joined from resource_types

    class Config:
        has_attributes = True

class SkillBase(BaseModel):
    skill_type_id: UUID4
    current_level: int = Field(..., ge=0)
    current_xp: int = Field(..., ge=0)

class SkillCreate(SkillBase):
    pass

class SkillResponse(SkillBase, TimeStampModel):
    character_skill_id: UUID4
    character_id: UUID4
    skill_name: str  # This would be joined from skill_types

    class Config:
        has_attributes = True

class GatherResourceRequest(BaseModel):
    quantity: Optional[int] = 1

class GatherResourceResponse(BaseModel):
    status: str
    character_id: str
    resource: str
    quantity_gathered: int
    time_spent: float