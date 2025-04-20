# app/routers/world.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session, joinedload
from typing import List
from uuid import UUID

from database.connection import get_db
from app.models.core import Worlds, Themes
from app.schemas.world import WorldResponse, WorldStateResponse
from app.game_state.manager import GameStateManager
# Temporarily comment this out to get the server running
from app.workers.time_worker import advance_game_day

router = APIRouter(prefix="/worlds", tags=["worlds"])

@router.get("/", response_model=List[WorldResponse])
async def get_worlds(db: Session = Depends(get_db)):
    # Query with join to Themes table
    worlds = db.query(
        Worlds, 
        Themes.theme_name
    ).outerjoin(
        Themes, 
        Worlds.theme_id == Themes.theme_id
    ).all()
    
    # Process the results to include theme name
    result = []
    for world, theme_name in worlds:
        result.append({
            "world_id": str(world.world_id),  # Convert UUID to string
            "world_name": world.world_name,
            "created_at": world.creation_date,
            "updated_at": world.last_updated,
            "theme_id": str(world.theme_id) if world.theme_id else None,  # Convert UUID to string if exists
            "theme_name": theme_name,
            "active": world.active,
            "current_game_day": world.current_game_day
        })
    
    return result

@router.get("/{world_id}", response_model=WorldResponse)
async def get_world(world_id: UUID, db: Session = Depends(get_db)):
    # Query with join to Themes table
    result = db.query(
        Worlds,
        Themes.theme_name
    ).outerjoin(
        Themes,
        Worlds.theme_id == Themes.theme_id
    ).filter(
        Worlds.world_id == str(world_id)
    ).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="World not found")
    
    world, theme_name = result
    
    # Create a dictionary with proper string conversion for UUIDs
    return {
        "world_id": str(world.world_id),  # Convert UUID to string
        "world_name": world.world_name,
        "created_at": world.creation_date,
        "updated_at": world.last_updated,
        "theme_id": str(world.theme_id) if world.theme_id else None,  # Convert UUID to string if exists
        "theme_name": theme_name,
        "active": world.active,
        "current_game_day": world.current_game_day
    }

@router.get("/{world_id}/state", response_model=WorldStateResponse)
async def get_world_state(world_id: UUID, db: Session = Depends(get_db)):
    manager = GameStateManager(db)
    state = manager.get_world_state(world_id)
    if not state:
        raise HTTPException(status_code=404, detail="World not found")
    
    # Get the world data to construct the nested world object
    world_obj = state.get('world')
    
    # Transform the response to match WorldStateResponse model
    return {
        "world": {
            "world_id": str(world_id),
            "world_name": world_obj.world_name,
            "theme_id": str(world_obj.theme_id) if world_obj.theme_id else None,
            "theme_name": getattr(world_obj, "theme_name", None),
            "is_premium": getattr(world_obj, "is_premium", None),
            "max_players": getattr(world_obj, "max_players", None),
            "current_game_day": getattr(world_obj, "current_game_day", None),
            "current_season": getattr(world_obj, "current_season", None),
            "day_of_season": getattr(world_obj, "day_of_season", None),
            "days_per_season": getattr(world_obj, "days_per_season", None),
            "current_year": getattr(world_obj, "current_year", None),
            "world_seed": getattr(world_obj, "world_seed", None),
            "creation_date": getattr(world_obj, "creation_date", None),
            "last_updated": getattr(world_obj, "last_updated", None)
        },
        "current_day": state["current_day"],
        "settlement_count": state["settlement_count"],
        "player_count": state["player_count"],
        "current_season": state.get("current_season")
    }

@router.post("/{world_id}/advance-day")
async def trigger_day_advance(world_id: UUID, background_tasks: BackgroundTasks):
    # Schedule the tick in the background via Celery
    task = advance_game_day.delay(str(world_id))
    return {
        "status": "Task submitted",
        "task_id": task.id,
        "world_id": str(world_id)
    }


@router.get("/{world_id}/seasons")
async def get_seasons(world_id: UUID, db: Session = Depends(get_db)):
    """Get information about all seasons and highlight the current one"""
    from app.models.seasons import Seasons
    
    # Check if world exists
    world = db.query(Worlds).filter(Worlds.world_id == str(world_id)).first()
    if not world:
        raise HTTPException(status_code=404, detail="World not found")
    
    # Get current season for this world
    current_season = getattr(world, "current_season", "spring")
    
    # Get all seasons
    seasons = db.query(Seasons).all()
    if not seasons:
        # If seasons table doesn't exist yet or is empty, return default seasons
        default_seasons = [
            {
                "name": "spring",
                "display_name": "Spring",
                "description": "The growing season. Food and herbs are plentiful.",
                "color_hex": "#76FF7A",
                "resource_modifiers": {"wood": 1.0, "food": 1.2, "stone": 0.9, "ore": 0.9, "herbs": 1.3},
                "travel_modifier": 1.0,
                "is_current": current_season == "spring"
            },
            {
                "name": "summer",
                "display_name": "Summer", 
                "description": "Hot and dry. Mining and construction are efficient.",
                "color_hex": "#FFCF40",
                "resource_modifiers": {"wood": 1.1, "food": 1.1, "stone": 1.2, "ore": 1.2, "herbs": 1.0},
                "travel_modifier": 1.2,
                "is_current": current_season == "summer"
            },
            {
                "name": "autumn",
                "display_name": "Autumn",
                "description": "Harvest time. Wood gathering is most effective.",
                "color_hex": "#FF9A3D",
                "resource_modifiers": {"wood": 1.2, "food": 1.0, "stone": 1.1, "ore": 1.0, "herbs": 0.8},
                "travel_modifier": 1.0,
                "is_current": current_season == "autumn"
            },
            {
                "name": "winter",
                "display_name": "Winter",
                "description": "Cold and harsh. All resource production slows. Travel is difficult.",
                "color_hex": "#A0E9FF",
                "resource_modifiers": {"wood": 0.7, "food": 0.6, "stone": 0.7, "ore": 0.8, "herbs": 0.5},
                "travel_modifier": 0.7,
                "is_current": current_season == "winter"
            }
        ]
        return {
            "current_season": current_season,
            "day_of_season": getattr(world, "day_of_season", 1),
            "days_per_season": getattr(world, "days_per_season", 30),
            "seasons": default_seasons
        }
    
    # Format seasons from database
    formatted_seasons = []
    for season in seasons:
        formatted_seasons.append({
            "name": season.name,
            "display_name": season.display_name,
            "description": season.description,
            "color_hex": season.color_hex,
            "resource_modifiers": season.resource_modifiers,
            "travel_modifier": season.travel_modifier,
            "is_current": season.name == current_season
        })
    
    return {
        "current_season": current_season,
        "day_of_season": getattr(world, "day_of_season", 1),
        "days_per_season": getattr(world, "days_per_season", 30),
        "seasons": formatted_seasons
    }

from app.workers.world_worker import advance_game_day  # <-- correct module
