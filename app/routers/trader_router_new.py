# app/routers/trader_router_new.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional

from database.connection import get_db
from app.schemas.trader import (
    TraderResponse, 
    TraderCreate, 
    TraderUpdate, 
    TraderWithPath
)
from app.game_state.managers.trader_manager import TraderManager
from app.game_state.entities.trader import Trader as TraderEntity
from app.workers.trader_worker import process_trader_movement, process_all_traders

router = APIRouter(prefix="/traders", tags=["traders"])

# Helper function to convert between entity and response models
def entity_to_response(entity: TraderEntity) -> TraderResponse:
    """Convert a trader entity to a response model"""
    return TraderResponse(
        trader_id=entity.trader_id,
        name=entity.name,
        description=entity.description,
        current_location_id=entity.current_location_id,
        destination_id=entity.destination_id,
        preferred_biomes=entity.preferred_biomes,
        resources=entity.resources,
        # Include other fields as needed
    )

@router.get("/", response_model=List[TraderResponse])
def get_all_traders(world_id: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Get all traders, optionally filtered by world_id.
    """
    trader_manager = TraderManager()
    traders = trader_manager.get_all_traders()
    
    # Convert entities to response models
    return [entity_to_response(trader) for trader in traders]

@router.get("/{trader_id}", response_model=TraderResponse)
def get_trader(trader_id: str, db: Session = Depends(get_db)):
    """
    Get a specific trader by ID.
    """
    trader_manager = TraderManager()
    trader = trader_manager.load_trader(trader_id)
    
    if not trader:
        raise HTTPException(status_code=404, detail="Trader not found")
    
    return entity_to_response(trader)

@router.post("/", response_model=TraderResponse)
def create_trader(trader: TraderCreate, db: Session = Depends(get_db)):
    """
    Create a new trader.
    """
    trader_manager = TraderManager()
    
    # Create new trader entity
    new_trader = trader_manager.create_trader(
        name=trader.name,
        description=trader.description
    )
    
    # Set initial location if provided
    if trader.current_location_id:
        new_trader.set_location(trader.current_location_id, "current")
        trader_manager.save_trader(new_trader)
    
    return entity_to_response(new_trader)

@router.put("/{trader_id}", response_model=TraderResponse)
def update_trader(trader_id: str, trader_update: TraderUpdate, db: Session = Depends(get_db)):
    """
    Update a trader's information.
    """
    trader_manager = TraderManager()
    trader = trader_manager.load_trader(trader_id)
    
    if not trader:
        raise HTTPException(status_code=404, detail="Trader not found")
    
    # Update the trader entity
    if trader_update.name:
        trader.name = trader_update.name
    
    if trader_update.description:
        trader.description = trader_update.description
    
    if trader_update.current_location_id:
        trader.set_location(trader_update.current_location_id, "current")
    
    if trader_update.destination_id:
        trader.set_location(trader_update.destination_id, "destination")
    
    # Save the updated trader
    trader_manager.save_trader(trader)
    
    return entity_to_response(trader)

@router.delete("/{trader_id}")
def delete_trader(trader_id: str, db: Session = Depends(get_db)):
    """
    Delete a trader.
    """
    trader_manager = TraderManager()
    success = trader_manager.delete_trader(trader_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Trader not found or could not be deleted")
    
    return {"status": "success", "message": f"Trader {trader_id} deleted"}

@router.post("/{trader_id}/move")
def move_trader(
    trader_id: str, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Process movement for a trader.
    This is an asynchronous operation that will be processed in the background.
    """
    # First check if the trader exists
    trader_manager = TraderManager()
    trader = trader_manager.load_trader(trader_id)
    
    if not trader:
        raise HTTPException(status_code=404, detail="Trader not found")
    
    # Queue the background task
    background_tasks.add_task(process_trader_movement, trader_id)
    
    return {
        "status": "processing",
        "message": f"Movement for trader {trader_id} is being processed"
    }

@router.post("/process-all")
def process_all(
    background_tasks: BackgroundTasks,
    world_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Process movement for all traders in a world (or all worlds).
    This is an asynchronous operation that will be processed in the background.
    """
    # Queue the background task
    background_tasks.add_task(process_all_traders, world_id)
    
    return {
        "status": "processing",
        "message": f"Processing all traders" + (f" in world {world_id}" if world_id else "")
    }