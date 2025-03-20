# routers/area.py
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
import json
import random
from datetime import datetime

from database.connection import get_db
from models.core import (
    Areas, 
    AreaEncounterTypes,
    AreaEncounterOutcomes,
    AreaEncounters,
    TravelRoutes,
    Settlements,
    Characters,
    Traders
)
from app.schemas.area import (
    AreaResponse,
    AreaCreate,
    EncounterTypeResponse,
    EncounterOutcomeResponse,
    ActiveEncounterResponse,
    EncounterResolveRequest,
    EncounterResolveResponse,
    TravelRequest,
    TravelResponse,
    RouteResponse
)
from workers.area_worker import generate_encounter, resolve_encounter

router = APIRouter(prefix="/areas", tags=["areas"])

@router.get("/", response_model=List[AreaResponse])
async def get_areas(world_id: Optional[UUID] = None, db: Session = Depends(get_db)):
    """Get all areas, optionally filtered by world"""
    query = db.query(Areas)
    if world_id:
        query = query.filter(Areas.world_id == str(world_id))
        
    areas = query.all()
    
    # Convert JSON fields to Python objects
    result = []
    for area in areas:
        connected_settlements = json.loads(area.connected_settlements) if area.connected_settlements else []
        connected_areas = json.loads(area.connected_areas) if area.connected_areas else []
        
        area_dict = {
            "area_id": area.area_id,
            "world_id": area.world_id,
            "theme_id": area.theme_id,
            "area_name": area.area_name,
            "area_type": area.area_type,
            "location_x": area.location_x,
            "location_y": area.location_y,
            "radius": area.radius,
            "danger_level": area.danger_level,
            "resource_richness": area.resource_richness,
            "created_at": area.created_at,
            "last_updated": area.last_updated,
            "description": area.description,
            "connected_settlements": connected_settlements,
            "connected_areas": connected_areas
        }
        result.append(area_dict)
    
    return result

@router.get("/{area_id}", response_model=AreaResponse)
async def get_area(area_id: UUID, db: Session = Depends(get_db)):
    """Get details for a specific area"""
    area = db.query(Areas).filter(Areas.area_id == str(area_id)).first()
    if not area:
        raise HTTPException(status_code=404, detail="Area not found")
    
    # Convert JSON fields to Python objects
    connected_settlements = json.loads(area.connected_settlements) if area.connected_settlements else []
    connected_areas = json.loads(area.connected_areas) if area.connected_areas else []
    
    return {
        "area_id": area.area_id,
        "world_id": area.world_id,
        "theme_id": area.theme_id,
        "area_name": area.area_name,
        "area_type": area.area_type,
        "location_x": area.location_x,
        "location_y": area.location_y,
        "radius": area.radius,
        "danger_level": area.danger_level,
        "resource_richness": area.resource_richness,
        "created_at": area.created_at,
        "last_updated": area.last_updated,
        "description": area.description,
        "connected_settlements": connected_settlements,
        "connected_areas": connected_areas
    }

@router.post("/", response_model=AreaResponse)
async def create_area(area_data: AreaCreate, db: Session = Depends(get_db)):
    """Create a new area"""
    # Convert Python lists to JSON strings
    connected_settlements = json.dumps([str(s) for s in area_data.connected_settlements])
    connected_areas = json.dumps([str(a) for a in area_data.connected_areas])
    
    new_area = Areas(
        area_id=str(uuid.uuid4()),
        world_id=str(area_data.world_id),
        theme_id=str(area_data.theme_id) if area_data.theme_id else None,
        area_name=area_data.area_name,
        area_type=area_data.area_type,
        location_x=area_data.location_x,
        location_y=area_data.location_y,
        radius=area_data.radius,
        danger_level=area_data.danger_level,
        resource_richness=area_data.resource_richness,
        created_at=datetime.now(),
        last_updated=datetime.now(),
        description=area_data.description,
        connected_settlements=connected_settlements,
        connected_areas=connected_areas
    )
    
    db.add(new_area)
    db.commit()
    db.refresh(new_area)
    
    # Convert JSON fields back to Python objects for response
    connected_settlements_list = json.loads(new_area.connected_settlements) if new_area.connected_settlements else []
    connected_areas_list = json.loads(new_area.connected_areas) if new_area.connected_areas else []
    
    return {
        "area_id": new_area.area_id,
        "world_id": new_area.world_id,
        "theme_id": new_area.theme_id,
        "area_name": new_area.area_name,
        "area_type": new_area.area_type,
        "location_x": new_area.location_x,
        "location_y": new_area.location_y,
        "radius": new_area.radius,
        "danger_level": new_area.danger_level,
        "resource_richness": new_area.resource_richness,
        "created_at": new_area.created_at,
        "last_updated": new_area.last_updated,
        "description": new_area.description,
        "connected_settlements": connected_settlements_list,
        "connected_areas": connected_areas_list
    }

