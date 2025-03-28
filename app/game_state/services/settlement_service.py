# app/game_state/services/settlement_service.py
import logging
import json
import uuid
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from datetime import datetime

from app.game_state.managers.settlement_manager import SettlementManager
from app.game_state.entities.settlement import Settlement
from app.game_state.entities.resource import Resource
from app.models.core import Settlements, Areas, Worlds, BuildingTypes
# Note: We're importing BuildingTypes from core.py instead of the Building entity class
# The Building entity should only be used for game logic, not for database queries

logger = logging.getLogger(__name__)

class SettlementService:
    """
    Service layer that bridges between Celery tasks and settlement-related game state components.
    This service orchestrates operations between different components of the game_state architecture,
    making it easier to use from the Celery worker tasks and API endpoints.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the settlement service with a database session.
        
        Args:
            db (Session): SQLAlchemy database session
        """
        self.db = db
        self.settlement_manager = SettlementManager()
    
    def process_settlement_growth(self, settlement_id: str) -> Dict[str, Any]:
        """
        Process population growth, resource production, and building construction for a settlement.
        This is the main entry point called by the Celery task.
        
        Args:
            settlement_id (str): The ID of the settlement to process
            
        Returns:
            Dict[str, Any]: Result of the settlement processing
        """
        # Load the settlement entity
        settlement = self.settlement_manager.load_settlement(settlement_id)
        if not settlement:
            logger.error(f"Settlement {settlement_id} not found")
            return {"status": "error", "message": "Settlement not found"}
        
        settlement_name = settlement.settlement_name if settlement.settlement_name else f"Settlement {settlement.settlement_id}"
        logger.info(f"Processing settlement {settlement_name}")
        
        try:
            # Get the settlement's world
            settlement_db = self.db.query(Settlements).filter(Settlements.settlement_id == settlement_id).first()
            if not settlement_db or not settlement_db.world_id:
                return {"status": "error", "message": "Settlement has no associated world"}
            
            world = self.db.query(Worlds).filter(Worlds.world_id == settlement_db.world_id).first()
            if not world:
                return {"status": "error", "message": "Settlement's world not found"}
            
            # Process resource production
            production_result = self._process_resource_production(settlement, world)
            if production_result["status"] != "success":
                logger.error(f"Resource production failed: {production_result.get('message')}")
                return production_result
            
            # Process population growth
            growth_result = self._process_population_growth(settlement, world)
            if growth_result["status"] != "success":
                logger.error(f"Population growth failed: {growth_result.get('message')}")
                return growth_result
            
            # Process building construction/repairs
            building_result = self._process_buildings(settlement)
            if building_result["status"] != "success":
                logger.error(f"Building processing failed: {building_result.get('message')}")
                return building_result
            
            # Save settlement changes
            self.settlement_manager.save_settlement(settlement)
            
            return {
                "status": "success",
                "production": production_result.get("resources", {}),
                "population": growth_result.get("population", {}),
                "buildings": building_result.get("buildings", [])
            }
            
        except Exception as e:
            logger.exception(f"Error processing settlement {settlement_id}: {e}")
            return {"status": "error", "message": f"Error processing settlement: {str(e)}"}
    
    def _process_resource_production(self, settlement: Settlement, world: Any) -> Dict[str, Any]:
        """
        Process resource production for a settlement.
        
        Args:
            settlement (Settlement): The settlement entity
            world (Any): The world database record
            
        Returns:
            Dict[str, Any]: Result of resource production
        """
        try:
            logger.info(f"Processing resource production for settlement {settlement.settlement_name}")
            
            # Get current season for production modifiers
            current_season = world.current_season if hasattr(world, 'current_season') else "summer"
            
            # Get settlement's resource production buildings
            settlement_db = self.db.query(Settlements).filter(
                Settlements.settlement_id == settlement.settlement_id
            ).first()
            
            if not settlement_db:
                return {"status": "error", "message": "Settlement database record not found"}
            
            # Get building info for the settlement
            from app.models.core import BuildingTypes
            
            # Since we don't have a Buildings table, we'll create a placeholder
            # empty list for now - in a real implementation, this would query the
            # appropriate database table for buildings
            buildings = []
            
            # Log that we're using a placeholder implementation
            logger.info(f"Using placeholder implementation for buildings in settlement {settlement.settlement_id}")
            
            # Calculate resource production based on buildings
            resources_produced = {}
            for building in buildings:
                if not hasattr(building, 'production_type') or not building.production_type:
                    continue
                
                # Calculate base production
                base_production = building.production_rate or 1
                
                # Apply seasonal modifiers
                seasonal_modifier = 1.0
                if building.production_type == "food" and current_season == "winter":
                    seasonal_modifier = 0.5
                elif building.production_type == "wood" and current_season == "autumn":
                    seasonal_modifier = 1.2
                
                # Final production amount
                production_amount = int(base_production * seasonal_modifier)
                
                # Add to total
                if building.production_type in resources_produced:
                    resources_produced[building.production_type] += production_amount
                else:
                    resources_produced[building.production_type] = production_amount
            
            # Update settlement resources in database
            for resource_type, amount in resources_produced.items():
                # Check if resource already exists
                resource = self.db.query(Resource).filter(
                    Resource.settlement_id == settlement.settlement_id,
                    Resource.resource_type == resource_type
                ).first()
                
                if resource:
                    # Update existing resource
                    resource.amount += amount
                else:
                    # Create new resource entry
                    new_resource = Resource(
                        resource_id=str(uuid.uuid4()),
                        settlement_id=settlement.settlement_id,
                        resource_type=resource_type,
                        amount=amount
                    )
                    self.db.add(new_resource)
            
            # Commit changes
            self.db.commit()
            
            # Also update the settlement entity
            for resource_type, amount in resources_produced.items():
                current_amount = settlement.get_property(f"resource_{resource_type}", 0)
                settlement.set_property(f"resource_{resource_type}", current_amount + amount)
            
            return {
                "status": "success",
                "resources": resources_produced
            }
            
        except Exception as e:
            logger.exception(f"Error processing resource production: {e}")
            return {"status": "error", "message": f"Error processing resource production: {str(e)}"}
    
    def _process_population_growth(self, settlement: Settlement, world: Any) -> Dict[str, Any]:
        """
        Process population growth for a settlement.
        
        Args:
            settlement (Settlement): The settlement entity
            world (Any): The world database record
            
        Returns:
            Dict[str, Any]: Result of population growth
        """
        try:
            logger.info(f"Processing population growth for settlement {settlement.settlement_name}")
            
            # Get settlement database record
            settlement_db = self.db.query(Settlements).filter(
                Settlements.settlement_id == settlement.settlement_id
            ).first()
            
            if not settlement_db:
                return {"status": "error", "message": "Settlement database record not found"}
            
            # Get current population
            current_population = settlement_db.population or 0
            
            # Calculate growth factors
            food_supply = self._get_settlement_resource(settlement.settlement_id, "food")
            housing_capacity = self._calculate_housing_capacity(settlement.settlement_id)
            current_season = world.current_season if hasattr(world, 'current_season') else "summer"
            
            # Base growth rate (% per day)
            base_growth_rate = 0.02  # 2% per day
            
            # Modifiers
            food_modifier = min(1.0, food_supply / max(1, current_population))
            housing_modifier = min(1.0, housing_capacity / max(1, current_population + 1))
            seasonal_modifier = 1.0
            if current_season == "winter":
                seasonal_modifier = 0.5
            
            # Calculate final growth
            final_growth_rate = base_growth_rate * food_modifier * housing_modifier * seasonal_modifier
            population_increase = int(current_population * final_growth_rate)
            
            # Ensure we don't exceed housing capacity
            new_population = min(current_population + population_increase, housing_capacity)
            
            # Update settlement population in database
            settlement_db.population = new_population
            self.db.commit()
            
            # Also update the settlement entity, handling potential None _properties
            try:
                if settlement._properties is None:
                    settlement._properties = {}
                settlement.set_property("population", new_population)
            except Exception as e:
                logger.warning(f"Could not set population property on settlement: {e}")
            
            # Consume food (1 food per day per person)
            self._consume_settlement_resource(settlement.settlement_id, "food", current_population)
            
            return {
                "status": "success",
                "population": {
                    "previous": current_population,
                    "current": new_population,
                    "growth": new_population - current_population,
                    "food_supply": food_supply,
                    "housing_capacity": housing_capacity
                }
            }
            
        except Exception as e:
            logger.exception(f"Error processing population growth: {e}")
            return {"status": "error", "message": f"Error processing population growth: {str(e)}"}
    
    def _process_buildings(self, settlement: Settlement) -> Dict[str, Any]:
        """
        Process building construction and repairs for a settlement.
        
        Args:
            settlement (Settlement): The settlement entity
            
        Returns:
            Dict[str, Any]: Result of building processing
        """
        try:
            logger.info(f"Processing buildings for settlement {settlement.settlement_name}")
            
            # Using a placeholder since we don't have a real Buildings table yet
            logger.info(f"Using placeholder implementation for buildings in settlement {settlement.settlement_id}")
            buildings = []
            
            # Process under-construction buildings
            for building in buildings:
                if building.is_under_construction:
                    # Progress construction
                    building.construction_progress += 10  # 10% per day
                    
                    # Check if construction complete
                    if building.construction_progress >= 100:
                        building.is_under_construction = False
                        building.is_built = True
                        building.construction_progress = 100
                        logger.info(f"Building {building.building_type} completed in settlement {settlement.name}")
                
                # Process repairs
                if building.is_damaged and building.is_under_repair:
                    # Progress repair
                    building.repair_progress += 15  # 15% per day
                    
                    # Check if repair complete
                    if building.repair_progress >= 100:
                        building.is_damaged = False
                        building.is_under_repair = False
                        building.repair_progress = 100
                        logger.info(f"Building {building.building_type} repaired in settlement {settlement.name}")
            
            # Commit changes
            self.db.commit()
            
            # Collect building statuses for return
            building_statuses = []
            for building in buildings:
                status = {
                    "building_id": building.building_id,
                    "type": building.building_type,
                    "is_built": building.is_built,
                    "is_damaged": building.is_damaged,
                    "construction_progress": building.construction_progress if hasattr(building, 'construction_progress') else None,
                    "repair_progress": building.repair_progress if hasattr(building, 'repair_progress') else None
                }
                building_statuses.append(status)
            
            return {
                "status": "success",
                "buildings": building_statuses
            }
            
        except Exception as e:
            logger.exception(f"Error processing buildings: {e}")
            return {"status": "error", "message": f"Error processing buildings: {str(e)}"}
    
    def _get_settlement_resource(self, settlement_id: str, resource_type: str) -> int:
        """
        Get the amount of a specific resource in a settlement.
        
        Args:
            settlement_id (str): The settlement ID
            resource_type (str): The type of resource
            
        Returns:
            int: The amount of the resource
        """
        try:
            # Using a placeholder since we don't have a real Resources table yet
            logger.info(f"Using placeholder implementation for resources in settlement {settlement_id}")
            resource = None
            
            return 0
            
        except Exception as e:
            logger.exception(f"Error getting settlement resource: {e}")
            return 0
    
    def _consume_settlement_resource(self, settlement_id: str, resource_type: str, amount: int) -> bool:
        """
        Consume an amount of a specific resource in a settlement.
        
        Args:
            settlement_id (str): The settlement ID
            resource_type (str): The type of resource
            amount (int): The amount to consume
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Using a placeholder since we don't have a real Resources table yet
            logger.info(f"Using placeholder implementation for consuming resources in settlement {settlement_id}")
            
            # Pretend we consumed the resource successfully
            return True
            
        except Exception as e:
            logger.exception(f"Error consuming settlement resource: {e}")
            return False
    
    def _calculate_housing_capacity(self, settlement_id: str) -> int:
        """
        Calculate the housing capacity for a settlement.
        
        Args:
            settlement_id (str): The settlement ID
            
        Returns:
            int: The housing capacity
        """
        try:
            # Get housing buildings - using a placeholder since we don't have a real Building table
            logger.info(f"Using placeholder implementation for housing buildings in settlement {settlement_id}")
            housing_buildings = []
            
            # Calculate total capacity
            capacity = 0
            for building in housing_buildings:
                if building.building_type == "house":
                    capacity += 5
                elif building.building_type == "apartment":
                    capacity += 20
                elif building.building_type == "mansion":
                    capacity += 10
            
            # Add base capacity for the settlement
            base_capacity = 10
            
            return base_capacity + capacity
            
        except Exception as e:
            logger.exception(f"Error calculating housing capacity: {e}")
            return 10  # Default base capacity
    
    def create_settlement(self, name: str, location_id: str, world_id: str) -> Dict[str, Any]:
        """
        Create a new settlement.
        
        Args:
            name (str): The name of the settlement
            location_id (str): The ID of the location (area)
            world_id (str): The ID of the world
            
        Returns:
            Dict[str, Any]: Result of settlement creation
        """
        try:
            logger.info(f"Creating new settlement: {name}")
            
            # Check if area exists
            area = self.db.query(Areas).filter(Areas.area_id == location_id).first()
            if not area:
                return {"status": "error", "message": "Area not found"}
            
            # Check if world exists
            world = self.db.query(Worlds).filter(Worlds.world_id == world_id).first()
            if not world:
                return {"status": "error", "message": "World not found"}
            
            # Generate settlement ID
            settlement_id = str(uuid.uuid4())
            
            # Create settlement entity
            settlement = Settlement(settlement_id)
            settlement.set_basic_info(name, f"A settlement named {name}")
            settlement.set_location(location_id)
            settlement.set_property("world_id", world_id)
            settlement.set_property("population", 10)  # Starting population
            
            # Save settlement entity
            self.settlement_manager.save_settlement(settlement)
            
            # Create database record
            new_settlement = Settlements(
                settlement_id=settlement_id,
                settlement_name=name,
                world_id=world_id,
                area_id=location_id,
                population=10,
                founding_date=datetime.now()
            )
            
            self.db.add(new_settlement)
            self.db.commit()
            
            # Create initial buildings
            self._create_initial_buildings(settlement_id)
            
            return {
                "status": "success",
                "settlement_id": settlement_id,
                "name": name,
                "location_id": location_id,
                "world_id": world_id
            }
            
        except Exception as e:
            logger.exception(f"Error creating settlement: {e}")
            return {"status": "error", "message": f"Error creating settlement: {str(e)}"}
    
    def _create_initial_buildings(self, settlement_id: str) -> None:
        """
        Create initial buildings for a new settlement.
        
        Args:
            settlement_id (str): The settlement ID
        """
        try:
            # Initial building types
            initial_buildings = [
                {"type": "town_hall", "is_built": True},
                {"type": "house", "is_built": True},
                {"type": "farm", "is_built": True},
                {"type": "market", "is_built": False, "construction_progress": 30}
            ]
            
            # Create each building
            for building_info in initial_buildings:
                building_id = str(uuid.uuid4())
                building = Building(
                    building_id=building_id,
                    settlement_id=settlement_id,
                    building_type=building_info["type"],
                    is_built=building_info["is_built"],
                    is_damaged=False,
                    is_under_construction=not building_info["is_built"],
                    construction_progress=building_info.get("construction_progress", 100 if building_info["is_built"] else 0)
                )
                
                # Add production type for resource buildings
                if building_info["type"] == "farm":
                    building.production_type = "food"
                    building.production_rate = 15
                elif building_info["type"] == "mine":
                    building.production_type = "ore"
                    building.production_rate = 10
                elif building_info["type"] == "lumber_mill":
                    building.production_type = "wood"
                    building.production_rate = 12
                
                self.db.add(building)
            
            # Commit changes
            self.db.commit()
            
        except Exception as e:
            logger.exception(f"Error creating initial buildings: {e}")
    
    def start_building_construction(self, settlement_id: str, building_type: str) -> Dict[str, Any]:
        """
        Start construction of a new building in a settlement.
        
        Args:
            settlement_id (str): The settlement ID
            building_type (str): The type of building to construct
            
        Returns:
            Dict[str, Any]: Result of construction initiation
        """
        try:
            logger.info(f"Starting construction of {building_type} in settlement {settlement_id}")
            
            # Check if settlement exists
            settlement = self.settlement_manager.load_settlement(settlement_id)
            if not settlement:
                return {"status": "error", "message": "Settlement not found"}
            
            # Check if resources are available
            resource_requirements = self._get_building_resource_requirements(building_type)
            for resource_type, amount in resource_requirements.items():
                available = self._get_settlement_resource(settlement_id, resource_type)
                if available < amount:
                    return {
                        "status": "error", 
                        "message": f"Insufficient resources: {resource_type} ({available}/{amount})"
                    }
            
            # Consume resources
            for resource_type, amount in resource_requirements.items():
                self._consume_settlement_resource(settlement_id, resource_type, amount)
            
            # Create building
            building_id = str(uuid.uuid4())
            new_building = Building(
                building_id=building_id,
                settlement_id=settlement_id,
                building_type=building_type,
                is_built=False,
                is_damaged=False,
                is_under_construction=True,
                construction_progress=0
            )
            
            # Add production information if applicable
            if building_type == "farm":
                new_building.production_type = "food"
                new_building.production_rate = 15
            elif building_type == "mine":
                new_building.production_type = "ore"
                new_building.production_rate = 10
            elif building_type == "lumber_mill":
                new_building.production_type = "wood"
                new_building.production_rate = 12
            
            self.db.add(new_building)
            self.db.commit()
            
            return {
                "status": "success",
                "building_id": building_id,
                "type": building_type,
                "message": f"Started construction of {building_type}"
            }
            
        except Exception as e:
            logger.exception(f"Error starting building construction: {e}")
            return {"status": "error", "message": f"Error starting construction: {str(e)}"}
    
    def _get_building_resource_requirements(self, building_type: str) -> Dict[str, int]:
        """
        Get the resource requirements for constructing a building.
        
        Args:
            building_type (str): The type of building
            
        Returns:
            Dict[str, int]: Resource requirements (type -> amount)
        """
        # Building requirements dictionary
        requirements = {
            "house": {"wood": 20, "stone": 10},
            "farm": {"wood": 15, "stone": 5},
            "mine": {"wood": 25, "stone": 15},
            "lumber_mill": {"wood": 10, "stone": 10},
            "market": {"wood": 30, "stone": 20},
            "blacksmith": {"wood": 25, "stone": 15, "ore": 10},
            "town_hall": {"wood": 50, "stone": 30, "gold": 10},
            "barracks": {"wood": 35, "stone": 25, "ore": 5},
            "temple": {"wood": 40, "stone": 40, "gold": 20},
            "warehouse": {"wood": 30, "stone": 15},
            "tavern": {"wood": 25, "stone": 10, "food": 15},
            "apartment": {"wood": 40, "stone": 30, "glass": 10}
        }
        
        return requirements.get(building_type, {"wood": 10, "stone": 5})
    
    def start_building_repair(self, settlement_id: str, building_id: str) -> Dict[str, Any]:
        """
        Start repair of a damaged building.
        
        Args:
            settlement_id (str): The settlement ID
            building_id (str): The building ID
            
        Returns:
            Dict[str, Any]: Result of repair initiation
        """
        try:
            logger.info(f"Starting repair of building {building_id} in settlement {settlement_id}")
            
            # Check if settlement exists
            settlement = self.settlement_manager.load_settlement(settlement_id)
            if not settlement:
                return {"status": "error", "message": "Settlement not found"}
            
            # Check if building exists and is damaged
            building = self.db.query(Building).filter(
                Building.building_id == building_id,
                Building.settlement_id == settlement_id
            ).first()
            
            if not building:
                return {"status": "error", "message": "Building not found"}
            
            if not building.is_damaged:
                return {"status": "error", "message": "Building is not damaged"}
            
            if building.is_under_repair:
                return {"status": "error", "message": "Building is already under repair"}
            
            # Calculate repair costs (50% of construction cost)
            repair_requirements = self._get_building_resource_requirements(building.building_type)
            for resource_type in repair_requirements:
                repair_requirements[resource_type] = repair_requirements[resource_type] // 2
            
            # Check if resources are available
            for resource_type, amount in repair_requirements.items():
                available = self._get_settlement_resource(settlement_id, resource_type)
                if available < amount:
                    return {
                        "status": "error", 
                        "message": f"Insufficient resources: {resource_type} ({available}/{amount})"
                    }
            
            # Consume resources
            for resource_type, amount in repair_requirements.items():
                self._consume_settlement_resource(settlement_id, resource_type, amount)
            
            # Start repair
            building.is_under_repair = True
            building.repair_progress = 0
            self.db.commit()
            
            return {
                "status": "success",
                "building_id": building_id,
                "type": building.building_type,
                "message": f"Started repair of {building.building_type}"
            }
            
        except Exception as e:
            logger.exception(f"Error starting building repair: {e}")
            return {"status": "error", "message": f"Error starting repair: {str(e)}"}
    
    def process_all_settlements(self, world_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process all settlements in a world.
        
        Args:
            world_id (Optional[str]): The world ID, or None for all worlds
            
        Returns:
            Dict[str, Any]: Result of processing all settlements
        """
        logger.info(f"Processing all settlements" + (f" in world {world_id}" if world_id else ""))
        
        try:
            # Query all settlements in the world
            query = self.db.query(Settlements)
            if world_id:
                query = query.filter(Settlements.world_id == world_id)
            
            settlements = query.all()
            processed_count = 0
            
            # Process each settlement
            for settlement in settlements:
                try:
                    # Process this settlement
                    result = self.process_settlement_growth(str(settlement.settlement_id))
                    
                    if result["status"] == "success":
                        processed_count += 1
                    else:
                        logger.warning(f"Failed to process settlement {settlement.settlement_id}: {result.get('message')}")
                        
                except Exception as e:
                    logger.exception(f"Error processing settlement {settlement.settlement_id}: {e}")
            
            return {
                "status": "success",
                "total": len(settlements),
                "processed": processed_count
            }
            
        except Exception as e:
            logger.exception(f"Error processing all settlements: {e}")
            return {"status": "error", "message": f"Error processing settlements: {str(e)}"}