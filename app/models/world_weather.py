from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
import uuid
from datetime import datetime, timezone
from typing import Dict, Any

Base = declarative_base()

class WorldWeather(Base):
    __tablename__ = "world_weather"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    world_id = Column(UUID(as_uuid=True), ForeignKey("worlds.world_id"), nullable=False)
    weather_type = Column(String, nullable=False)
    intensity = Column(Float, default=0.0)
    duration = Column(Integer, default=1)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default= lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))