@router.get("/{area_id}/encounters", response_model=List[ActiveEncounterResponse])
async def get_area_encounters(area_id: UUID, active_only: bool = True, db: Session = Depends(get_db)):
    """Get encounters for a specific area"""
    query = db.query(AreaEncounters).filter(AreaEncounters.area_id == str(area_id))
    
    if active_only:
        query = query.filter(AreaEncounters.is_active == True)
        
    encounters = query.all()
    
    result = []
    for encounter in encounters:
        # Get the encounter type details
        encounter_type = db.query(AreaEncounterTypes).filter(
            AreaEncounterTypes.encounter_type_id == encounter.encounter_type_id
        ).first()
        
        if not encounter_type:
            continue
            
        # Get the area details
        area = db.query(Areas).filter(Areas.area_id == encounter.area_id).first()
        if not area:
            continue
            
        # Get possible outcomes
        possible_outcomes = []
        if encounter_type.possible_outcomes:
            outcome_ids = json.loads(encounter_type.possible_outcomes)
            outcomes = db.query(AreaEncounterOutcomes).filter(
                AreaEncounterOutcomes.outcome_id.in_(outcome_ids)
            ).all()
            
            for outcome in outcomes:
                outcome_dict = {
                    "outcome_id": outcome.outcome_id,
                    "encounter_type_id": outcome.encounter_type_id,
                    "outcome_code": outcome.outcome_code,
                    "outcome_name": outcome.outcome_name,
                    "outcome_type": outcome.outcome_type,
                    "probability": outcome.probability,
                    "narrative": outcome.narrative,
                    "requirements": json.loads(outcome.requirements) if outcome.requirements else None,
                    "rewards": json.loads(outcome.rewards) if outcome.rewards else None,
                    "penalties": json.loads(outcome.penalties) if outcome.penalties else None
                }
                possible_outcomes.append(outcome_dict)
        
        encounter_dict = {
            "encounter_id": encounter.encounter_id,
            "area_id": encounter.area_id,
            "encounter_type_id": encounter_type.encounter_type_id,
            "encounter_name": encounter_type.encounter_name,
            "encounter_description": encounter_type.description,
            "area_name": area.area_name,
            "current_state": encounter.current_state,
            "created_at": encounter.created_at,
            "possible_outcomes": possible_outcomes
        }
        result.append(encounter_dict)
    
    return result

