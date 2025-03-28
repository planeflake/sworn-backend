# app/game_state/services/world_service.py
import logging
import json
import uuid
from typing import List, Dict, Optional, Any, Tuple

from datetime import datetime
from sqlalchemy.orm import Session

from app.game_state.entities.world import World
from app.models.core import Worlds, Settlements, Areas, ResourceSites
from app.game_state.managers.world_manager import WorldManager

logger = logging.getLogger(__name__)

class WorldService:
    """
    Service layer for managing the game world.
    
    This service orchestrates operations related to the world entity,
    including time progression, weather, events, and world-level state.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the world service with a database session.
        
        Args:
            db (Session): SQLAlchemy database session
        """
        self.db = db
        # TODO: Add world manager when implemented
        # self.world_manager = WorldManager()
    
    def get_world(self, world_id: str) -> Optional[World]:
        """
        Get a world entity by ID.
        
        Args:
            world_id (str): The ID of the world to retrieve
            
        Returns:
            Optional[World]: The world entity, or None if not found
        """
        # TODO: Replace with world manager when implemented
        # return self.world_manager.load_world(world_id)
        
        try:
            # Temporary implementation using direct database access
            world_db = self.db.query(Worlds).filter(Worlds.world_id == world_id).first()
            if not world_db:
                logger.warning(f"World {world_id} not found")
                return None
                
            # Create world entity from database
            world = World(str(world_db.world_id))
            world.set_basic_info(
                name=world_db.world_name,
                description=world_db.description
            )
            
            # Set time information
            world.current_game_day = world_db.current_game_day
            world.current_season = world_db.current_season or "spring"
            world.day_of_season = world_db.day_of_season or 1
            world.days_per_season = world_db.days_per_season or 30
            world.current_year = world_db.current_year or 1
            
            # Load settlements
            self._load_world_settlements(world)
            
            # Load areas
            self._load_world_areas(world)
            
            # Load resource sites
            self._load_world_resource_sites(world)
            
            world.mark_clean()  # Mark as clean since we just loaded from DB
            return world
            
        except Exception as e:
            logger.exception(f"Error loading world {world_id}: {e}")
            return None
    
    def _load_world_settlements(self, world: World):
        """
        Load all settlements for a world entity.
        
        Args:
            world (World): The world entity to load settlements for
        """
        try:
            settlements = self.db.query(Settlements).filter(
                Settlements.world_id == world.world_id
            ).all()
            
            for settlement in settlements:
                # Register each settlement with the world
                world.register_settlement(
                    settlement_id=str(settlement.settlement_id),
                    name=settlement.settlement_name,
                    location=(settlement.x_coord, settlement.y_coord) if hasattr(settlement, 'x_coord') else (0, 0),
                    size=settlement.settlement_size or "hamlet"
                )
                
        except Exception as e:
            logger.exception(f"Error loading settlements for world {world.world_id}: {e}")
    
    def _load_world_areas(self, world: World):
        """
        Load all areas for a world entity.
        
        Args:
            world (World): The world entity to load areas for
        """
        try:
            areas = self.db.query(Areas).filter(
                Areas.world_id == world.world_id
            ).all()
            
            for area in areas:
                # Register each area with the world
                world.register_area(
                    area_id=str(area.area_id),
                    name=area.area_name,
                    area_type=area.area_type or "wilderness",
                    location=(area.x_coord, area.y_coord) if hasattr(area, 'x_coord') else (0, 0),
                    radius=area.radius or 10.0
                )
                
        except Exception as e:
            logger.exception(f"Error loading areas for world {world.world_id}: {e}")
    
    def _load_world_resource_sites(self, world: World):
        """
        Load all resource sites for a world entity.
        
        Args:
            world (World): The world entity to load resource sites for
        """
        try:
            sites = self.db.query(ResourceSites).filter(
                ResourceSites.world_id == world.world_id
            ).all()
            
            for site in sites:
                # Register each resource site with the world
                world.register_resource_site(
                    site_id=str(site.resource_site_id),
                    name=site.site_name,
                    site_type=site.resource_type or "generic",
                    area_id=str(site.area_id)
                )
                
        except Exception as e:
            logger.exception(f"Error loading resource sites for world {world.world_id}: {e}")
    
    def save_world(self, world: World) -> bool:
        """
        Save a world entity to the database.
        
        Args:
            world (World): The world entity to save
            
        Returns:
            bool: True if saved successfully, False otherwise
        """
        # TODO: Replace with world manager when implemented
        # return self.world_manager.save_world(world)
        
        try:
            # Skip if no changes to save
            if not world.is_dirty():
                return True
                
            # Get or create world record
            world_db = self.db.query(Worlds).filter(Worlds.world_id == world.world_id).first()
            if not world_db:
                # Create new world record
                world_db = Worlds()
                world_db.world_id = world.world_id
                world_db.created_at = datetime.now()
                
            # Update fields
            world_db.world_name = world.name
            world_db.description = world.description or f"A world named {world.name}"
            world_db.current_game_day = world.current_game_day
            world_db.current_season = world.current_season
            world_db.day_of_season = world.day_of_season
            world_db.days_per_season = world.days_per_season
            world_db.current_year = world.current_year
            world_db.last_updated = datetime.now()
            
            # Save to database
            self.db.add(world_db)
            self.db.commit()
            
            # Mark entity as clean
            world.mark_clean()
            
            logger.info(f"Saved world {world.name} (ID: {world.world_id})")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.exception(f"Error saving world {world.world_id}: {e}")
            return False
    
    def create_world(self, name: str, description: Optional[str] = None) -> Optional[World]:
        """
        Create a new world entity.
        
        Args:
            name (str): Name of the world
            description (Optional[str]): Description of the world
            
        Returns:
            Optional[World]: The newly created world entity, or None if creation failed
        """
        try:
            # Generate a new world ID
            world_id = str(uuid.uuid4())
            
            # Create world entity
            world = World(world_id)
            world.set_basic_info(name=name, description=description)
            
            # Set default time values
            world.current_game_day = 1
            world.current_season = "spring"
            world.day_of_season = 1
            world.days_per_season = 30
            world.current_year = 1
            
            # Save to database
            if self.save_world(world):
                logger.info(f"Created new world: {name} (ID: {world_id})")
                return world
            else:
                logger.error(f"Failed to save new world {name}")
                return None
                
        except Exception as e:
            logger.exception(f"Error creating world {name}: {e}")
            return None
    
    def advance_world_day(self, world_id: str) -> Dict[str, Any]:
        """
        Advance a world by one game day.
        
        Args:
            world_id (str): The ID of the world to advance
            
        Returns:
            Dict[str, Any]: Result of the day advancement
        """
        try:
            # Load the world entity
            world = self.get_world(world_id)
            if not world:
                return {"status": "error", "message": f"World {world_id} not found"}
            
            # Advance the day
            season_changed = world.advance_day()
            
            # Update weather if needed
            world.generate_weather()
            
            # Update events
            ended_events = world.update_events()
            
            # If season changed, update economy
            if season_changed:
                world.calculate_resource_scarcity()
                world.update_economy()
            
            # Save changes to database
            if not self.save_world(world):
                return {"status": "error", "message": "Failed to save world changes"}
            
            # Return results
            result = {
                "status": "success",
                "day": world.current_game_day,
                "season": world.current_season,
                "year": world.current_year,
                "day_of_season": world.day_of_season,
                "season_changed": season_changed,
                "ended_events": len(ended_events)
            }
            
            logger.info(f"Advanced world {world.name} to day {world.current_game_day}")
            return result
            
        except Exception as e:
            logger.exception(f"Error advancing world day for {world_id}: {e}")
            return {"status": "error", "message": f"Error advancing day: {str(e)}"}
    
    def trigger_world_event(self, world_id: str, event_type: str, location: Tuple[float, float], 
                         radius: float, duration: int, name: Optional[str] = None, 
                         description: Optional[str] = None) -> Dict[str, Any]:
        """
        Trigger a new world event.
        
        Args:
            world_id (str): The ID of the world
            event_type (str): Type of event (natural_disaster, war, festival, etc.)
            location (Tuple[float, float]): (x, y) coordinates of event center
            radius (float): Area of effect radius
            duration (int): Duration in game days
            name (Optional[str]): Name of the event
            description (Optional[str]): Description of the event
            
        Returns:
            Dict[str, Any]: Result of event creation
        """
        try:
            # Load the world entity
            world = self.get_world(world_id)
            if not world:
                return {"status": "error", "message": f"World {world_id} not found"}
            
            # Trigger the event
            event_id = world.trigger_world_event(
                event_type=event_type,
                location=location,
                radius=radius,
                duration=duration,
                name=name,
                description=description
            )
            
            # Save changes to database
            if not self.save_world(world):
                return {"status": "error", "message": "Failed to save world changes"}
            
            # Get the created event details
            event_details = next((e for e in world.active_events if e["event_id"] == event_id), None)
            
            # Return result
            return {
                "status": "success",
                "event_id": event_id,
                "event_name": event_details["name"] if event_details else name or f"{event_type} Event",
                "start_day": world.current_game_day,
                "end_day": world.current_game_day + duration
            }
            
        except Exception as e:
            logger.exception(f"Error triggering world event for {world_id}: {e}")
            return {"status": "error", "message": f"Error triggering event: {str(e)}"}
    
    def get_active_world_events(self, world_id: str) -> Dict[str, Any]:
        """
        Get all active events in a world.
        
        Args:
            world_id (str): The ID of the world
            
        Returns:
            Dict[str, Any]: List of active events and their details
        """
        try:
            # Load the world entity
            world = self.get_world(world_id)
            if not world:
                return {"status": "error", "message": f"World {world_id} not found"}
            
            # Return active events
            return {
                "status": "success",
                "events": world.active_events,
                "count": len(world.active_events)
            }
            
        except Exception as e:
            logger.exception(f"Error getting active events for world {world_id}: {e}")
            return {"status": "error", "message": f"Error getting events: {str(e)}"}
    
    def update_faction_relation(self, world_id: str, faction_id: str, 
                              other_faction_id: str, relation_value: float) -> Dict[str, Any]:
        """
        Update the relation between two factions in a world.
        
        Args:
            world_id (str): The ID of the world
            faction_id (str): ID of the first faction
            other_faction_id (str): ID of the second faction
            relation_value (float): New relation value (-1.0 to 1.0)
            
        Returns:
            Dict[str, Any]: Result of the relation update
        """
        try:
            # Load the world entity
            world = self.get_world(world_id)
            if not world:
                return {"status": "error", "message": f"World {world_id} not found"}
            
            # Set the relation
            world.set_faction_relation(faction_id, other_faction_id, relation_value)
            
            # Save changes to database
            if not self.save_world(world):
                return {"status": "error", "message": "Failed to save world changes"}
            
            # Return result
            return {
                "status": "success",
                "faction_id": faction_id,
                "other_faction_id": other_faction_id,
                "relation_value": relation_value
            }
            
        except Exception as e:
            logger.exception(f"Error updating faction relation in world {world_id}: {e}")
            return {"status": "error", "message": f"Error updating relation: {str(e)}"}
    
    def process_all_worlds(self) -> Dict[str, Any]:
        """
        Process all worlds, advancing time and updating state.
        
        Returns:
            Dict[str, Any]: Result of processing all worlds
        """
        try:
            # Query all active worlds
            worlds = self.db.query(Worlds).filter(Worlds.active == True).all()
            
            processed_count = 0
            results = []
            
            for world_db in worlds:
                try:
                    # Advance this world's day
                    result = self.advance_world_day(str(world_db.world_id))
                    
                    if result["status"] == "success":
                        processed_count += 1
                        results.append({
                            "world_id": str(world_db.world_id),
                            "world_name": world_db.world_name,
                            "day": result["day"],
                            "season": result["season"],
                            "season_changed": result["season_changed"]
                        })
                    else:
                        logger.warning(f"Failed to process world {world_db.world_id}: {result.get('message')}")
                        
                except Exception as e:
                    logger.exception(f"Error processing world {world_db.world_id}: {e}")
            
            return {
                "status": "success",
                "total": len(worlds),
                "processed": processed_count,
                "results": results
            }
            
        except Exception as e:
            logger.exception(f"Error processing all worlds: {e}")
            return {"status": "error", "message": f"Error processing worlds: {str(e)}"}
