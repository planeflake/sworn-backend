# app/game_state/services/area_service.py
import logging
import json
import uuid
import random
from typing import List, Dict, Optional, Any, Tuple

from datetime import datetime
from sqlalchemy.orm import Session

from app.game_state.entities.area import Area
from app.game_state.managers.area_manager import AreaManager
from app.models.core import Areas, AreaEncounters, AreaEncounterTypes, ResourceSites

logger = logging.getLogger(__name__)

class AreaService:
    """
    Service layer for managing game areas and related functionality.
    
    Areas are wilderness locations between settlements where characters can
    travel, harvest resources, and encounter various situations.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the area service with a database session and manager.
        
        Args:
            db (Session): SQLAlchemy database session
        """
        self.db = db
        self.area_manager = AreaManager()
    
    def get_area(self, area_id: str) -> Optional[Area]:
        """
        Get an area entity by ID.
        
        Args:
            area_id (str): The ID of the area to retrieve
            
        Returns:
            Optional[Area]: The area entity, or None if not found
        """
        return self.area_manager.load_entity(area_id)
    
    def create_area(self, name: str, area_type: str, world_id: str, 
                   location: Tuple[float, float], radius: float = 10.0,
                   danger_level: int = 1, description: Optional[str] = None) -> Optional[Area]:
        """
        Create a new area entity.
        
        Args:
            name (str): Name of the area
            area_type (str): Type of area (forest, mountains, plains, etc.)
            world_id (str): ID of the world this area belongs to
            location (Tuple[float, float]): (x, y) coordinates
            radius (float): Size/radius of the area
            danger_level (int): 1-5 rating of area danger
            description (Optional[str]): Description of the area
            
        Returns:
            Optional[Area]: The newly created area, or None if creation failed
        """
        try:
            # Create area entity
            area = self.area_manager.create_area(name=name, description=description)
            if not area:
                logger.error(f"Failed to create area entity for {name}")
                return None
                
            # Set area properties
            area.set_property("area_type", area_type)
            area.set_property("world_id", world_id)
            area.set_property("x_coord", location[0])
            area.set_property("y_coord", location[1])
            area.set_property("radius", radius)
            area.set_property("danger_level", danger_level)
            area.set_property("biome", area_type)  # Use area_type as biome for now
            
            # Save area
            if self.area_manager.save_entity(area):
                logger.info(f"Created new area: {name} (ID: {area.area_id})")
                return area
            else:
                logger.error(f"Failed to save new area {name}")
                return None
                
        except Exception as e:
            logger.exception(f"Error creating area {name}: {e}")
            return None
    
    def connect_areas(self, area_id: str, connected_area_id: str) -> bool:
        """
        Connect two areas together for travel purposes.
        
        Args:
            area_id (str): ID of the first area
            connected_area_id (str): ID of the area to connect to
            
        Returns:
            bool: True if connection was successful, False otherwise
        """
        try:
            # Get both areas
            area = self.get_area(area_id)
            connected_area = self.get_area(connected_area_id)
            
            if not area or not connected_area:
                logger.error(f"Cannot connect areas: one or both areas not found")
                return False
            
            # Get current connections for first area
            connections = area.get_property("connected_areas", [])
            if connected_area_id not in connections:
                connections.append(connected_area_id)
                area.set_property("connected_areas", connections)
            
            # Get current connections for second area
            other_connections = connected_area.get_property("connected_areas", [])
            if area_id not in other_connections:
                other_connections.append(area_id)
                connected_area.set_property("connected_areas", other_connections)
            
            # Save both areas
            if not self.area_manager.save_entity(area):
                logger.error(f"Failed to save area {area_id} after connecting")
                return False
                
            if not self.area_manager.save_entity(connected_area):
                logger.error(f"Failed to save area {connected_area_id} after connecting")
                return False
            
            logger.info(f"Connected areas {area.area_name} and {connected_area.area_name}")
            return True
            
        except Exception as e:
            logger.exception(f"Error connecting areas {area_id} and {connected_area_id}: {e}")
            return False
    
    def connect_area_to_settlement(self, area_id: str, settlement_id: str) -> bool:
        """
        Connect an area to a settlement for travel purposes.
        
        Args:
            area_id (str): ID of the area
            settlement_id (str): ID of the settlement
            
        Returns:
            bool: True if connection was successful, False otherwise
        """
        try:
            # Get the area
            area = self.get_area(area_id)
            if not area:
                logger.error(f"Cannot connect to settlement: area {area_id} not found")
                return False
            
            # Get current settlement connections
            settlement_connections = area.get_property("connected_settlements", [])
            if settlement_id not in settlement_connections:
                settlement_connections.append(settlement_id)
                area.set_property("connected_settlements", settlement_connections)
            
            # Save area
            if not self.area_manager.save_entity(area):
                logger.error(f"Failed to save area {area_id} after connecting to settlement")
                return False
            
            logger.info(f"Connected area {area.area_name} to settlement {settlement_id}")
            return True
            
        except Exception as e:
            logger.exception(f"Error connecting area {area_id} to settlement {settlement_id}: {e}")
            return False
    
    def generate_encounter(self, area_id: str, entity_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a random encounter in an area.
        
        Args:
            area_id (str): ID of the area
            entity_id (Optional[str]): ID of the entity encountering (player, trader, etc.)
            
        Returns:
            Dict[str, Any]: Result of encounter generation
        """
        try:
            # Get the area
            area = self.get_area(area_id)
            if not area:
                return {"status": "error", "message": f"Area {area_id} not found"}
            
            # Determine if an encounter happens based on danger level
            danger_level = area.get_property("danger_level", 1)
            encounter_chance = 0.1 + (danger_level * 0.05)  # 10% base chance + 5% per danger level
            
            # Roll for encounter
            encounter_roll = random.random()
            if encounter_roll > encounter_chance:
                # No encounter this time
                logger.info(f"No encounter generated in area {area.area_name}")
                return {"status": "success", "result": "no_encounter"}
            
            # Get available encounter types
            encounter_types = self.db.query(AreaEncounterTypes).all()
            if not encounter_types:
                logger.warning("No encounter types found in database")
                return {"status": "success", "result": "no_encounter"}
            
            # Select an appropriate encounter type based on area type and danger level
            area_type = area.get_property("area_type", "wilderness")
            appropriate_types = [et for et in encounter_types if 
                               et.applicable_area_types is None or 
                               area_type in json.loads(et.applicable_area_types)]
            
            if not appropriate_types:
                # Fall back to any encounter type
                appropriate_types = encounter_types
            
            # Filter by danger level if possible
            danger_appropriate = [et for et in appropriate_types if 
                                et.min_danger_level <= danger_level <= et.max_danger_level]
            
            if danger_appropriate:
                selected_encounter = random.choice(danger_appropriate)
            else:
                selected_encounter = random.choice(appropriate_types)
            
            # Create the encounter
            encounter_id = str(uuid.uuid4())
            encounter = AreaEncounters(
                encounter_id=encounter_id,
                area_id=area_id,
                encounter_type_id=selected_encounter.encounter_type_id,
                is_active=True,
                is_completed=False,
                current_state="initial",
                created_at=datetime.now(),
                custom_narrative=f"Encounter in {area.area_name}: {selected_encounter.encounter_name}"
            )
            
            # Add entity information if provided
            if entity_id:
                encounter.triggered_by = entity_id
            
            # Save to database
            self.db.add(encounter)
            self.db.commit()
            
            logger.info(f"Generated {selected_encounter.encounter_name} encounter in {area.area_name}")
            
            return {
                "status": "success", 
                "result": "encounter_created",
                "encounter_id": encounter_id,
                "encounter_name": selected_encounter.encounter_name,
                "description": selected_encounter.description
            }
            
        except Exception as e:
            self.db.rollback()
            logger.exception(f"Error generating encounter in area {area_id}: {e}")
            return {"status": "error", "message": f"Error generating encounter: {str(e)}"}
    
    def resolve_encounter(self, encounter_id: str, entity_id: str, 
                       resolution_type: str = "default") -> Dict[str, Any]:
        """
        Resolve an area encounter.
        
        Args:
            encounter_id (str): ID of the encounter to resolve
            entity_id (str): ID of the entity resolving the encounter
            resolution_type (str): Type of resolution (flee, fight, negotiate, etc.)
            
        Returns:
            Dict[str, Any]: Result of the resolution
        """
        try:
            # Get the encounter
            encounter = self.db.query(AreaEncounters).filter(
                AreaEncounters.encounter_id == encounter_id,
                AreaEncounters.is_completed == False
            ).first()
            
            if not encounter:
                return {"status": "error", "message": f"Active encounter {encounter_id} not found"}
            
            # Get the encounter type
            encounter_type = self.db.query(AreaEncounterTypes).filter(
                AreaEncounterTypes.encounter_type_id == encounter.encounter_type_id
            ).first()
            
            if not encounter_type:
                return {"status": "error", "message": "Encounter type not found"}
            
            # Determine outcome based on resolution type
            # In a real implementation, this would be more complex and based on character stats
            outcomes = ["success", "partial_success", "failure"]
            weights = [0.5, 0.3, 0.2]  # Default weights favoring success
            
            # Adjust weights based on resolution type
            if resolution_type == "flee":
                weights = [0.3, 0.4, 0.3]  # Fleeing has moderate success chance
            elif resolution_type == "fight":
                weights = [0.4, 0.3, 0.3]  # Fighting is risky but can be effective
            elif resolution_type == "negotiate":
                weights = [0.6, 0.3, 0.1]  # Negotiation has high success chance
            
            outcome = random.choices(outcomes, weights=weights, k=1)[0]
            
            # Update encounter
            encounter.is_completed = True
            encounter.is_active = False
            encounter.current_state = "resolved"
            encounter.resolved_at = datetime.now()
            encounter.resolved_by = entity_id
            encounter.resolution_outcome = outcome
            
            # Save changes
            self.db.commit()
            
            logger.info(f"Resolved encounter {encounter_id} with outcome: {outcome}")
            
            # Return outcome information
            result = {
                "status": "success",
                "encounter_id": encounter_id,
                "encounter_name": encounter_type.encounter_name,
                "resolution_type": resolution_type,
                "outcome": outcome
            }
            
            # Add narrative based on outcome
            if outcome == "success":
                result["narrative"] = f"You successfully dealt with the {encounter_type.encounter_name}." 
            elif outcome == "partial_success":
                result["narrative"] = f"You partially resolved the {encounter_type.encounter_name}, but at some cost."
            else:
                result["narrative"] = f"You failed to resolve the {encounter_type.encounter_name} effectively."
            
            return result
            
        except Exception as e:
            self.db.rollback()
            logger.exception(f"Error resolving encounter {encounter_id}: {e}")
            return {"status": "error", "message": f"Error resolving encounter: {str(e)}"}
    
    def get_area_resource_sites(self, area_id: str) -> Dict[str, Any]:
        """
        Get all resource sites in an area.
        
        Args:
            area_id (str): ID of the area
            
        Returns:
            Dict[str, Any]: List of resource sites and their details
        """
        try:
            # Get the area
            area = self.get_area(area_id)
            if not area:
                return {"status": "error", "message": f"Area {area_id} not found"}
            
            # Query resource sites in this area
            sites = self.db.query(ResourceSites).filter(ResourceSites.area_id == area_id).all()
            
            # Format resource site data
            site_data = []
            for site in sites:
                site_data.append({
                    "site_id": str(site.resource_site_id),
                    "name": site.site_name,
                    "resource_type": site.resource_type,
                    "current_stage": site.current_stage,
                    "is_discovered": site.is_discovered
                })
            
            return {
                "status": "success",
                "area_id": area_id,
                "area_name": area.area_name,
                "resource_sites": site_data,
                "count": len(site_data)
            }
            
        except Exception as e:
            logger.exception(f"Error getting resource sites for area {area_id}: {e}")
            return {"status": "error", "message": f"Error getting resource sites: {str(e)}"}
    
    def update_danger_level(self, area_id: str, new_danger_level: int) -> Dict[str, Any]:
        """
        Update the danger level of an area.
        
        Args:
            area_id (str): ID of the area
            new_danger_level (int): New danger level (1-5)
            
        Returns:
            Dict[str, Any]: Result of the update
        """
        try:
            # Get the area
            area = self.get_area(area_id)
            if not area:
                return {"status": "error", "message": f"Area {area_id} not found"}
            
            # Validate danger level
            if new_danger_level < 1 or new_danger_level > 5:
                return {"status": "error", "message": "Danger level must be between 1 and 5"}
            
            # Update the danger level
            area.set_property("danger_level", new_danger_level)
            
            # Save changes
            if self.area_manager.save_entity(area):
                logger.info(f"Updated danger level for area {area.area_name} to {new_danger_level}")
                return {
                    "status": "success",
                    "area_id": area_id,
                    "area_name": area.area_name,
                    "old_danger_level": area.get_property("danger_level", 1),
                    "new_danger_level": new_danger_level
                }
            else:
                return {"status": "error", "message": "Failed to save area changes"}
                
        except Exception as e:
            logger.exception(f"Error updating danger level for area {area_id}: {e}")
            return {"status": "error", "message": f"Error updating danger level: {str(e)}"}
    
    def process_all_areas(self, world_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process all areas, updating state and generating ambient events.
        
        Args:
            world_id (Optional[str]): ID of the world to process areas for, or None for all worlds
            
        Returns:
            Dict[str, Any]: Result of processing all areas
        """
        try:
            # Query all areas or areas in a specific world
            query = self.db.query(Areas)
            if world_id:
                query = query.filter(Areas.world_id == world_id)
                
            areas = query.all()
            processed_count = 0
            events_generated = 0
            
            for area_db in areas:
                try:
                    # Process this area
                    area_entity = self.get_area(str(area_db.area_id))
                    if not area_entity:
                        continue
                    
                    # Random chance to generate ambient encounter
                    if random.random() < 0.1:  # 10% chance
                        result = self.generate_encounter(str(area_db.area_id))
                        if result["status"] == "success" and result["result"] == "encounter_created":
                            events_generated += 1
                    
                    processed_count += 1
                    
                except Exception as e:
                    logger.exception(f"Error processing area {area_db.area_id}: {e}")
            
            return {
                "status": "success",
                "total": len(areas),
                "processed": processed_count,
                "events_generated": events_generated
            }
            
        except Exception as e:
            logger.exception(f"Error processing all areas: {e}")
            return {"status": "error", "message": f"Error processing areas: {str(e)}"}
