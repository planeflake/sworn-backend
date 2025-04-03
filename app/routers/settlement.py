# routers/settlement.py
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Text
from sqlalchemy.sql import text
from uuid import UUID
import json
import uuid
from datetime import datetime
from fastapi.encoders import jsonable_encoder

from database.connection import get_db, SessionLocal
from app.game_state.services.settlement_service import SettlementService
from app.workers.settlement_worker import (
    process_settlement_growth, 
    start_building_construction as worker_start_building_construction,
    start_building_repair,
    create_new_settlement
)
from app.models.resource import Resource #, ResourceRequirement
from app.models.core import (
    Settlements, 
    SettlementBuildings, 
    SettlementResources, 
    ResourceSites, 
    ResourceSiteTypes,
    ResourceSiteStages,
    ResourceTypes,
    BuildingTypes
)
from app.schemas.settlement import (
    SettlementResponse, 
    BuildingResponse, 
    ResourceResponse, 
    ResourceSiteResponse,
    ResourceSiteStageResponse,
    ResourceSiteCreate,
    SettlementCreate,
    BuildingCreate
)

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

@router.get("/{settlement_id}/buildings")  # , response_model=List[BuildingResponse])
async def get_settlement_buildings(settlement_id: UUID, db: Session = Depends(get_db)):
    buildings = (
        db.query(SettlementBuildings, BuildingTypes.building_name)
        .join(BuildingTypes, SettlementBuildings.building_type_id == BuildingTypes.building_type_id)
        .filter(SettlementBuildings.settlement_id == settlement_id)
        .all()
    )
    
    # Serialise the query result
    serialised_buildings = [
        {
            "settlement_building": jsonable_encoder(building[0]),  # Serialize SettlementBuildings
            "building_name": building[1],  # Building name is already a string
        }
        for building in buildings
    ]
    
    return serialised_buildings

@router.get("/{settlement_id}/resources")  #,response_model=List[ResourceResponse])
async def get_settlement_resources(settlement_id: UUID, db: Session = Depends(get_db)):
    results = (
        db.query(SettlementResources, Resource.resource_name)
        .join(Resource, SettlementResources.resource_type_id == Resource.resource_type_id)
        .filter(SettlementResources.settlement_id == settlement_id)
        .all()
    )
    return [
        {
            "id": settlement_resource.settlement_resource_id,
            "settlement_id": settlement_resource.settlement_id,
            "resource_id": settlement_resource.resource_type_id,
            "quantity": settlement_resource.quantity,
            "resource_name": resource_name,
        }
        for settlement_resource, resource_name in results
    ]

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

@router.get("/{settlement_id}/resource-sites", response_model=List[ResourceSiteResponse])
async def get_settlement_resource_sites(settlement_id: UUID, db: Session = Depends(get_db)):
    # Get all resource sites for this settlement
    sites = db.query(ResourceSites).filter(ResourceSites.settlement_id == settlement_id).all()
    
    # Prepare response with full details
    result = []
    for site in sites:
        # Get site type information
        site_type = db.query(ResourceSiteTypes).filter(
            ResourceSiteTypes.site_type_id == site.site_type_id
        ).first()
        
        if not site_type:
            continue
        
        # Get primary resource information
        primary_resource = None
        if site_type.primary_resource_type_id:
            resource = db.query(ResourceTypes).filter(
                ResourceTypes.resource_type_id == site_type.primary_resource_type_id
            ).first()
            if resource:
                primary_resource = resource.resource_name
        
        # Get stage details
        stage_details = None
        stage = db.query(ResourceSiteStages).filter(
            ResourceSiteStages.site_type_id == site.site_type_id,
            ResourceSiteStages.stage_code == site.current_stage
        ).first()
        
        if stage:
            # Parse JSON fields for the response
            production_rates = {}
            if stage.production_rates:
                try:
                    production_rates = json.loads(stage.production_rates)
                except:
                    pass
                    
            required_resources = None
            if stage.required_resources:
                try:
                    required_resources = json.loads(stage.required_resources)
                except:
                    pass
            
            settlement_effects = None
            if stage.settlement_effects:
                try:
                    settlement_effects = json.loads(stage.settlement_effects)
                except:
                    pass
            
            stage_details = {
                "stage_id": stage.stage_id,
                "stage_code": stage.stage_code,
                "stage_name": stage.stage_name,
                "stage_description": stage.stage_description,
                "building_requirement": stage.building_requirement,
                "required_resources": required_resources,
                "production_rates": production_rates,
                "settlement_effects": settlement_effects,
                "development_cost": stage.development_cost,
                "next_stage": stage.next_stage
            }
        
        # Create the combined response
        site_response = {
            "site_id": site.site_id,
            "settlement_id": site.settlement_id,
            "site_type_id": site.site_type_id,
            "current_stage": site.current_stage,
            "depletion_level": site.depletion_level,
            "development_level": site.development_level,
            "production_multiplier": site.production_multiplier,
            "associated_building_id": site.associated_building_id,
            "discovery_date": site.discovery_date,
            "last_updated": site.last_updated,
            "site_name": site_type.site_name,
            "site_category": site_type.site_category,
            "primary_resource": primary_resource,
            "description": site_type.description,
            "stage_details": stage_details
        }
        
        result.append(site_response)
    
    return result

