# schemas/area.py
from pydantic import BaseModel, UUID4, validator, Field
from typing import Optional, List, Dict, Any, Union
import uuid
from datetime import datetime

from app.schemas.base import TimeStampModel

class AreaBase(BaseModel):
    area_name: str = Field(..., min_length=3, max_length=100)
    area_type: str
    location_x: float
    location_y: float
    danger_level: int = Field(..., ge=1, le=10)
    resource_richness: float = Field(..., ge=0.0, le=1.0)
    description: Optional[str] = None
    radius: Optional[float] = 10.0

class AreaCreate(AreaBase):
    world_id: UUID4
    theme_id: Optional[UUID4] = None
    connected_settlements: Optional[List[UUID4]] = []
    connected_areas: Optional[List[UUID4]] = []

class AreaResponse(AreaBase, TimeStampModel):
    area_id: UUID4
    world_id: UUID4
    theme_id: Optional[UUID4] = None
    connected_settlements: List[UUID4] = []
    connected_areas: List[UUID4] = []

    class Config:
        orm_mode = True

class EncounterTypeBase(BaseModel):
    encounter_code: str = Field(..., min_length=3, max_length=50)
    encounter_name: str = Field(..., min_length=3, max_length=100)
    encounter_category: str
    min_danger_level: int = Field(..., ge=0, le=10)
    compatible_area_types: List[str]
    rarity: float = Field(..., ge=0.0, le=1.0)
    description: str

class EncounterTypeResponse(EncounterTypeBase, TimeStampModel):
    encounter_type_id: UUID4
    theme_id: Optional[UUID4] = None
    possible_outcomes: List[UUID4] = []

    class Config:
        orm_mode = True

class EncounterOutcomeBase(BaseModel):
    outcome_code: str = Field(..., min_length=3, max_length=50)
    outcome_name: str = Field(..., min_length=3, max_length=100)
    outcome_type: str
    probability: float = Field(..., ge=0.0, le=1.0)
    narrative: str
    requirements: Optional[Dict[str, Any]] = None
    rewards: Optional[Dict[str, Any]] = None
    penalties: Optional[Dict[str, Any]] = None

class EncounterOutcomeResponse(EncounterOutcomeBase):
    outcome_id: UUID4
    encounter_type_id: UUID4

    class Config:
        orm_mode = True

class ActiveEncounterResponse(BaseModel):
    encounter_id: UUID4
    area_id: UUID4
    encounter_type_id: UUID4
    encounter_name: str
    encounter_description: str
    area_name: str
    current_state: str
    created_at: datetime
    possible_outcomes: List[EncounterOutcomeResponse] = []

    class Config:
        orm_mode = True

class EncounterResolveRequest(BaseModel):
    character_id: Optional[UUID4] = None
    trader_id: Optional[UUID4] = None
    chosen_outcome_code: Optional[str] = None

class EncounterResolveResponse(BaseModel):
    encounter_id: UUID4
    outcome_name: str
    outcome_type: str
    narrative: str
    rewards: Dict[str, Any] = {}
    penalties: Dict[str, Any] = {}

    class Config:
        orm_mode = True

class TravelRequest(BaseModel):
    character_id: Optional[UUID4] = None
    trader_id: Optional[UUID4] = None
    destination_area_id: UUID4
    current_area_id: Optional[UUID4] = None
    current_settlement_id: Optional[UUID4] = None

class TravelResponse(BaseModel):
    status: str
    destination_reached: bool = False
    encounter_generated: bool = False
    encounter: Optional[ActiveEncounterResponse] = None
    travel_time: Optional[int] = None
    message: str

    class Config:
        orm_mode = True

class RouteResponse(BaseModel):
    route_id: UUID4
    start_settlement_id: UUID4
    start_settlement_name: str
    end_settlement_id: UUID4
    end_settlement_name: str
    areas: List[AreaResponse]
    total_distance: float
    danger_level: int
    path_condition: str
    travel_time: int

    class Config:
        orm_mode = True