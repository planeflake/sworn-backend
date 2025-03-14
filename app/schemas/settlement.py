# schemas/settlement.py
from pydantic import BaseModel, UUID4, validator, Field
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime

from app.schemas.base import TimeStampModel

class SettlementBase(BaseModel):
    settlement_name: str = Field(..., min_length=3, max_length=100)
    area_type: str
    location_x: float
    location_y: float
    population: int = Field(..., ge=0)

class SettlementCreate(SettlementBase):
    world_id: UUID4
    threats: Optional[List[str]] = []
    connections: Optional[Dict[str, Any]] = {}

class Connection(BaseModel):
    distance: int
    destination: str
    danger_level: int
    path_condition: str
    biome_composition: Dict[str, float]

class SettlementResponse(SettlementBase, TimeStampModel):
    settlement_id: UUID4
    world_id: UUID4
    owner_character_id: Optional[UUID4] = None
    threats: List[str] = []
    connections: List[Connection] = {}

    class Config:
        has_attributes = True

class BuildingBase(BaseModel):
    building_type_id: UUID4
    construction_status: str = "planned"
    construction_progress: float = 0.0
    health: int = 100
    is_operational: bool = False

class BuildingCreate(BuildingBase):
    settlement_id: UUID4

class BuildingResponse(BuildingBase, TimeStampModel):
    settlement_building_id: UUID4
    settlement_id: UUID4
    building_name: str  # This would be joined from building_types
    building_type: str  # This would be joined from building_types
    staff_assigned: List[Dict[str, Any]] = []
    constructed_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class ResourceBase(BaseModel):
    resource_type_id: UUID4
    quantity: int = Field(..., ge=0)

class ResourceCreate(ResourceBase):
    settlement_id: UUID4

class ResourceResponse(ResourceBase, TimeStampModel):
    settlement_resource_id: UUID4
    settlement_id: UUID4
    resource_name: str  # This would be joined from resource_types

    class Config:
        orm_mode = True

class BuildRequest(BaseModel):
    location_x: Optional[float] = None
    location_y: Optional[float] = None

class ConnectionResponse(BaseModel):
    destination: str
    distance: int
    biome_composition: Dict[str, float]
    danger_level: int
    path_condition: str
    sea_route: Optional[bool] = False