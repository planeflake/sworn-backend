from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Union
from datetime import datetime
import uuid

# Base Biome Models
class BiomeBase(BaseModel):
    name: str
    display_name: str
    description: str
    base_movement_modifier: float = 1.0
    danger_level_base: int = 1
    resource_types: Dict[str, float] = {}
    color_hex: str = "#FFFFFF"
    icon_path: Optional[str] = None

class BiomeCreate(BiomeBase):
    pass

class Biome(BiomeBase):
    biome_id: int

    class Config:
        orm_mode = True

# Weather Models
class WeatherBase(BaseModel):
    name: str
    display_name: str
    description: str
    movement_modifier: float = 1.0
    encounter_modifier: float = 1.0
    resource_modifiers: Dict[str, float] = {}
    visibility_modifier: float = 1.0
    terrain_effects: Dict[str, float]  # Biome ID to movement effect
    duration_range: List[int]  # [min_days, max_days]
    season_weights: Dict[str, float]  # Season name to probability
    icon_path: Optional[str] = None
    color_hex: str = "#FFFFFF"

class WeatherCreate(WeatherBase):
    pass

class Weather(WeatherBase):
    weather_id: int

    class Config:
        orm_mode = True

# Transport Method Models
class TransportMethodBase(BaseModel):
    name: str
    display_name: str
    description: str
    base_speed: float = 1.0
    capacity: int  # Cargo capacity
    acquisition_cost: int
    maintenance_cost: int
    terrain_modifiers: Dict[str, float]  # Biome ID to speed modifier
    weather_vulnerabilities: Dict[str, float]  # Weather name to speed modifier
    requirements: Optional[str] = None
    benefits: Optional[str] = None
    icon_path: Optional[str] = None
    available_for_purchase: bool = True

class TransportMethodCreate(TransportMethodBase):
    pass

class TransportMethod(TransportMethodBase):
    transport_id: int

    class Config:
        orm_mode = True

# Road Type Models
class RoadTypeBase(BaseModel):
    name: str
    display_name: str
    description: str
    movement_modifier: float = 1.0
    maintenance_cost: int = 0
    required_for_transport: List[str] = []  # List of transport names requiring this road level

class RoadTypeCreate(RoadTypeBase):
    pass

class RoadType(RoadTypeBase):
    road_type_id: int

    class Config:
        orm_mode = True

# Area Road Models
class AreaRoadBase(BaseModel):
    area_id: str  # Using string since your db uses VARCHAR
    connecting_area_id: str
    road_type_id: int
    length: float
    toll_cost: int = 0
    restricted_access: bool = False

    @validator('area_id', 'connecting_area_id')
    def validate_uuid_format(cls, v):
        # Optional validation if area_ids should be properly formatted UUIDs
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError('Invalid UUID format')

class AreaRoadCreate(AreaRoadBase):
    pass

class AreaRoad(AreaRoadBase):
    area_road_id: int

    class Config:
        orm_mode = True

# Season Models (based on your existing seasons table)
class SeasonBase(BaseModel):
    name: str
    display_name: str
    next_season: str
    resource_modifiers: Dict[str, float] = {}
    travel_modifier: float = 1.0
    description: str
    color_hex: str = "#FFFFFF"

class SeasonCreate(SeasonBase):
    pass

class Season(SeasonBase):
    season_id: int

    class Config:
        orm_mode = True

# Combined models for movement calculation
class MovementFactors(BaseModel):
    """Model to hold all factors affecting movement speed"""
    base_speed: float = 1.0
    biome_modifier: float = 1.0
    road_modifier: float = 1.0
    weather_modifier: float = 1.0
    season_modifier: float = 1.0
    transport_modifier: float = 1.0
    additional_modifiers: Dict[str, float] = {}
    
    def calculate_total_speed(self) -> float:
        """Calculate the final movement speed with all factors applied"""
        base = self.base_speed
        base *= self.biome_modifier
        base *= self.road_modifier
        base *= self.weather_modifier
        base *= self.season_modifier
        base *= self.transport_modifier
        
        # Apply any additional modifiers
        for modifier in self.additional_modifiers.values():
            base *= modifier
            
        return base

# Request/Response models for movement calculation API
class MovementCalculationRequest(BaseModel):
    transport_method_id: int
    biome_id: int
    road_type_id: Optional[int] = None
    weather_id: Optional[int] = None
    season_name: Optional[str] = None
    additional_modifiers: Dict[str, float] = {}

class MovementCalculationResponse(BaseModel):
    base_speed: float
    total_speed: float
    travel_time_per_unit: float  # Time to travel 1 unit of distance
    factors: MovementFactors
    limitations: List[str] = []  # Any limitations on travel (e.g., "Cannot travel through mountains")