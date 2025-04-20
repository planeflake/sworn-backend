from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.sql import or_
from datetime import datetime, timezone
import random

from app.models.core import Worlds
from app.models.weather import WorldWeather, WeatherType

class WeatherService:
    def __init__(self, db: Session):
        self.db = db

    def get_weighted_weather_types(self, season: str, theme_id: Optional[str]) -> str:
        """
        Pull possible weather types for a season and theme, return one randomly based on weight.
        """
        query = self.db.query(WeatherType).filter(WeatherType.season == season)
        if theme_id:
            query = query.filter(or_(WeatherType.theme_id == theme_id, WeatherType.theme_id == None))

        results = query.all()

        if not results:
            return "clear"  # fallback if no entries found

        pool = [w.weather_type for w in results for _ in range(int(w.weight * 10))]
        return random.choice(pool)

    def generate_weather_for_world(self, world_id: str) -> Dict[str, Any]:
        world = self.db.query(Worlds).filter_by(world_id=world_id).first()
        if not world:
            raise ValueError("World not found")

        season = world.current_season or "spring"
        theme_id = str(world.theme_id) if world.theme_id else None

        chosen_weather = self.get_weighted_weather_types(season, theme_id)
        intensity = round(random.uniform(0.3, 1.0), 2)
        duration = random.randint(1, 3)

        # Create a new weather event
        weather = WorldWeather(
            world_id=world_id,
            weather_type=chosen_weather,
            intensity=intensity,
            duration=duration,
            active=True,
            created_at=datetime.now(timezone.utc)
        )

        self.db.add(weather)
        self.db.commit()
        self.db.refresh(weather)

        return {
            "weather_type": chosen_weather,
            "intensity": intensity,
            "duration": duration
        }

    def get_current_weather(self, world_id: str) -> Dict[str, Any]:
        event = (
            self.db.query(WorldWeather)
            .filter_by(world_id=world_id, active=True)
            .order_by(WorldWeather.created_at.desc())
            .first()
        )
        if not event:
            return {"weather_type": "clear", "intensity": 0.0, "duration": 0}
        return {
            "weather_type": event.weather_type,
            "intensity": event.intensity,
            "duration": event.duration,
            "days_remaining": event.duration
        }

    def advance_weather_day(self, world_id: str) -> None:
        active_event = (
            self.db.query(WorldWeather)
            .filter_by(world_id=world_id, active=True)
            .order_by(WorldWeather.created_at.desc())
            .first()
        )
        if not active_event:
            return

        active_event.duration -= 1
        if active_event.duration <= 0:
            active_event.active = False

        self.db.commit()

    def record_weather_event(self, world_id: str, weather_type: str, intensity: float, duration: int) -> None:
        weather = WorldWeather(
            world_id=world_id,
            weather_type=weather_type,
            intensity=intensity,
            duration=duration,
            active=True,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(weather)
        self.db.commit()

    def apply_weather_effects(self, world_id: str) -> None:
        # Placeholder for logic that adjusts settlement/trader stats based on current weather
        current = self.get_current_weather(world_id)
        # Apply modifiers to services or cache effects
        pass