@router.post("/{settlement_id}/resource-sites/{site_id}/develop")
async def develop_resource_site(
    settlement_id: UUID,
    site_id: UUID,
    character_id: UUID,
    db: Session = Depends(get_db)
):
    # Check if site exists and belongs to settlement
    site = db.query(ResourceSites).filter(
        ResourceSites.site_id == site_id,
        ResourceSites.settlement_id == settlement_id
    ).first()
    
    if site is None:
        raise HTTPException(status_code=404, detail="Resource site not found")
    
    # Get the current stage information
    current_stage = db.query(ResourceSiteStages).filter(
        ResourceSiteStages.site_type_id == site.site_type_id,
        ResourceSiteStages.stage_code == site.current_stage
    ).first()
    
    if not current_stage:
        raise HTTPException(status_code=404, detail="Current site stage information not found")
    
    # Check if there's a next stage to develop to
    if not current_stage.next_stage:
        raise HTTPException(status_code=400, detail="This site cannot be developed further")
    
    # Get the next stage information
    next_stage = db.query(ResourceSiteStages).filter(
        ResourceSiteStages.site_type_id == site.site_type_id,
        ResourceSiteStages.stage_code == current_stage.next_stage
    ).first()
    
    if not next_stage:
        raise HTTPException(status_code=404, detail="Next stage information not found")
    
    # Check if the required resources are available in the settlement
    if next_stage.required_resources:
        try:
            required_resources = json.loads(next_stage.required_resources)
            
            for resource_code, amount in required_resources.items():
                # Get the resource type ID
                resource_type = db.query(ResourceTypes).filter(
                    ResourceTypes.resource_code == resource_code
                ).first()
                
                if not resource_type:
                    raise HTTPException(status_code=400, detail=f"Required resource '{resource_code}' not found")
                
                # Check if the settlement has enough of this resource
                settlement_resource = db.query(SettlementResources).filter(
                    SettlementResources.settlement_id == settlement_id,
                    SettlementResources.resource_type_id == resource_type.resource_type_id
                ).first()
                
                if not settlement_resource or settlement_resource.quantity < amount:
                    raise HTTPException(status_code=400, 
                                      detail=f"Not enough {resource_code}. Need {amount}, have {settlement_resource.quantity if settlement_resource else 0}")
                
                # Consume the resources
                settlement_resource.quantity -= amount
                settlement_resource.last_updated = datetime.now()
                
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="Error parsing required resources")
    
    # Update the site to the next stage
    site.current_stage = next_stage.stage_code
    site.last_updated = datetime.now()
    
    # Reset depletion level for the new stage
    if site.depletion_level is not None:
        site.depletion_level = 0.0
    
    # Increase development level
    site.development_level = 0.0  # Start at 0 for the new stage
    
    # If the stage requires a building, we would handle that here
    # (This would be implemented based on your building system)
    
    db.commit()
    
    return {
        "status": "success",
        "message": f"Site developed to {next_stage.stage_name}",
        "site_id": str(site_id),
        "settlement_id": str(settlement_id),
        "new_stage": next_stage.stage_code
    }

