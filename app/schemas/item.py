# schemas/area.py
from pydantic import BaseModel, UUID4, Field
from typing import Optional, List, Dict, Any, Union
import uuid
from datetime import datetime

from app.schemas.base import TimeStampModel

class ItemBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = None
    weight: float = Field(..., ge=0.0)
    value: int = Field(..., ge=0)
    rarity: float = Field(..., ge=0.0, le=1.0)

class ItemCreate(ItemBase):
    pass

class ItemResponse(ItemBase, TimeStampModel):
    item_id: UUID4
    owner_id: UUID4
    durability: int
    max_durability: int