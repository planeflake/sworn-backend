from pydantic import BaseModel
from typing import Dict, List, Optional, Any

class ServiceDetail(BaseModel):
    durability_restored: Optional[int] = None
    cost: Optional[int] = None
    materials_required: Optional[Dict[str, int]] = None
    capacity_bonus: Optional[int] = None
    durability_bonus: Optional[int] = None
    weather_protection: Optional[bool] = None
    travel_speed_bonus: Optional[float] = None
    health_restored: Optional[int] = None
    cost_per_day: Optional[int] = None
    protection: Optional[int] = None
    specialty: Optional[str] = None
    preservation_bonus: Optional[float] = None
    journey_endurance: Optional[float] = None
    mountain_travel_bonus: Optional[float] = None
    quality_improved: Optional[bool] = None

class Business(BaseModel):
    level: int
    services: Dict[str, ServiceDetail]

class Settlement(BaseModel):
    name: str
    businesses: Dict[str, Business]

class SettlementsImport(BaseModel):
    settlements: List[Settlement]