@router.post("/{settlement_id}/resource-sites", response_model=ResourceSiteResponse)
async def add_resource_site(
    settlement_id: UUID,
    site_data: ResourceSiteCreate,
    db: Session = Depends(get_db)
):
    """Add a new resource site to a settlement"""
    # Check if settlement exists
    settlement = db.query(Settlements).filter(Settlements.settlement_id == settlement_id).first()
    if not settlement:
        raise HTTPException(status_code=404, detail="Settlement not found")
    
    # Check if site type exists
    site_type = db.query(ResourceSiteTypes).filter(
        ResourceSiteTypes.site_type_id == site_data.site_type_id
    ).first()
    if not site_type:
        raise HTTPException(status_code=404, detail="Resource site type not found")
    
    # Check if the site type is compatible with the settlement's area type
    compatible_areas = []
    if site_type.compatible_area_types:
        try:
            compatible_areas = json.loads(site_type.compatible_area_types)
        except json.JSONDecodeError:
            pass
    
    if settlement.area_type not in compatible_areas:
        raise HTTPException(
            status_code=400, 
            detail=f"Site type '{site_type.site_name}' is not compatible with area type '{settlement.area_type}'"
        )
    
    # Create new resource site
    new_site = ResourceSites(
        site_id=str(uuid.uuid4()),
        settlement_id=str(settlement_id),
        site_type_id=str(site_data.site_type_id),
        current_stage=site_data.current_stage,
        depletion_level=0.0,
        development_level=0.0,
        production_multiplier=site_data.production_multiplier,
        discovery_date=datetime.now() if site_data.current_stage != "undiscovered" else None,
        last_updated=datetime.now(),
        associated_building_id=None
    )
    
    db.add(new_site)
    db.commit()
    db.refresh(new_site)
    
    # Prepare response with full details (similar to get_settlement_resource_sites)
    # Get primary resource information
    primary_resource = None
    if site_type.primary_resource_type_id:
        resource = db.query(ResourceTypes).filter(
            ResourceTypes.resource_type_id == site_type.primary_resource_type_id
        ).first()
        if resource:
            primary_resource = resource.resource_name
    
    # Get stage details
    stage_details = None
    stage = db.query(ResourceSiteStages).filter(
        ResourceSiteStages.site_type_id == new_site.site_type_id,
        ResourceSiteStages.stage_code == new_site.current_stage
    ).first()
    
    if stage:
        # Parse JSON fields for the response
        production_rates = {}
        if stage.production_rates:
            try:
                production_rates = json.loads(stage.production_rates)
            except:
                pass
                
        required_resources = None
        if stage.required_resources:
            try:
                required_resources = json.loads(stage.required_resources)
            except:
                pass
        
        settlement_effects = None
        if stage.settlement_effects:
            try:
                settlement_effects = json.loads(stage.settlement_effects)
            except:
                pass
        
        stage_details = {
            "stage_id": stage.stage_id,
            "stage_code": stage.stage_code,
            "stage_name": stage.stage_name,
            "stage_description": stage.stage_description,
            "building_requirement": stage.building_requirement,
            "required_resources": required_resources,
            "production_rates": production_rates,
            "settlement_effects": settlement_effects,
            "development_cost": stage.development_cost,
            "next_stage": stage.next_stage
        }
    
    return {
        "site_id": new_site.site_id,
        "settlement_id": new_site.settlement_id,
        "site_type_id": new_site.site_type_id,
        "current_stage": new_site.current_stage,
        "depletion_level": new_site.depletion_level,
        "development_level": new_site.development_level,
        "production_multiplier": new_site.production_multiplier,
        "associated_building_id": new_site.associated_building_id,
        "discovery_date": new_site.discovery_date,
        "last_updated": new_site.last_updated,
        "site_name": site_type.site_name,
        "site_category": site_type.site_category,
        "primary_resource": primary_resource,
        "description": site_type.description,
        "stage_details": stage_details
    }

