import json
import uuid
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy import select, insert, update, delete
from sqlalchemy.orm import Session
from database.connection import SessionLocal

from app.models.settlement import SettlementModel
from app.game_state.entities.settlement import Settlement

logger = logging.getLogger(__name__)

class SettlementManager:
    """
    Manages persistence and lifecycle for Settlement entities.
    
    Responsibilities:
      1. Loading settlements from the database.
      2. Saving settlements to the database.
      3. Creating new settlements.
      4. Maintaining a cache of loaded settlements.
      5. Providing query methods.
    """
    
    def __init__(self):
        self.settlements = {}  # Cache: settlement_id -> Settlement (domain entity)
        logger.info(f"{self.__class__.__name__} initialized")
    
    def create_settlement(self, name: str, description: Optional[str] = None) -> Settlement:
        """
        Create a new settlement with a unique ID.
        """
        settlement_id = str(uuid.uuid4())
        settlement = Settlement(settlement_id=settlement_id, name=name, description=description)
        settlement.set_basic_info(name, description or f"A settlement named {name}")
        self.settlements[settlement_id] = settlement
        self.save_settlement(settlement)
        logger.info(f"Created new settlement: {name} (ID: {settlement_id})")
        return settlement

    def load_settlement(self, settlement_id: str) -> Optional[Settlement]:
        """
        Load a settlement from cache or database, including buildings and resources.
        """
        # Return from cache if available
        if settlement_id in self.settlements:
            return self.settlements[settlement_id]
        
        session: Session = SessionLocal()
        try:
            # Load settlement data from both models to get complete information
            stmt_model = select(SettlementModel).where(SettlementModel.settlement_id == settlement_id)
            result_model = session.execute(stmt_model).scalars().first()
            
            # Also load from Settlements in core.py to get world_id
            from app.models.core import Settlements
            stmt_core = select(Settlements).where(Settlements.settlement_id == settlement_id)
            result_core = session.execute(stmt_core).scalars().first()
            
            if not result_model or not result_core:
                logger.warning(f"Settlement not found: {settlement_id}")
                return None
            
            # Convert the ORM model to a dictionary, then to a domain Settlement
            settlement_data = result_model.to_dict()
            
            # Create the settlement entity
            settlement = Settlement.from_dict(settlement_data)
            
            # Add world_id from core model
            settlement.set_property("world_id", result_core.world_id)
            
            # Load buildings for this settlement
            from app.models.buildings import SettlementBuilding
            buildings_query = session.query(SettlementBuilding).filter(
                SettlementBuilding.settlement_id == settlement_id
            )
            buildings = buildings_query.all()
            
            # Add buildings to settlement
            buildings_data = []
            for building in buildings:
                building_data = {
                    "building_id": str(building.settlement_building_id),
                    "type": str(building.building_type_id) if building.building_type_id else "unknown",
                    "construction_status": building.construction_status,
                    "construction_progress": float(building.construction_progress) if building.construction_progress else 0,
                    "is_operational": building.is_operational,
                    "health": building.health,
                    "constructed_at": building.constructed_at.isoformat() if building.constructed_at else None
                }
                buildings_data.append(building_data)
            
            # Store buildings in settlement entity
            settlement.set_property("buildings", buildings_data)
            
            # Load resources for this settlement
            from app.models.core import SettlementResources
            resources_query = session.query(SettlementResources).filter(
                SettlementResources.settlement_id == settlement_id
            )
            resources = resources_query.all()
            
            # Add resources to settlement
            resources_data = {}
            for resource in resources:
                resources_data[resource.resource_type_id] = resource.quantity
            
            # Store resources in settlement entity
            settlement.set_property("resources", resources_data)
            
            # Cache and return the settlement
            self.settlements[settlement_id] = settlement
            logger.info(f"Loaded settlement: {settlement.settlement_name} (ID: {settlement_id}) with {len(buildings_data)} buildings and {len(resources_data)} resource types")
            return settlement
            
        except Exception as e:
            logger.error(f"Error loading settlement {settlement_id}: {e}")
            return None
        finally:
            session.close()

    def save_settlement(self, settlement: Settlement) -> bool:
        """
        Save (insert or update) a settlement to the database.
        """
        if not settlement.is_dirty:
            return True

        try:
            # Get the settlement dictionary
            settlement_dict = settlement.to_dict()
            
            # Recursively convert any remaining UUIDs to strings
            import uuid
            
            def convert_uuid_values(obj):
                if isinstance(obj, dict):
                    return {k: convert_uuid_values(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_uuid_values(item) for item in obj]
                elif isinstance(obj, uuid.UUID):
                    return str(obj)
                else:
                    return obj
            
            # Convert any UUIDs in the dict
            settlement_dict = convert_uuid_values(settlement_dict)
            
            # Use a custom JSON encoder as a backup
            class UUIDEncoder(json.JSONEncoder):
                def default(self, obj):
                    if isinstance(obj, uuid.UUID):
                        return str(obj)
                    return json.JSONEncoder.default(self, obj)
            
            # Serialize to JSON
            try:
                settlement_data = json.dumps(settlement_dict, cls=UUIDEncoder)
            except TypeError as e:
                # If we still have UUID conversion issues, log the problematic keys
                logger.error(f"JSON serialization error: {e}")
                # Debug by printing each top-level key's type
                for key, value in settlement_dict.items():
                    if isinstance(value, dict):
                        logger.error(f"Key '{key}' is a dict with keys: {list(value.keys())}")
                    else:
                        logger.error(f"Key '{key}' has value of type: {type(value)}")
                raise
        except Exception as e:
            logger.error(f"Error serializing settlement {settlement.settlement_id}: {e}")
            return False

        session: Session = SessionLocal()
        try:
            # Check if a record already exists
            stmt = select(SettlementModel).where(SettlementModel.settlement_id == settlement.settlement_id)
            existing = session.execute(stmt).scalars().first()

            if existing:
                # Update record
                upd = (
                    update(SettlementModel)
                    .where(SettlementModel.settlement_id == settlement.settlement_id)
                    .values(
                        settlement_name=settlement.settlement_name,
                        description=settlement.description,
                        location_id=settlement.location_id,
                        relations=settlement_dict.get("relations", {}),  # Use the UUID-converted dict
                        is_repairable=settlement.is_repairable,
                        is_damaged=settlement.is_damaged,
                        has_started_building=settlement.has_started_building,
                        is_under_repair=settlement.is_under_repair,
                        is_built=settlement.is_built,
                        properties=settlement_dict.get("properties", {})  # Use the UUID-converted dict
                    )
                )
                session.execute(upd)
            else:
                # Insert new record - create a new dict with the correct field names
                model_dict = {
                    "settlement_id": settlement_dict.get("id"),
                    "settlement_name": settlement_dict.get("name"),
                    "description": settlement_dict.get("description"),
                    "location_id": settlement_dict.get("location_id"),
                    "relations": settlement_dict.get("relations", {}),
                    "is_repairable": settlement_dict.get("is_repairable", False),
                    "is_damaged": settlement_dict.get("is_damaged", False),
                    "has_started_building": settlement_dict.get("has_started_building", False),
                    "is_under_repair": settlement_dict.get("is_under_repair", False),
                    "is_built": settlement_dict.get("is_built", False),
                    "properties": settlement_dict.get("properties", {})
                }
                new_settlement = SettlementModel(**model_dict)
                session.add(new_settlement)
            session.commit()
            settlement.clean()
            logger.info(f"Saved settlement: {settlement.settlement_name} (ID: {settlement.settlement_id})")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save settlement {settlement.settlement_id}: {e}")
            return False
        finally:
            session.close()

    def delete_settlement(self, settlement_id: str) -> bool:
        """
        Delete a settlement from the database and cache.
        """
        self.settlements.pop(settlement_id, None)
        session: Session = SessionLocal()
        try:
            stmt = delete(SettlementModel).where(SettlementModel.settlement_id == settlement_id)
            session.execute(stmt)
            session.commit()
            logger.info(f"Deleted settlement: {settlement_id}")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to delete settlement {settlement_id}: {e}")
            return False
        finally:
            session.close()

    def get_all_settlements(self) -> List[Settlement]:
        """
        Retrieve all settlements from the database.
        """
        session: Session = SessionLocal()
        try:
            # Get all settlement IDs first
            stmt = select(SettlementModel.settlement_id)
            results = session.execute(stmt).scalars().all()
            settlements = []
            
            # Load each settlement individually to get complete data
            for settlement_id in results:
                settlement = self.load_settlement(settlement_id)
                if settlement:
                    settlements.append(settlement)
                    
            return settlements
        except Exception as e:
            logger.error(f"Error fetching all settlements: {e}")
            return []
        finally:
            session.close()

    def get_settlements_by_location(self, location_id: str) -> List[Settlement]:
        """
        Retrieve settlements at a specific location.
        """
        session: Session = SessionLocal()
        try:
            # Get settlement IDs at this location
            stmt = select(SettlementModel.settlement_id).where(SettlementModel.location_id == location_id)
            results = session.execute(stmt).scalars().all()
            settlements = []
            
            # Load each settlement individually to get complete data
            for settlement_id in results:
                settlement = self.load_settlement(settlement_id)
                if settlement:
                    settlements.append(settlement)
                    
            return settlements
        except Exception as e:
            logger.error(f"Error fetching settlements at location {location_id}: {e}")
            return []
        finally:
            session.close()

    def get_settlement_by_name(self, name: str) -> Optional[Settlement]:
        """
        Find a settlement by name.
        """
        session: Session = SessionLocal()
        try:
            stmt = select(SettlementModel.settlement_id).where(SettlementModel.settlement_name == name)
            result = session.execute(stmt).scalars().first()
            if result:
                return self.load_settlement(result)
            return None
        except Exception as e:
            logger.error(f"Error fetching settlement by name {name}: {e}")
            return None
        finally:
            session.close()

    def update_settlement_location(self, settlement_id: str, location_id: str) -> bool:
        """
        Update the location of a settlement.
        """
        settlement = self.load_settlement(settlement_id)
        if not settlement:
            logger.warning(f"Settlement not found for update: {settlement_id}")
            return False
        settlement.set_location(location_id)
        return self.save_settlement(settlement)

    def save_all_settlements(self) -> bool:
        """
        Save all loaded (dirty) settlements.
        """
        success = True
        for settlement in self.settlements.values():
            if settlement.is_dirty():
                if not self.save_settlement(settlement):
                    success = False
        return success

    def get_settlement_count(self) -> int:
        """
        Return the total number of settlements in the database.
        """
        session: Session = SessionLocal()
        try:
            stmt = select(SettlementModel)
            results = session.execute(stmt).scalars().all()
            return len(results)
        except Exception as e:
            logger.error(f"Error counting settlements: {e}")
            return 0
        finally:
            session.close()

    def soft_delete_settlement(self, settlement_id: str) -> bool:
        """
        Soft delete a settlement by marking it as inactive.
        (Assumes your domain Settlement supports an 'is_active' attribute.)
        """
        settlement = self.load_settlement(settlement_id)
        if not settlement:
            logger.warning(f"Settlement not found for soft delete: {settlement_id}")
            return False
        settlement.is_active = False
        return self.save_settlement(settlement)

    def update_resource_site_rumors(self, settlement_id: str) -> int:
        """
        Check if any undiscovered resource sites should become rumored.
        
        Args:
            settlement_id (str): The ID of the settlement to check
            
        Returns:
            int: Number of sites that became rumored
        """
        settlement = self.load_settlement(settlement_id)
        if not settlement:
            logger.warning(f"Settlement not found for update_resource_site_rumors: {settlement_id}")
            return 0
        
        from app.models.resource_sites import ResourceSite, SiteType
        import random
        
        session = SessionLocal()
        try:
            # Get undiscovered sites for this settlement
            undiscovered_sites = session.query(ResourceSite).filter(
                ResourceSite.settlement_id == settlement_id,
                ResourceSite.current_stage == "undiscovered"
            ).all()
            
            updated_sites = []
            
            for site in undiscovered_sites:
                # Random chance based on development level of the settlement
                development_level = settlement.get_property("development_level", 0)
                base_chance = 0.05  # 5% base chance per check
                development_bonus = development_level * 0.1  # +10% per development level
                
                # Check if the settlement has explorers/scouts
                professions = settlement.get_property("professions", {})
                scout_bonus = 0
                if professions.get("scout", {}).get("count", 0) > 0 or professions.get("explorer", {}).get("count", 0) > 0:
                    scout_bonus = 0.1  # +10% with scouts/explorers
                
                # Roll for rumor generation
                final_chance = base_chance + development_bonus + scout_bonus
                
                if random.random() < final_chance:
                    # Site becomes rumored
                    site.current_stage = "rumored"
                    updated_sites.append(site)
                    
                    # Add a settlement event
                    self._add_settlement_event(
                        settlement_id, 
                        "Rumors of a potential resource site have been circulating among the villagers."
                    )
            
            # Commit changes
            if updated_sites:
                session.commit()
                logger.info(f"Updated {len(updated_sites)} resource sites to 'rumored' status for settlement {settlement_id}")
                
            return len(updated_sites)
        
        finally:
            session.close()

    def _add_settlement_event(self, settlement_id: str, message: str) -> bool:
        """
        Add an event message to the settlement's history.
        
        Args:
            settlement_id (str): The ID of the settlement
            message (str): The event message
            
        Returns:
            bool: Success status
        """
        settlement = self.load_settlement(settlement_id)
        if not settlement:
            return False
        
        events = settlement.get_property("events", [])
        
        # Get current date
        from datetime import datetime
        current_date = datetime.now()
        
        # Create event
        event = {
            "date": current_date.isoformat(),
            "message": message
        }
        
        # Add event to list (keep last 50 events)
        events.append(event)
        if len(events) > 50:
            events = events[-50:]
        
        # Update settlement
        settlement.set_property("events", events)
        
        # Save settlement
        return self.save_settlement(settlement)

    def get_settlement_resource_sites(self, settlement_id: str) -> list:
        """
        Get all resource sites for a settlement.
        
        Args:
            settlement_id (str): The settlement ID
            
        Returns:
            list: List of resource sites with their types
        """
        from app.models.resource_sites import ResourceSite, SiteType
        
        session = SessionLocal()
        try:
            # Get the settlement's resource sites
            sites = session.query(ResourceSite, SiteType).join(
                SiteType, ResourceSite.site_type_id == SiteType.site_type_id
            ).filter(
                ResourceSite.settlement_id == settlement_id
            ).all()
            
            # Convert to dictionaries
            site_data = []
            for site, site_type in sites:
                site_data.append({
                    "site_id": str(site.site_id),
                    "settlement_id": str(site.settlement_id),
                    "site_type_id": str(site.site_type_id),
                    "site_type_name": site_type.name,
                    "resource_category": site_type.resource_category,
                    "resource_output": site_type.resource_output,
                    "current_stage": site.current_stage,
                    "depletion_level": site.depletion_level,
                    "development_level": site.development_level,
                    "production_multiplier": site.production_multiplier,
                    "discovery_date": site.discovery_date.isoformat() if site.discovery_date else None,
                    "last_updated": site.last_updated.isoformat() if site.last_updated else None,
                    "associated_building_id": str(site.associated_building_id) if site.associated_building_id else None
                })
            
            return site_data
            
        finally:
            session.close()

        # Additional methods (pagination, cache refresh, bulk operations, etc.)
        def clear_cache(self) -> None:
            """Clear the settlements cache."""
            self.settlements.clear()
            logger.info("Settlement cache cleared")

        def refresh_cache(self, settlement_id: str) -> Optional[Settlement]:
            """Refresh a specific settlement in the cache."""
            settlement = self.load_settlement(settlement_id)
            if settlement:
                self.settlements[settlement_id] = settlement
            return settlement
