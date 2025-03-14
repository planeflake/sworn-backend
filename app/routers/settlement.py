# routers/settlement.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from database.connection import get_db
from models.core import Settlements, SettlementBuildings, SettlementResources
from app.schemas.settlement import SettlementResponse, BuildingResponse, ResourceResponse

router = APIRouter(prefix="/settlements", tags=["settlements"])

@router.get("/", response_model=List[SettlementResponse])
async def get_settlements(world_id: Optional[UUID] = None, db: Session = Depends(get_db)):
    query = db.query(Settlements)
    if world_id:
        query = query.filter(Settlements.world_id == world_id)
    settlements = query.all()
    return settlements

@router.get("/{settlement_id}", response_model=SettlementResponse)
async def get_settlement(settlement_id: UUID, db: Session = Depends(get_db)):
    settlement = db.query(Settlements).filter(Settlements.settlement_id == settlement_id).first()
    if settlement is None:
        raise HTTPException(status_code=404, detail="Settlement not found")
    return settlement

@router.get("/{settlement_id}/buildings", response_model=List[BuildingResponse])
async def get_settlement_buildings(settlement_id: UUID, db: Session = Depends(get_db)):
    buildings = db.query(SettlementBuildings).filter(SettlementBuildings.settlement_id == settlement_id).all()
    return buildings

@router.get("/{settlement_id}/resources", response_model=List[ResourceResponse])
async def get_settlement_resources(settlement_id: UUID, db: Session = Depends(get_db)):
    resources = db.query(SettlementResources).filter(SettlementResources.settlement_id == settlement_id).all()
    return resources

@router.post("/{settlement_id}/build/{building_code}")
async def start_building_construction(
    settlement_id: UUID, 
    building_code: str, 
    character_id: UUID,
    db: Session = Depends(get_db)
):
    # This would trigger a worker to start construction
    # Check if character is in settlement, has resources, etc.
    return {
        "status": "Construction initiated", 
        "settlement_id": str(settlement_id), 
        "building": building_code
    }

@router.get("/{settlement_id}/connections")
async def get_settlement_connections(settlement_id: UUID, db: Session = Depends(get_db)):
    settlement = db.query(Settlements).filter(Settlements.settlement_id == settlement_id).first()
    if settlement is None:
        raise HTTPException(status_code=404, detail="Settlement not found")
    return settlement.connections