# Added from settlement_router_new.py - new endpoints that use the class-based architecture
@router.post("/new", response_model=dict)
async def create_settlement(
    settlement_data: SettlementCreate, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Create a new settlement using the class-based architecture.
    """
    # Queue task in the background
    background_tasks.add_task(
        create_new_settlement,
        name=settlement_data.name,
        location_id=settlement_data.location_id,
        world_id=settlement_data.world_id
    )
    
    return {
        "status": "pending",
        "message": f"Settlement creation started for {settlement_data.name}",
        "location_id": settlement_data.location_id,
        "world_id": settlement_data.world_id
    }

@router.post("/{settlement_id}/buildings/new", response_model=dict)
async def start_building_construction_new(
    settlement_id: str,
    building_data: BuildingCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Start construction of a new building in a settlement using the class-based architecture.
    """
    # Check if settlement exists
    settlement = db.query(Settlements).filter(Settlements.settlement_id == settlement_id).first()
    if settlement is None:
        raise HTTPException(status_code=404, detail="Settlement not found")
    
    # Queue task in the background
    background_tasks.add_task(
        worker_start_building_construction,
        settlement_id=settlement_id,
        building_type=building_data.building_type
    )
    
    return {
        "status": "pending",
        "message": f"Building construction started for {building_data.building_type}",
        "settlement_id": settlement_id
    }

@router.post("/{settlement_id}/buildings/{building_id}/repair", response_model=dict)
async def repair_building(
    settlement_id: str,
    building_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Start repair of a damaged building.
    """
    # Check if building exists and is damaged
    building = db.query(SettlementBuildings).filter(
        SettlementBuildings.building_id == building_id,
        SettlementBuildings.settlement_id == settlement_id
    ).first()
    
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    
    if not getattr(building, 'is_damaged', False):
        raise HTTPException(status_code=400, detail="Building is not damaged")
    
    # Queue task in the background
    background_tasks.add_task(
        start_building_repair,
        settlement_id=settlement_id,
        building_id=building_id
    )
    
    return {
        "status": "pending",
        "message": f"Building repair started for {building.building_type}",
        "settlement_id": settlement_id,
        "building_id": building_id
    }

@router.post("/{settlement_id}/process", response_model=dict)
async def trigger_settlement_processing(
    settlement_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Manually trigger processing for a settlement.
    """
    # Check if settlement exists
    settlement = db.query(Settlements).filter(Settlements.settlement_id == settlement_id).first()
    if settlement is None:
        raise HTTPException(status_code=404, detail="Settlement not found")
    
    # Queue task in the background
    background_tasks.add_task(
        process_settlement_growth,
        settlement_id=settlement_id
    )
    
    return {
        "status": "pending",
        "message": f"Settlement processing started for {settlement.settlement_name}",
        "settlement_id": settlement_id
    }

# Entity-based endpoint that uses the class-based architecture
@router.get("/{settlement_id}/entity", response_model=dict)
async def get_settlement_entity(settlement_id: str, db: Session = Depends(get_db)):
    """
    Get a specific settlement by ID, using the entity-based system.
    """
    # Query the database
    settlement = db.query(Settlements).filter(Settlements.settlement_id == settlement_id).first()
    if settlement is None:
        raise HTTPException(status_code=404, detail="Settlement not found")
    
    # Create a service instance
    settlement_service = SettlementService(db)
    
    # Use the manager to load the entity
    settlement_entity = settlement_service.settlement_manager.load_settlement(settlement_id)
    if settlement_entity:
        # Return the entity data
        return {
            "settlement_id": settlement_id,
            "settlement_name": settlement.settlement_name,
            "entity_data": settlement_entity.to_dict()
        }
    else:
        raise HTTPException(status_code=404, detail="Settlement entity not found")
    
@router.get("/{settlement_id}/non_operational_requirements") #, response_model=List[ResourceRequirement])
def get_non_operational_requirements(settlement_id: str):
    query = text("""
        SELECT 
            s.settlement_id,
            s.settlement_name,
            sb.settlement_building_id,
            bt.building_name,
            rr.resource_id,
            rt.resource_name,
            rr.required,
            COALESCE(sr.quantity, 0) AS available,
            GREATEST(rr.required - COALESCE(sr.quantity, 0), 0) AS lacking
        FROM settlement_buildings sb
        JOIN building_types bt 
          ON sb.building_type_id = bt.building_type_id
        JOIN settlements s 
          ON s.settlement_id = sb.settlement_id
        -- Unpack the resource_requirements JSON object into key/value pairs.
        CROSS JOIN LATERAL (
          SELECT 
            key AS resource_id,
            value::int AS required
          FROM jsonb_each(bt.resource_requirements)
        ) AS rr
        -- Left join the settlement's resource inventory.
        LEFT JOIN settlement_resources sr 
          ON sr.settlement_id = sb.settlement_id 
          AND sr.resource_type_id::text = rr.resource_id
        -- Join resource_types to get the resource name.
        LEFT JOIN resource_types rt
          ON rt.resource_type_id::text = rr.resource_id
        WHERE sb.settlement_id = :settlement_id
          AND sb.is_operational = false;
    """)

    with SessionLocal() as db:
        results = db.execute(query, {"settlement_id": settlement_id}).fetchall()
        if not results:
            raise HTTPException(status_code=404, detail="No non-operational building resources found for this settlement.")

        # Convert the results using _mapping so that we can create dicts from each row.
        requirements = [dict(row._mapping) for row in results]
        
    return requirements