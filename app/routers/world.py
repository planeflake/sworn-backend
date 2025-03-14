# app/routers/world.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session, joinedload
from typing import List
from uuid import UUID

from database.connection import get_db
from models.core import Worlds, Themes
from app.schemas.world import WorldResponse, WorldStateResponse
from app.game_state.manager import GameStateManager
from workers.time_worker import advance_game_day

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
            "game_date": world.current_game_day
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
        "game_date": world.current_game_day
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
            "theme_name": getattr(world_obj, "theme_name", None),  # Adapt based on your object structure
            "is_premium": getattr(world_obj, "is_premium", None),
            "max_players": getattr(world_obj, "max_players", None),
            "current_game_day": getattr(world_obj, "current_game_day", None),
            "world_seed": getattr(world_obj, "world_seed", None),
            "creation_date": getattr(world_obj, "creation_date", None),
            "last_updated": getattr(world_obj, "last_updated", None)
        },
        "current_day": state["current_day"],
        "settlement_count": state["settlement_count"],
        "player_count": state["player_count"]
        # "events": [] is no longer required since you commented it out in the model
    }

@router.post("/{world_id}/advance-day")
async def trigger_day_advance(world_id: UUID, background_tasks: BackgroundTasks):
    # Use background task to trigger Celery worker without waiting for completion
    background_tasks.add_task(advance_game_day.delay, str(world_id))
    return {"status": "Day advancement initiated"}