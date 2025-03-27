# schemas/area.py
from pydantic import BaseModel, UUID4, Field
from typing import Optional, List, Dict, Any, Union
import uuid
from datetime import datetime

from app.schemas.base import TimeStampModel

class AnimalBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    species: str = Field(..., min_length=3, max_length=100)
    age: int = Field(..., ge=0)

class AnimalCreate(AnimalBase):
    group_id: UUID4
    area_id: UUID4
    health: int
    hunger: int
    thirst: int
    happiness: int

class AnimalResponse(AnimalBase, TimeStampModel):
    animal_id: UUID4
    group_id: UUID4
    area_id: UUID4
    health: int
    hunger: int
    thirst: int
    happiness: int

    class Config:
        has_attribute = True
