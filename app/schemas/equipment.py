# schemas/area.py
from pydantic import BaseModel, UUID4, Field
from typing import Optional, List, Dict, Any, Union
import uuid
from datetime import datetime

from app.schemas.base import TimeStampModel
from app.models.equipment import Equipment
from pydantic import BaseModel
from typing import Dict, Optional

from app.models.item import Item

class Slot(BaseModel):
    id: UUID4
    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=255)

class EquipmentBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    weight: float = Field(..., ge=0)
    value: int = Field(..., ge=0)
    durability: int = Field(..., ge=0)
    is_equipped: bool = False
    is_usable: bool = False
    is_consumable: bool = False
    is_stackable: bool = False
    is_unique: bool = False
    slot: Optional[str] = Field(None, max_length=50)
    rarity: Optional[str] = Field(None, max_length=50)

class EquipItemRequest(BaseModel):
    item_id: str
    slot: str
    
class EquipmentResponse(BaseModel):
    character_id: str
    slots: Dict[str, Optional[str]]