@router.post("/travel", response_model=TravelResponse)
async def travel_between_areas(travel_req: TravelRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Handle travel between areas, potentially generating an encounter.
    Either current_area_id or current_settlement_id must be provided.
    """
    if not travel_req.character_id and not travel_req.trader_id:
        raise HTTPException(status_code=400, detail="Either character_id or trader_id must be provided")
        
    if not travel_req.current_area_id and not travel_req.current_settlement_id:
        raise HTTPException(status_code=400, detail="Either current_area_id or current_settlement_id must be provided")
    
    # Get the destination area
    destination = db.query(Areas).filter(Areas.area_id == str(travel_req.destination_area_id)).first()
    if not destination:
        raise HTTPException(status_code=404, detail="Destination area not found")
    
    # Validate that the actor can travel to the destination
    is_valid_travel = False
    
    if travel_req.current_area_id:
        # Check if areas are connected
        current_area = db.query(Areas).filter(Areas.area_id == str(travel_req.current_area_id)).first()
        if not current_area:
            raise HTTPException(status_code=404, detail="Current area not found")
            
        connected_areas = json.loads(current_area.connected_areas) if current_area.connected_areas else []
        is_valid_travel = str(travel_req.destination_area_id) in connected_areas
    else:
        # Check if area is connected to settlement
        current_settlement = db.query(Settlements).filter(
            Settlements.settlement_id == str(travel_req.current_settlement_id)
        ).first()
        if not current_settlement:
            raise HTTPException(status_code=404, detail="Current settlement not found")
            
        connected_settlements = json.loads(destination.connected_settlements) if destination.connected_settlements else []
        is_valid_travel = str(travel_req.current_settlement_id) in connected_settlements
    
    if not is_valid_travel:
        raise HTTPException(status_code=400, detail="Cannot travel directly to the specified destination")
    
    # If validation passed, generate a possible encounter
    actor_id = travel_req.character_id if travel_req.character_id else travel_req.trader_id
    actor_type = "character" if travel_req.character_id else "trader"
    
    # Generate encounter asynchronously
    background_tasks.add_task(
        generate_encounter,
        character_id=str(travel_req.character_id) if travel_req.character_id else None,
        trader_id=str(travel_req.trader_id) if travel_req.trader_id else None,
        area_id=str(travel_req.destination_area_id)
    )
    
    # Calculate travel time (simplified)
    travel_time = 1  # Default time unit
    
    return {
        "status": "success",
        "destination_reached": True,
        "encounter_generated": True,
        "travel_time": travel_time,
        "message": f"Traveling to {destination.area_name}. Any encounters will be processed asynchronously."
    }

@router.post("/encounters/{encounter_id}/resolve", response_model=EncounterResolveResponse)
async def resolve_area_encounter(
    encounter_id: UUID, 
    resolution: EncounterResolveRequest, 
    db: Session = Depends(get_db)
):
    """Resolve an active encounter with a specific outcome"""
    # Check if the encounter exists and is active
    encounter = db.query(AreaEncounters).filter(
        AreaEncounters.encounter_id == str(encounter_id),
        AreaEncounters.is_active == True,
        AreaEncounters.is_completed == False
    ).first()
    
    if not encounter:
        raise HTTPException(status_code=404, detail="Active encounter not found")
    
    # Call the worker to resolve the encounter
    result = resolve_encounter(
        encounter_id=str(encounter_id),
        character_id=str(resolution.character_id) if resolution.character_id else None,
        trader_id=str(resolution.trader_id) if resolution.trader_id else None,
        chosen_outcome_code=resolution.chosen_outcome_code
    )
    
    if result.get("status") != "success":
        raise HTTPException(status_code=400, detail=result.get("error", "Error resolving encounter"))
    
    return {
        "encounter_id": encounter_id,
        "outcome_name": result.get("outcome_name", "Unknown"),
        "outcome_type": result.get("outcome_type", "neutral"),
        "narrative": result.get("narrative", "The encounter was resolved."),
        "rewards": result.get("rewards", {}),
        "penalties": result.get("penalties", {})
    }

@router.get("/routes/between-settlements", response_model=List[RouteResponse])
async def get_routes_between_settlements(
    start_settlement_id: Optional[UUID] = None,
    end_settlement_id: Optional[UUID] = None,
    world_id: Optional[UUID] = None,
    db: Session = Depends(get_db)
):
    """Get travel routes between settlements"""
    query = db.query(TravelRoutes)
    
    if world_id:
        query = query.filter(TravelRoutes.world_id == str(world_id))
        
    if start_settlement_id:
        query = query.filter(TravelRoutes.start_settlement_id == str(start_settlement_id))
        
    if end_settlement_id:
        query = query.filter(TravelRoutes.end_settlement_id == str(end_settlement_id))
    
    routes = query.all()
    
    result = []
    for route in routes:
        # Get settlement names
        start_settlement = db.query(Settlements).filter(
            Settlements.settlement_id == route.start_settlement_id
        ).first()
        
        end_settlement = db.query(Settlements).filter(
            Settlements.settlement_id == route.end_settlement_id
        ).first()
        
        if not start_settlement or not end_settlement:
            continue
            
        # Get areas in path
        area_ids = json.loads(route.path) if route.path else []
        areas = db.query(Areas).filter(Areas.area_id.in_(area_ids)).all()
        
        area_responses = []
        for area in areas:
            connected_settlements = json.loads(area.connected_settlements) if area.connected_settlements else []
            connected_areas = json.loads(area.connected_areas) if area.connected_areas else []
            
            area_dict = {
                "area_id": area.area_id,
                "world_id": area.world_id,
                "theme_id": area.theme_id,
                "area_name": area.area_name,
                "area_type": area.area_type,
                "location_x": area.location_x,
                "location_y": area.location_y,
                "radius": area.radius,
                "danger_level": area.danger_level,
                "resource_richness": area.resource_richness,
                "created_at": area.created_at,
                "last_updated": area.last_updated,
                "description": area.description,
                "connected_settlements": connected_settlements,
                "connected_areas": connected_areas
            }
            area_responses.append(area_dict)
        
        route_dict = {
            "route_id": route.route_id,
            "start_settlement_id": route.start_settlement_id,
            "start_settlement_name": start_settlement.settlement_name,
            "end_settlement_id": route.end_settlement_id,
            "end_settlement_name": end_settlement.settlement_name,
            "areas": area_responses,
            "total_distance": route.total_distance,
            "danger_level": route.danger_level,
            "path_condition": route.path_condition,
            "travel_time": route.travel_time
        }
        result.append(route_dict)
    
    return result