from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, date
import uuid

# Area Models (to complement your existing system)
class AreaBase(BaseModel):
    world_id: str
    theme_id: Optional[str] = None
    area_name: str
    area_type: str
    biome_id: int
    location_x: float
    location_y: float
    radius: float = 15.0
    danger_level: int = 1
    resource_richness: float = 0.5
    description: str = ""
    connected_settlements: List[str] = []
    connected_areas: List[str] = []

class AreaCreate(AreaBase):
    pass

class Area(AreaBase):
    area_id: str
    created_at: datetime
    last_updated: datetime

    class Config:
        has_attributes = True

# Travel Route Models
class TravelRouteBase(BaseModel):
    start_settlement_id: str
    end_settlement_id: str
    path: List[str]  # List of area_ids forming the path
    distance: float = 0.0
    danger_level: int = 1
    recommended_transport: Optional[str] = None
    travel_time_modifier: float = 1.0
    description: Optional[str] = None

class TravelRouteCreate(TravelRouteBase):
    pass

class TravelRoute(TravelRouteBase):
    route_id: str
    created_at: datetime
    last_updated: Optional[datetime] = None

    class Config:
        has_attributes = True

# Current Weather State Models (for tracking active weather)
class WorldWeatherStateBase(BaseModel):
    world_id: str
    weather_id: int
    start_date: datetime  # When this weather began
    end_date: Optional[datetime] = None  # When this weather will end (predicted)
    severity: float = 1.0  # How severe this instance is (1.0 = normal)
    affected_biomes: List[int] = []  # Which biomes are affected, empty means all

class WorldWeatherStateCreate(WorldWeatherStateBase):
    pass

class WorldWeatherState(WorldWeatherStateBase):
    weather_state_id: int
    
    class Config:
        has_attributes = True

# Trader Transport Models (for tracking what transport each trader has)
class TraderTransportBase(BaseModel):
    trader_id: str
    transport_id: int
    acquisition_date: datetime
    condition: float = 100.0  # Percentage condition (affects actual speed)
    modifications: Dict[str, Any] = {}  # Custom upgrades or modifications
    name: Optional[str] = None  # Custom name for the transport

class TraderTransportCreate(TraderTransportBase):
    pass

class TraderTransport(TraderTransportBase):
    trader_transport_id: int
    
    class Config:
        has_attributes = True

# Journey Models (for tracking travel progress)
class JourneyBase(BaseModel):
    trader_id: str
    start_settlement_id: str
    destination_settlement_id: str
    transport_id: int
    path: List[str]  # List of area_ids forming the path
    start_time: datetime
    expected_arrival: datetime
    current_area_id: Optional[str] = None
    progress: float = 0.0  # Percentage progress (0-100)
    is_active: bool = True
    weather_effects: List[Dict[str, Any]] = []  # Weather encountered during journey

class JourneyCreate(JourneyBase):
    pass

class Journey(JourneyBase):
    journey_id: int
    completed_at: Optional[datetime] = None
    
    class Config:
        has_attributes = True

# Utility Models for Movement Calculation
class MovementParams(BaseModel):
    """Parameters for actual movement calculation in game logic"""
    trader_id: str
    path: List[str]  # Area IDs to travel through
    transport_id: int
    start_time: datetime
    
    # Optional overrides
    forced_speed: Optional[float] = None
    ignore_weather: bool = False
    ignore_terrain: bool = False

class MovementResult(BaseModel):
    """Result of movement calculation"""
    total_distance: float
    total_travel_time: float  # In hours or game time units
    arrival_time: datetime
    area_times: Dict[str, float]  # Time spent in each area
    encounter_chances: Dict[str, float]  # Chance of encounter in each area
    resource_costs: Dict[str, float] = {}  # Resources consumed (e.g. food, water)
    gold_costs: float = 0.0  # Tolls and other costs
    risks: List[Dict[str, Any]] = []  # Potential risks along the journey