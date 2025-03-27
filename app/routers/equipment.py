from fastapi import APIRouter, HTTPException, status, Depends
from app.game_state.services.equipment_service import EquipmentService
from app.schemas.equipment import EquipItemRequest, EquipmentResponse
from sqlalchemy.orm import Session
from database.connection import get_db
from typing import Dict, Any

router = APIRouter(
    prefix="/equipment",
    tags=["equipment"]
)

def get_equipment_service(db: Session = Depends(get_db)):
    return EquipmentService(db_session=db)

@router.get("/{character_id}")
async def get_character_equipment(
    character_id: str,
    equipment_service: EquipmentService = Depends(get_equipment_service)
):
    """Get all equipped items for a character."""
    result = equipment_service.get_character_equipment(character_id)
    
    if result["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["message"]
        )
    
    return result

@router.post("/{character_id}/equip")
async def equip_item(
    character_id: str,
    request: EquipItemRequest,
    equipment_service: EquipmentService = Depends(get_equipment_service)
):
    """Equip an item in a specified slot."""
    result = equipment_service.equip_item(
        character_id=character_id,
        item_id=request.item_id,
        slot=request.slot
    )
    
    if result["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    
    return result

@router.post("/{character_id}/unequip/{slot}")
async def unequip_item(
    character_id: str,
    slot: str,
    equipment_service: EquipmentService = Depends(get_equipment_service)
):
    """Unequip an item from a specified slot."""
    result = equipment_service.unequip_item(character_id, slot)
    
    if result["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["message"]
        )
    
    return result

@router.get("/item/{item_id}")
async def inspect_item(
    item_id: str,
    equipment_service: EquipmentService = Depends(get_equipment_service)
):
    """Get detailed information about an item."""
    result = equipment_service.inspect_item(item_id)
    
    if result["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["message"]
        )
    
    return result