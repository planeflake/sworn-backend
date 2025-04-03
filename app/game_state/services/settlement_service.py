# app/game_state/services/settlement_service.py
import logging
import json
import uuid
from typing import List, Dict, Optional, Any
from datetime import datetime

from app.game_state.managers.settlement_manager import SettlementManager
from app.game_state.entities.settlement import Settlement
from app.game_state.managers.building_manager import BuildingManager
from app.game_state.managers.resource_manager import ResourceManager
from app.game_state.services.logging_service import LoggingService
from database.connection import SessionLocal

logger = logging.getLogger(__name__)

class SettlementService:
    """
    Service layer that orchestrates settlement-related operations.
    This service should not directly interact with database models,
    but instead work through domain entities and managers.
    """
    
    def __init__(self, db=None):
        """
        Initialize the settlement service.
        
        Args:
            db: Database session (passed to managers that need it)
        """
        self.db = db
        self.settlement_manager = SettlementManager()
        self.building_type_manager = BuildingManager(db)
        self.resource_site_manager = ResourceManager(db)

    async def process_all_settlements(self, world_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process all settlements in a world.
        
        Args:
            world_id (Optional[str]): The world ID, or None for all worlds
            
        Returns:
            Dict[str, Any]: Result of processing all settlements
        """
        logger.info(f"Processing all settlements" + (f" in world {world_id}" if world_id else ""))
        
        try:
            # Get all settlements through the settlement manager
            settlements = self.settlement_manager.get_all_settlements()
            
            # Filter by world_id if provided
            if world_id:
                settlements = [s for s in settlements if s.get_property("world_id") == world_id]
            
            processed_count = 0
            results = []
            tasks_generated = 0
            
            # Process each settlement
            for settlement in settlements:
                try:
                    # Get world_id for this settlement
                    world_id_for_tasks = settlement.get_property("world_id")
                    
                    # Process this settlement's growth
                    growth_result = self.process_settlement_growth(str(settlement.settlement_id))
                    
                    # Process tasks for this settlement
                    task_result = await self.process_settlement_tasks(str(settlement.settlement_id), world_id_for_tasks)
                    tasks_generated += task_result.get("tasks_generated", 0)
                    
                    results.append({
                        "settlement_id": str(settlement.settlement_id),
                        "name": settlement.settlement_name,
                        "growth_result": growth_result,
                        "task_result": task_result
                    })
                    
                    if growth_result["status"] == "success":
                        processed_count += 1
                    else:
                        logger.warning(f"Failed to process settlement {settlement.settlement_id}: {growth_result.get('message')}")
                        
                except Exception as e:
                    logger.exception(f"Error processing settlement {settlement.settlement_id}: {e}")
            
            return {
                "status": "success",
                "total": len(settlements),
                "processed": processed_count,
                "tasks_generated": tasks_generated,
                "results": results
            }
            
        except Exception as e:
            logger.exception(f"Error processing all settlements: {e}")
            return {"status": "error", "message": f"Error processing settlements: {str(e)}"}

    def process_settlement_growth(self, settlement_id: str) -> Dict[str, Any]:
        """
        Process population growth, resource production, and building construction for a settlement.
        
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
            # Get the world info through a world manager
            from app.game_state.managers.world_manager import WorldManager
            world_manager = WorldManager()
            world_info = world_manager.get_world_info(settlement.get_property("world_id"))
            
            if not world_info:
                return {"status": "error", "message": "Settlement's world not found"}
            
            # Process resource production
            production_result = self._process_resource_production(settlement, world_info)
            if production_result["status"] != "success":
                logger.error(f"Resource production failed: {production_result.get('message')}")
                return production_result
            
            # Process population growth
            growth_result = self._process_population_growth(settlement, world_info)
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
    
    def _process_resource_production(self, settlement: Settlement, world_info: Dict) -> Dict[str, Any]:
        """
        Process resource production for a settlement.
        
        Args:
            settlement (Settlement): The settlement entity
            world_info (Dict): The world information
            
        Returns:
            Dict[str, Any]: Result of resource production
        """
        try:
            logger.info(f"Processing resource production for settlement {settlement.settlement_name}")
            
            # Get current season for production modifiers
            current_season = world_info.get('current_season', "summer")
            
            # Get buildings from the settlement entity
            buildings = settlement.get_buildings()
            
            # Calculate resource production based on buildings
            resources_produced = {}
            
            # Production from buildings
            for building in buildings:
                # Skip if not operational
                if not building.get("is_operational", False):
                    continue
                
                building_type_id = building.get("type")
                
                # Get building type details from manager
                building_type = self.building_type_manager.get_building_type(building_type_id)
                if not building_type:
                    continue
                
                # Get production type and rate
                production_type = building_type.get("production_type")
                production_rate = building_type.get("production_rate", 0)
                
                if not production_type or not production_rate:
                    continue
                
                # Apply seasonal modifiers
                seasonal_modifier = 1.0
                if production_type == "food" and current_season == "winter":
                    seasonal_modifier = 0.5
                elif production_type == "wood" and current_season == "autumn":
                    seasonal_modifier = 1.2
                
                # Final production amount
                production_amount = int(production_rate * seasonal_modifier)
                
                # Add to total
                if production_type in resources_produced:
                    resources_produced[production_type] += production_amount
                else:
                    resources_produced[production_type] = production_amount
            
            # Production from resource sites
            resource_sites = self.resource_site_manager.get_settlement_resource_sites(settlement.settlement_id)
            
            for site in resource_sites:
                # Only operational sites produce resources
                if site.get("current_stage") in ["discovered", "mine", "farm", "camp", "garden", "outpost"]:
                    resource_type = site.get("resource_output")
                    if not resource_type:
                        continue
                    
                    # Base production rate depends on the stage and development
                    base_rate = 5  # Default rate
                    if "development_level" in site:
                        base_rate += int(site["development_level"] * 20)  # Up to +20 at max development
                    
                    # Apply production multiplier
                    multiplier = site.get("production_multiplier", 1.0)
                    
                    # Apply depletion factor
                    depletion_factor = 1.0 - min(1.0, site.get("depletion_level", 0))
                    
                    # Calculate final amount
                    amount = int(base_rate * multiplier * depletion_factor)
                    
                    # Add to resources
                    if resource_type in resources_produced:
                        resources_produced[resource_type] += amount
                    else:
                        resources_produced[resource_type] = amount
            
            # Update settlement resources
            current_resources = settlement.get_resources()
            for resource_type, amount in resources_produced.items():
                current_amount = current_resources.get(resource_type, 0)
                current_resources[resource_type] = current_amount + amount
            
            # Save updated resources
            settlement.set_property("resources", current_resources)
            
            return {
                "status": "success",
                "resources": resources_produced
            }
            
        except Exception as e:
            logger.exception(f"Error processing resource production: {e}")
            return {"status": "error", "message": f"Error processing resource production: {str(e)}"}
    
    def _process_population_growth(self, settlement: Settlement, world_info: Dict) -> Dict[str, Any]:
        """
        Process population growth for a settlement.
        
        Args:
            settlement (Settlement): The settlement entity
            world_info (Dict): The world information
            
        Returns:
            Dict[str, Any]: Result of population growth
        """
        try:
            logger.info(f"Processing population growth for settlement {settlement.settlement_name}")
            
            # Get current population from settlement entity
            current_population = settlement.get_property("population", 0)
            
            # Calculate growth factors
            resources = settlement.get_resources()
            food_supply = resources.get("food", 0)
            housing_capacity = self._calculate_housing_capacity(settlement)
            current_season = world_info.get('current_season', "summer")
            
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
            
            # Update the settlement entity
            settlement.set_property("population", new_population)
            
            # Consume food (1 food per day per person)
            self._consume_settlement_resource(settlement, "food", current_population)
            
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
            
            # Get buildings from the settlement entity 
            buildings = settlement.get_buildings()
            logger.info(f"Found {len(buildings)} buildings in settlement {settlement.settlement_name}")
            
            # Get resources from the settlement entity
            resources = settlement.get_resources()
            
            # Processing buildings
            updated_buildings = []
            for building_data in buildings:
                building_id = building_data.get("building_id")
                
                # Check if building is under construction
                if building_data.get("construction_status") == 'in_progress':
                    logger.info(f"Building {building_data.get('type')} is under construction")
                    
                    # Check if settlement has resources for the build step
                    has_resources = True  # Simplified for now
                    
                    if has_resources:
                        # Progress construction
                        current_progress = building_data.get("construction_progress", 0)
                        new_progress = min(100, current_progress + 10)  # Progress by 10%
                        building_data["construction_progress"] = new_progress
                        
                        # Check if construction complete
                        if new_progress >= 100:
                            building_data["construction_status"] = 'completed'
                            building_data["is_operational"] = True
                            building_data["construction_progress"] = 100
                            building_data["constructed_at"] = datetime.now().isoformat()
                            logger.info(f"Building {building_data.get('type')} completed in settlement {settlement.settlement_name}")
                
                updated_buildings.append(building_data)
            
            # Update the settlement entity with the new building data
            settlement.set_property("buildings", updated_buildings)
            
            # Save building changes to the database through the manager
            self._save_buildings_to_database(settlement.settlement_id, updated_buildings)
            
            # Return success result
            return {
                "status": "success",
                "buildings": updated_buildings
            }
            
        except Exception as e:
            logger.exception(f"Error processing buildings: {e}")
            return {"status": "error", "message": f"Error processing buildings: {str(e)}"}
    
    def _save_buildings_to_database(self, settlement_id: str, buildings: List[Dict]) -> None:
        """
        Save building changes to the database through the appropriate manager.
        
        Args:
            settlement_id (str): The settlement ID
            buildings (List[Dict]): The updated building data
        """
        # This would typically use a Building Manager to save changes
        # For now, we'll just log the changes
        logger.info(f"Saving {len(buildings)} buildings for settlement {settlement_id}")
        
        # In a real implementation, this would call a manager method like:
        # self.building_manager.update_buildings(settlement_id, buildings)
    
    def _consume_settlement_resource(self, settlement: Settlement, resource_type: str, amount: int) -> bool:
        """
        Consume an amount of a specific resource in a settlement.
        
        Args:
            settlement (Settlement): The settlement entity
            resource_type (str): The type of resource
            amount (int): The amount to consume
            
        Returns:
            bool: True if successful, False otherwise
        """
        resources = settlement.get_resources()
        current = resources.get(resource_type, 0)
        
        if current >= amount:
            resources[resource_type] = current - amount
            settlement.set_property("resources", resources)
            return True
        else:
            # Not enough resources - only consume what's available
            resources[resource_type] = 0
            settlement.set_property("resources", resources)
            return False
    
    def _calculate_housing_capacity(self, settlement: Settlement) -> int:
        """
        Calculate the housing capacity for a settlement.
        
        Args:
            settlement (Settlement): The settlement entity
            
        Returns:
            int: The housing capacity
        """
        # Get buildings from the settlement
        buildings = settlement.get_buildings()
        
        # Calculate total capacity
        capacity = 0
        for building in buildings:
            building_type = building.get("type")
            if building.get("is_operational", False):
                if building_type == "house":
                    capacity += 5
                elif building_type == "apartment":
                    capacity += 20
                elif building_type == "mansion":
                    capacity += 10
        
        # Add base capacity for the settlement
        base_capacity = 10
        
        return base_capacity + capacity
    
    async def process_settlement_tasks(self, settlement_id: str, world_id: str) -> Dict[str, Any]:
        """
        Process task generation for a settlement.
        
        Args:
            settlement_id (str): The ID of the settlement to process
            world_id (str): The world ID for task creation
            
        Returns:
            Dict[str, Any]: Result of task processing
        """
        try:
            # Load the settlement through the manager
            settlement = self.settlement_manager.load_settlement(settlement_id)
            if not settlement:
                logger.error(f"Settlement {settlement_id} not found")
                return {"status": "error", "message": "Settlement not found"}
            
            # Get current game day from world manager
            from app.game_state.managers.world_manager import WorldManager
            world_manager = WorldManager()
            world_day = world_manager.get_current_day()
            
            # Process settlement needs less frequently (every 7 days)
            if world_day % 7 == 0:
                # Check for resource site rumors
                updated_sites = self.settlement_manager.update_resource_site_rumors(settlement_id)
                
                # Generate resource site tasks
                from app.game_state.services.task_service import TaskService
                task_service = TaskService()
                generated_tasks = await task_service.generate_resource_site_tasks(settlement_id, world_id)
                
                return {
                    "status": "success", 
                    "tasks_generated": len(generated_tasks),
                    "sites_updated": updated_sites
                }
            
            return {"status": "success", "tasks_generated": 0, "message": "No task processing scheduled for this day"}
            
        except Exception as e:
            logger.exception(f"Error processing settlement tasks: {e}")
            return {"status": "error", "message": f"Error processing settlement tasks: {str(e)}"}