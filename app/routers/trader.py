from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from uuid import UUID

from database.connection import get_db
from app.models.core import Traders, TraderInventory, ResourceTypes
from app.schemas.trader import TraderResponse, TraderInventoryResponse, TradeRequest
from app.game_state.manager import GameStateManager
from app.game_state.services.logging_service import LoggingService
from app.models.logging import EntityActionLog

router = APIRouter(prefix="/traders", tags=["traders"])

@router.get("/", response_model=List[TraderResponse])
async def get_traders(settlement_id: Optional[UUID] = None, db: Session = Depends(get_db)):
    query = db.query(Traders)
    if settlement_id:
        query = query.filter(Traders.current_settlement_id == settlement_id)
    traders = query.all()
    return traders

@router.get("/{trader_id}", response_model=TraderResponse)
async def get_trader(trader_id: str, db: Session = Depends(get_db)):
    trader = db.query(Traders).filter(Traders.trader_id == trader_id).first()
    if trader is None:
        raise HTTPException(status_code=404, detail="Trader not found")
    return trader

@router.get("/{trader_id}/inventory", response_model=List[TraderInventoryResponse])
async def get_trader_inventory(trader_id: UUID, db: Session = Depends(get_db)):
    # Get the trader inventory items
    inventory_items = db.query(TraderInventory).filter(TraderInventory.trader_id == trader_id).all()
    
    # Get resource information to include names
    inventory_with_details = []
    for item in inventory_items:
        # Get the resource details using the resource_id from inventory
        resource = db.query(ResourceTypes).filter(ResourceTypes.resource_type_id == item.resource_type_id).first()
        
        # Create the response object with all required fields
        inventory_item = {
            "trader_inventory_id": item.trader_inventory_id,
            "trader_id": item.trader_id,
            "resource_type_id": item.resource_type_id,
            "resource_name": resource.resource_name if resource else "Unknown",
            "quantity": item.quantity,
            "price_modifier": item.price_modifier if hasattr(item, 'price_modifier') else 1.0,
            "base_value": resource.base_value if resource and hasattr(resource, 'base_value') else 0,
            "effective_price": (resource.base_value * item.price_modifier) if resource and hasattr(resource, 'base_value') and hasattr(item, 'price_modifier') else 0
        }
        inventory_with_details.append(inventory_item)
    
    return inventory_with_details

@router.post("/{trader_id}/trade")
async def trade_with_trader(
    trader_id: UUID, 
    trade: TradeRequest, 
    character_id: UUID,
    db: Session = Depends(get_db)
):
    # This would handle a trading transaction between player and trader
    # Check if trader is at same location as character
    # Verify resources availability, pricing, etc.
    return {
        "status": "Trade successful", 
        "trader_id": str(trader_id),
        "character_id": str(character_id),
        "details": trade.dict()
    }

@router.get("/{trader_id}/schedule")
async def get_trader_schedule(trader_id: UUID, db: Session = Depends(get_db)):
    trader = db.query(Traders).filter(Traders.trader_id == trader_id).first()
    if trader is None:
        raise HTTPException(status_code=404, detail="Trader not found")
    return trader.schedule

@router.get("/{trader_id}/mcts_decision", response_model=Dict[str, Any])
async def get_trader_mcts_decision(
    trader_id: UUID, 
    simulations: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get the MCTS-based decision for a trader's next move.
    
    Args:
        trader_id: UUID of the trader
        simulations: Number of MCTS simulations to run (default: 100)
        
    Returns:
        MCTS decision details including stats
    """
    trader = db.query(Traders).filter(Traders.trader_id == trader_id).first()
    if trader is None:
        raise HTTPException(status_code=404, detail="Trader not found")
    
    # Only meaningful if trader is in a settlement
    if not trader.current_settlement_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trader is not in a settlement, cannot make a new movement decision"
        )
    
    # Use the game state manager to get MCTS decision
    manager = GameStateManager(db)
    mcts_decision = manager.get_mcts_trader_decision(str(trader_id), simulations)
    
    if mcts_decision["status"] != "success":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"MCTS decision failed: {mcts_decision.get('message', 'Unknown error')}"
        )
    
    return mcts_decision

@router.post("/{trader_id}/complete-task/{task_id}")
async def complete_trader_task(
    trader_id: UUID,
    task_id: UUID,
    character_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Complete a task for a trader and unblock their movement.
    
    Args:
        trader_id: The trader ID
        task_id: The task ID to complete
        character_id: The character completing the task
    """
    from app.game_state.services.trader_service import TraderService
    
    trader_service = TraderService(db)
    result = await trader_service.complete_trader_task(str(task_id), str(character_id))
    
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result

@router.get("/{trader_id}/movement_history")
async def get_trader_movement_history(
    trader_id: UUID,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get the movement history for a trader.
    
    Args:
        trader_id: UUID of the trader
        limit: Maximum number of records to return (default: 100)
        
    Returns:
        List of movement logs
    """
    trader = db.query(Traders).filter(Traders.trader_id == trader_id).first()
    if trader is None:
        raise HTTPException(status_code=404, detail="Trader not found")
    
    logging_service = LoggingService(db)
    movement_logs = logging_service.get_trader_movement_history(str(trader_id), limit)
    
    # Format logs for API response
    formatted_logs = []
    for log in movement_logs:
        formatted_logs.append({
            "timestamp": log.timestamp,
            "trader_id": log.entity_id,
            "trader_name": log.entity_name,
            "action_type": log.action_type,
            "action_subtype": log.action_subtype,
            "from_location": {
                "id": log.from_location_id,
                "type": log.from_location_type,
                "name": log.from_location_name
            },
            "to_location": {
                "id": log.to_location_id,
                "type": log.to_location_type,
                "name": log.to_location_name
            },
            "details": log.details,
            "game_day": log.game_day
        })
    
    return formatted_logs

@router.get("/{trader_id}/action_history")
async def get_trader_action_history(
    trader_id: UUID,
    limit: int = 100,
    action_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get the complete action history for a trader.
    
    Args:
        trader_id: UUID of the trader
        limit: Maximum number of records to return (default: 100)
        action_type: Optional filter for specific action type ('movement', 'trade', etc.)
        
    Returns:
        List of action logs
    """
    trader = db.query(Traders).filter(Traders.trader_id == trader_id).first()
    if trader is None:
        raise HTTPException(status_code=404, detail="Trader not found")
    
    # Query action logs
    query = db.query(EntityActionLog).filter(
        EntityActionLog.entity_id == str(trader_id),
        EntityActionLog.entity_type == 'trader'
    )
    
    if action_type:
        query = query.filter(EntityActionLog.action_type == action_type)
    
    action_logs = query.order_by(EntityActionLog.timestamp.desc()).limit(limit).all()
    
    # Format logs for API response
    formatted_logs = []
    for log in action_logs:
        formatted_logs.append({
            "timestamp": log.timestamp,
            "trader_id": log.entity_id,
            "trader_name": log.entity_name,
            "action_type": log.action_type,
            "action_subtype": log.action_subtype,
            "from_location": {
                "id": log.from_location_id,
                "type": log.from_location_type,
                "name": log.from_location_name
            } if log.from_location_id else None,
            "to_location": {
                "id": log.to_location_id,
                "type": log.to_location_type,
                "name": log.to_location_name
            } if log.to_location_id else None,
            "related_entity": {
                "id": log.related_entity_id,
                "type": log.related_entity_type,
                "name": log.related_entity_name
            } if log.related_entity_id else None,
            "details": log.details,
            "game_day": log.game_day
        })
    
    return formatted_logs