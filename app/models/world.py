from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class World(BaseModel):
    """
    Represents a world in the game as a Pydantic model.

    Example:
        {
            "world_id": "12345",
            "name": "Fantasy World",
            "description": "A magical realm full of adventure.",
            "world_seed": "abc123",
            "creation_date": "2023-01-01T00:00:00",
            "last_updated": "2023-01-10T12:00:00",
            "active": True,
            "is_premium": False,
            "max_players": 100,
            "theme_id": "medieval",
            "current_game_day": 42,
            "current_season": "summer",
            "day_of_season": 12,
            "days_per_season": 30,
            "current_year": 2,
            "properties": {},
            "regions": {},
            "settlements": {},
            "areas": {},
            "resource_sites": {},
            "travel_routes": {},
            "weather_system": {"current": {}, "forecast": []},
            "economy_state": {"global_inflation": 1.0, "resource_scarcity": {}}
        }
    """

    # Basic information
    world_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    world_seed: Optional[str] = None
    creation_date: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    active: bool = True
    is_premium: bool = False
    max_players: int = 100
    theme_id: Optional[str] = None

    # Time and seasons
    current_game_day: int = 1
    current_season: str = "spring"
    day_of_season: int = 1
    days_per_season: int = 30
    current_year: int = 1

    # World state
    properties: Dict[str, Any] = Field(default_factory=dict)
    regions: Dict[str, Any] = Field(default_factory=dict)
    settlements: Dict[str, Any] = Field(default_factory=dict)
    areas: Dict[str, Any] = Field(default_factory=dict)
    resource_sites: Dict[str, Any] = Field(default_factory=dict)
    travel_routes: Dict[str, Any] = Field(default_factory=dict)

    # World systems
    weather_system: Dict[str, Any] = Field(default_factory=lambda: {"current": {}, "forecast": []})
    economy_state: Dict[str, Any] = Field(default_factory=lambda: {
        "global_inflation": 1.0,
        "resource_scarcity": {}
    })

    # Events
    active_events: List[Dict[str, Any]] = Field(default_factory=list)
    scheduled_events: List[Dict[str, Any]] = Field(default_factory=list)

    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True  # Allow non-standard types if needed

# Example usage:
# data = {...}  # Dictionary representing a world
# world = World(**data)  # Create a World instance from the dictionary