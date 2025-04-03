# app/game_state/managers/building_manager.py
import logging
import uuid
from typing import Dict, List, Optional, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from database.connection import SessionLocal,get_db
from app.models.buildings import BuildingType, SettlementBuilding
from database.connection import SessionLocal
from app.game_state.services.logging_service import LoggingService

logger = LoggingService(SessionLocal())

class BuildingManager:
    """
    Manager for buildings and building types.
    Handles persistence, loading, and lifecycle of buildings.
    """
    
    def __init__(self, db=None):
        """
        Initialize the BuildingManager.
        
        Args:
            db (Session, optional): Database session
        """
        self.db = db or SessionLocal()
        self.building_types = {}  # Cache of building types
        
    def get_building_type(self, building_type_id: str) -> Optional[Dict[str, Any]]:
        """
        Get building type information by ID.
        
        Args:
            building_type_id (str): The building type ID
            
        Returns:
            Dict[str, Any]: Building type details or None if not found
        """
        # Check cache first
        if building_type_id in self.building_types:
            return self.building_types[building_type_id]
        
        try:
            # Try to get from database
            building_type = self.db.query(BuildingType).filter(
                BuildingType.building_type_id == building_type_id
            ).first()
            
            if building_type:
                # Convert to dict
                building_data = {
                    "id": str(building_type.building_type_id),
                    "code": building_type.building_code,
                    "name": building_type.building_name,
                    "category": building_type.building_category,
                    "description": building_type.description,
                    "construction_time": building_type.construction_time,
                    "resource_requirements": building_type.resource_requirements,
                    "personnel_requirements": building_type.personnel_requirements,
                    "effects": building_type.effects,
                    "upgrade_path": building_type.upgrade_path,
                    "area_type_bonuses": building_type.area_type_bonuses,
                    # Add production_type and rate if you have them
                    "production_type": getattr(building_type, "production_type", None),
                    "production_rate": getattr(building_type, "production_rate", 0)
                }
                
                # Add to cache
                self.building_types[building_type_id] = building_data
                return building_data
        except Exception as e:
            logger.error(f"Error fetching building type {building_type_id}: {e}")
        
        return None
    
    def get_building_type_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        """
        Get building type information by code.
        
        Args:
            code (str): The building type code
            
        Returns:
            Dict[str, Any]: Building type details or None if not found
        """
        try:
            # Try to find in cache first
            for bt_id, bt_data in self.building_types.items():
                if bt_data.get("code") == code:
                    return bt_data
            
            # Not in cache, fetch from database
            building_type = self.db.query(BuildingType).filter(
                BuildingType.building_code == code
            ).first()
            
            if building_type:
                # Get by ID which will add to cache
                return self.get_building_type(str(building_type.building_type_id))
        except Exception as e:
            logger.error(f"Error fetching building type by code {code}: {e}")
        
        return None
    
    def get_settlement_buildings(self, settlement_id: str) -> List[Dict[str, Any]]:
        """
        Get all buildings for a settlement.
        
        Args:
            settlement_id (str): The settlement ID
            
        Returns:
            List[Dict[str, Any]]: List of buildings with their details
        """
        try:
            buildings = self.db.query(SettlementBuilding).filter(
                SettlementBuilding.settlement_id == settlement_id
            ).all()
            
            building_data = []
            for building in buildings:
                # Get building type details
                building_type = self.get_building_type(str(building.building_type_id)) if building.building_type_id else None
                
                data = {
                    "building_id": str(building.settlement_building_id),
                    "type": str(building.building_type_id) if building.building_type_id else None,
                    "type_name": building_type.get("name") if building_type else "Unknown",
                    "construction_status": building.construction_status,
                    "construction_progress": float(building.construction_progress) if building.construction_progress else 0,
                    "health": building.health,
                    "is_operational": building.is_operational,
                    "staff_assigned": building.staff_assigned or {},
                    "constructed_at": building.constructed_at.isoformat() if building.constructed_at else None,
                    "last_updated": building.last_updated.isoformat() if building.last_updated else None
                }
                
                building_data.append(data)
            
            return building_data
        except Exception as e:
            logger.error(f"Error fetching buildings for settlement {settlement_id}: {e}")
            return []
    
    def update_buildings(self, settlement_id: str, buildings: List[Dict[str, Any]]) -> int:
        """
        Update multiple buildings for a settlement.
        
        Args:
            settlement_id (str): The settlement ID
            buildings (List[Dict[str, Any]]): List of building data to update
            
        Returns:
            int: Number of buildings updated
        """
        try:
            # Ensure settlement_id is a UUID
            if isinstance(settlement_id, str):
                settlement_id = UUID(settlement_id)
            
            # Get existing buildings from database
            db_buildings = self.db.query(SettlementBuilding).filter(
                SettlementBuilding.settlement_id == settlement_id
            ).all()
            
            # Map by ID for easier lookup
            db_buildings_map = {str(b.settlement_building_id): b for b in db_buildings}
            
            # Track updates
            updated_count = 0
            
            # Update each building
            for building_data in buildings:
                building_id = building_data.get("building_id")
                
                if building_id in db_buildings_map:
                    db_building = db_buildings_map[building_id]
                    
                    # Update fields
                    if "construction_status" in building_data:
                        db_building.construction_status = building_data["construction_status"]
                    
                    if "construction_progress" in building_data:
                        db_building.construction_progress = building_data["construction_progress"]
                    
                    if "health" in building_data:
                        db_building.health = building_data["health"]
                    
                    if "is_operational" in building_data:
                        db_building.is_operational = building_data["is_operational"]
                    
                    if "staff_assigned" in building_data:
                        db_building.staff_assigned = building_data["staff_assigned"]
                    
                    # Handle datetime fields
                    if "constructed_at" in building_data and building_data["constructed_at"]:
                        if isinstance(building_data["constructed_at"], str):
                            db_building.constructed_at = datetime.fromisoformat(building_data["constructed_at"])
                        else:
                            db_building.constructed_at = building_data["constructed_at"]
                    
                    # Always update last_updated
                    db_building.last_updated = datetime.now()
                    
                    updated_count += 1
            
            # Commit changes
            if updated_count > 0:
                self.db.commit()
                logger.info(f"Updated {updated_count} buildings for settlement {settlement_id}")
            
            return updated_count
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating buildings for settlement {settlement_id}: {e}")
            return 0
    
    def create_building(self, settlement_id: str, building_type_id: str, 
                       status: str = "planned", progress: float = 0, 
                       operational: bool = False) -> Optional[str]:
        """
        Create a new building for a settlement.
        
        Args:
            settlement_id (str): The settlement ID
            building_type_id (str): The building type ID
            status (str): Initial construction status
            progress (float): Initial construction progress
            operational (bool): Whether the building is operational
            
        Returns:
            Optional[str]: Building ID if successful, None otherwise
        """
        try:
            # Ensure IDs are UUIDs
            if isinstance(settlement_id, str):
                settlement_id = UUID(settlement_id)
            
            if isinstance(building_type_id, str):
                building_type_id = UUID(building_type_id)
            
            # Create new building
            building_id = uuid.uuid4()
            
            building = SettlementBuilding(
                settlement_building_id=building_id,
                settlement_id=settlement_id,
                building_type_id=building_type_id,
                construction_status=status,
                construction_progress=progress,
                health=100,
                is_operational=operational,
                staff_assigned={},
                constructed_at=datetime.now() if status == "completed" else None,
                last_updated=datetime.now()
            )
            
            self.db.add(building)
            self.db.commit()
            
            logger.info(f"Created new building {building_id} for settlement {settlement_id}")
            return str(building_id)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating building for settlement {settlement_id}: {e}")
            return None
    
    def process_building_construction(self, building_id: str, 
                                     progress_amount: float = 10, 
                                     resources_consumed: Dict[str, int] = None) -> Dict[str, Any]:
        """
        Process construction progress for a building.
        
        Args:
            building_id (str): The building ID
            progress_amount (float): Amount to progress construction by
            resources_consumed (Dict[str, int]): Resources used in this construction step
            
        Returns:
            Dict[str, Any]: Processing result
        """
        try:
            building = self.db.query(SettlementBuilding).filter(
                SettlementBuilding.settlement_building_id == building_id
            ).first()
            
            if not building:
                return {"status": "error", "message": "Building not found"}
            
            # Only process if under construction
            if building.construction_status != "in_progress":
                return {"status": "info", "message": f"Building not under construction, status: {building.construction_status}"}
            
            # Update progress
            current_progress = float(building.construction_progress or 0)
            new_progress = min(100, current_progress + progress_amount)
            building.construction_progress = new_progress
            
            # Check if construction complete
            if new_progress >= 100:
                building.construction_status = "completed"
                building.is_operational = True
                building.construction_progress = 100
                building.constructed_at = datetime.now()
            
            building.last_updated = datetime.now()
            self.db.commit()
            
            return {
                "status": "success",
                "building_id": str(building.settlement_building_id),
                "progress": float(building.construction_progress),
                "is_complete": building.construction_status == "completed",
                "is_operational": building.is_operational
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error processing construction for building {building_id}: {e}")
            return {"status": "error", "message": f"Error processing construction: {str(e)}"}