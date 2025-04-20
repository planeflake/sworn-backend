import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.core import Worlds
from app.models.weather import WorldWeather, Base
from app.game_state.services.weather_service import WeatherService

from datetime import datetime, timezone
import uuid


@pytest.fixture
def in_memory_db():
    """
    Creates an in-memory SQLite database and adds a test world.
    This keeps the tests isolated and fast.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)  # Creates all tables

    db = TestingSessionLocal()

    # Add a dummy world
    test_world = Worlds(
        world_id=str(uuid.uuid4()),
        world_name="TestWorld",
        current_game_day=1,
        current_season="spring"
    )
    db.add(test_world)
    db.commit()

    yield db

    db.close()


def test_generate_weather_for_world(in_memory_db):
    """
    Tests that WeatherService correctly generates a weather event
    for a given world and saves it to the database.
    """
    db = in_memory_db
    world = db.query(Worlds).first()
    service = WeatherService(db)

    result = service.generate_weather_for_world(world.world_id)

    assert "weather_type" in result
    assert result["intensity"] > 0
    assert result["duration"] >= 1

    weather = db.query(WorldWeather).filter_by(world_id=world.world_id).first()
    assert weather is not None
    assert weather.active is True


def test_advance_weather_day(in_memory_db):
    """
    Tests that advancing the weather day correctly decreases duration
    and deactivates the weather when it expires.
    """
    db = in_memory_db
    world = db.query(Worlds).first()
    service = WeatherService(db)

    # Create fixed weather with 1-day duration
    service.record_weather_event(world_id=world.world_id, weather_type="fog", intensity=0.5, duration=1)

    # Advance day (should expire the weather)
    service.advance_weather_day(world.world_id)

    updated = db.query(WorldWeather).filter_by(world_id=world.world_id).first()
    assert updated.duration == 0
    assert updated.active is False


def test_get_current_weather_with_none(in_memory_db):
    """
    Tests that the default weather is returned when no active event exists.
    """
    db = in_memory_db
    world = db.query(Worlds).first()
    service = WeatherService(db)

    result = service.get_current_weather(world.world_id)
    assert result["weather_type"] == "clear"
    assert result["intensity"] == 0.0
