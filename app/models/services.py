from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class Service(BaseModel):
    service_id: str
    service_name: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class ServiceOption(BaseModel):
    option_id: str
    service_id: str  # Foreign key to Service
    option_name: str
    default_attributes: Dict[str, Any]
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class AreaService(BaseModel):
    area_service_id: str
    area_id: str  # This should match the type used in your areas table (UUID as string)
    option_id: str  # Foreign key to ServiceOption
    modifier: Dict[str, Any]  # Overrides or custom settings
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
