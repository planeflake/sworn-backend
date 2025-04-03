# app/game_state/managers/resource_manager.py
from typing import List, Dict, Optional, Any, Union
from sqlalchemy import Column, String, Text, Table, MetaData
from sqlalchemy import select, insert, update, delete
from sqlalchemy.orm import Session
from database.connection import get_db
import logging
import json
import uuid
from datetime import datetime
from typing import List, Dict, Set, Optional, Any, Callable

from app.game_state.entities.resource import (
    Resource, ResourceType, ResourceRarity, ResourceQuality, 
    MaterialState, ElementalAffinity, UsageCategory
)
from database.connection import SessionLocal
from app.game_state.services.logging_service import LoggingService
from app.models.core import ResourceSites as ResourceSite, ResourceSiteTypes as SiteType

logger = logging.getLogger(__name__)

class ResourceManager:
    """
    Manager for Resource entities that handles persistence and lifecycle.
    
    Responsible for:
    1. Loading resources from the database
    2. Saving resources to the database
    3. Creating new resources
    4. Maintaining a cache of loaded resources
    5. Providing query methods for finding resources
    """
    
    def __init__(self,db):
        """Initialize the ResourceManager."""
        # Cache of loaded resources
        self.resources = {}  # Dictionary to store loaded resources by ID
        self.db = db  # Store the database session
        
        # Set up database metadata
        self._setup_db_metadata()
        
        logger.info(f"{self.__class__.__name__} initialized")   
             
    def _setup_db_metadata(self):
        """Set up SQLAlchemy metadata for the resources table."""
        self.metadata = MetaData()
        
        # Define the table structure for resources
        self.resources_table = Table(
            'resources',  # Using the actual resources table name
            self.metadata,
            Column('id', String(36), primary_key=True),
            Column('name', String(100)),
            Column('resource_type', String(50)),
            Column('rarity', String(20)),
            Column('quality', String(20)),
            Column('location_id', String(36)),
            Column('owner_id', String(36)),
            Column('data', Text)  # JSON data column
        )
    
    def create_resource(self, name: str, description: Optional[str] = None,
                       resource_type: Optional[ResourceType] = None) -> Resource:
        """
        Create a new resource with a unique ID.
        
        Args:
            name: The resource's name
            description: Optional description
            resource_type: Optional resource type
            
        Returns:
            Resource: The newly created resource
        """
        # Create a new resource instance
        resource = Resource(name=name, description=description)
        
        # Set resource type if provided
        if resource_type:
            resource.resource_type = resource_type
        
        # Add to cache
        self.resources[resource.id] = resource
        
        # Save to database
        self.save_resource(resource)
        
        logger.info(f"Created new resource: {name} (ID: {resource.id})")
        return resource
    
    def load_resource(self, resource_id: str) -> Optional[Resource]:
        """
        Load a resource from the database or cache.
        
        Args:
            resource_id: The ID of the resource to load
            
        Returns:
            Resource: The loaded resource, or None if not found
        """
        # Check if already loaded in cache
        if resource_id in self.resources:
            return self.resources[resource_id]
        
        # Load from database
        db = get_db()
        with Session(db) as session:
            stmt = select(self.resources_table).where(
                self.resources_table.c.id == resource_id
            )
            result = session.execute(stmt).first()
            
            if result is None:
                logger.warning(f"Resource not found: {resource_id}")
                return None
            
            # Deserialize resource data
            try:
                resource_data = json.loads(result.data)
                resource = Resource.from_dict(resource_data)
                
                # Cache the resource
                self.resources[resource_id] = resource
                
                logger.info(f"Loaded resource: {resource.name} (ID: {resource_id})")
                return resource
                
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Error deserializing resource {resource_id}: {e}")
                return None
    
    def save_resource(self, resource: Resource) -> bool:
        """
        Save a resource to the database.
        
        Args:
            resource: The resource to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Skip if no changes to save
        if not resource.is_dirty:
            return True
        
        # Convert resource to JSON
        try:
            resource_dict = resource.to_dict()
            resource_data = json.dumps(resource_dict)
            
            # Save to database
            db = get_db()
            with Session(db) as session:
                try:
                    # Check if resource already exists
                    stmt = select(self.resources_table).where(
                        self.resources_table.c.id == resource.id
                    )
                    exists = session.execute(stmt).first() is not None
                    
                    if exists:
                        # Update existing resource
                        stmt = update(self.resources_table).where(
                            self.resources_table.c.id == resource.id
                        ).values(
                            name=resource.name,
                            resource_type=resource.resource_type.value if resource.resource_type else None,
                            rarity=str(resource.rarity.value) if resource.rarity else None,
                            quality=str(resource.quality.value) if resource.quality else None,
                            location_id=resource.location_id,
                            owner_id=resource.owner_id,
                            data=resource_data
                        )
                        session.execute(stmt)
                    else:
                        # Insert new resource
                        stmt = insert(self.resources_table).values(
                            id=resource.id,
                            name=resource.name,
                            resource_type=resource.resource_type.value if resource.resource_type else None,
                            rarity=str(resource.rarity.value) if resource.rarity else None,
                            quality=str(resource.quality.value) if resource.quality else None,
                            location_id=resource.location_id,
                            owner_id=resource.owner_id,
                            data=resource_data
                        )
                        session.execute(stmt)
                    
                    session.commit()
                    
                    # Mark resource as clean (no unsaved changes)
                    resource.clean()
                    
                    logger.info(f"Saved resource: {resource.name} (ID: {resource.id})")
                    return True
                    
                except Exception as e:
                    session.rollback()
                    logger.error(f"Failed to save resource {resource.id}: {str(e)}")
                    return False
        
        except Exception as e:
            logger.error(f"Error serializing resource {resource.id}: {str(e)}")
            return False
    
    def delete_resource(self, resource_id: str) -> bool:
        """
        Delete a resource from the database.
        
        Args:
            resource_id: The ID of the resource to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Remove from cache if present
        if resource_id in self.resources:
            del self.resources[resource_id]
        
        # Delete from database
        db = get_db()
        with Session(db) as session:
            try:
                stmt = delete(self.resources_table).where(
                    self.resources_table.c.id == resource_id
                )
                session.execute(stmt)
                session.commit()
                
                logger.info(f"Deleted resource: {resource_id}")
                return True
                
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to delete resource {resource_id}: {str(e)}")
                return False
    
    def get_all_resources(self) -> List[Resource]:
        """
        Get all resources from the database.
        
        Returns:
            List[Resource]: List of all resources
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.resources_table.c.id)
            results = session.execute(stmt).fetchall()
            
            resources = []
            for result in results:
                resource_id = result[0]
                resource = self.load_resource(resource_id)
                if resource:
                    resources.append(resource)
            
            return resources
    
    def get_resources_at_location(self, location_id: str) -> List[Resource]:
        """
        Get all resources at a specific location.
        
        Args:
            location_id: The location ID
            
        Returns:
            List[Resource]: List of resources at the location
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.resources_table.c.id).where(
                self.resources_table.c.location_id == location_id
            )
            results = session.execute(stmt).fetchall()
            
            resources = []
            for result in results:
                resource_id = result[0]
                resource = self.load_resource(resource_id)
                if resource:
                    resources.append(resource)
            
            return resources
    
    def get_resources_by_owner(self, owner_id: str) -> List[Resource]:
        """
        Get all resources owned by a specific entity.
        
        Args:
            owner_id: The owner ID
            
        Returns:
            List[Resource]: List of resources owned by the entity
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.resources_table.c.id).where(
                self.resources_table.c.owner_id == owner_id
            )
            results = session.execute(stmt).fetchall()
            
            resources = []
            for result in results:
                resource_id = result[0]
                resource = self.load_resource(resource_id)
                if resource:
                    resources.append(resource)
            
            return resources
    
    def get_resource_by_name(self, name: str) -> Optional[Resource]:
        """
        Find a resource by name.
        
        Args:
            name: The name to search for
            
        Returns:
            Resource: The resource with the given name, or None if not found
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.resources_table.c.id).where(
                self.resources_table.c.name == name
            )
            result = session.execute(stmt).first()
            
            if result:
                return self.load_resource(result[0])
            
            return None
    
    def get_resources_by_type(self, resource_type: ResourceType) -> List[Resource]:
        """
        Get all resources of a specific type.
        
        Args:
            resource_type: The type of resource to find
            
        Returns:
            List[Resource]: List of resources of the specified type
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.resources_table.c.id).where(
                self.resources_table.c.resource_type == resource_type.value
            )
            results = session.execute(stmt).fetchall()
            
            resources = []
            for result in results:
                resource_id = result[0]
                resource = self.load_resource(resource_id)
                if resource:
                    resources.append(resource)
            
            return resources
    
    def update_resource_location(self, resource_id: str, location_id: str) -> bool:
        """
        Update a resource's location.
        
        Args:
            resource_id: The resource ID
            location_id: The new location ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        resource = self.load_resource(resource_id)
        if not resource:
            logger.warning(f"Cannot update location: Resource not found: {resource_id}")
            return False
        
        resource.set_location(location_id)
        return self.save_resource(resource)
    
    def save_all_resources(self) -> bool:
        """
        Save all loaded resources to the database.
        
        Returns:
            bool: True if all saves were successful
        """
        success = True
        for resource in self.resources.values():
            if resource.is_dirty:
                if not self.save_resource(resource):
                    success = False
        
        return success
    
    def get_resource_count(self) -> int:
        """
        Get the total number of resources.
        
        Returns:
            int: The total count of resources
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.resources_table)
            result = session.execute(stmt).all()
            return len(result)

    def update_resource(self, resource_id: str, **kwargs) -> Optional[Resource]:
        """
        Update a resource's attributes.
        
        Args:
            resource_id: The ID of the resource to update
            **kwargs: Key-value pairs of attributes to update
            
        Returns:
            Resource: The updated resource, or None if not found
        """
        resource = self.load_resource(resource_id)
        if not resource:
            logger.warning(f"Resource not found for update: {resource_id}")
            return None

        for key, value in kwargs.items():
            if hasattr(resource, key):
                setattr(resource, key, value)
            else:
                resource.set_property(key, value)
        
        if self.save_resource(resource):
            logger.info(f"Updated resource: {resource_id}")
            return resource
        return None

    def load_resources(self, resource_ids: List[str]) -> List[Resource]:
        """
        Load multiple resources from the database.
        
        Args:
            resource_ids: A list of resource IDs to load
            
        Returns:
            List[Resource]: A list of loaded resources
        """
        resources = []
        for resource_id in resource_ids:
            resource = self.load_resource(resource_id)
            if resource:
                resources.append(resource)
        return resources

    def clear_cache(self) -> None:
        """
        Clear the cache of loaded resources.
        """
        self.resources.clear()
        logger.info("Resource cache cleared")

    def refresh_cache(self, resource_id: str) -> Optional[Resource]:
        """
        Refresh a specific resource in the cache.
        
        Args:
            resource_id: The ID of the resource to refresh
            
        Returns:
            Resource: The refreshed resource, or None if not found
        """
        # Remove from cache if present
        if resource_id in self.resources:
            del self.resources[resource_id]
            
        # Reload from database
        return self.load_resource(resource_id)

    def get_resources_by_quality(self, quality: ResourceQuality) -> List[Resource]:
        """
        Get all resources of a specific quality.
        
        Args:
            quality: The quality level to search for
            
        Returns:
            List[Resource]: List of resources with the specified quality
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.resources_table.c.id).where(
                self.resources_table.c.quality == str(quality.value)
            )
            results = session.execute(stmt).fetchall()
            
            resources = []
            for result in results:
                resource_id = result[0]
                resource = self.load_resource(resource_id)
                if resource:
                    resources.append(resource)
            
            return resources
    
    def get_resources_by_rarity(self, rarity: ResourceRarity) -> List[Resource]:
        """
        Get all resources of a specific rarity.
        
        Args:
            rarity: The rarity level to search for
            
        Returns:
            List[Resource]: List of resources with the specified rarity
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.resources_table.c.id).where(
                self.resources_table.c.rarity == str(rarity.value)
            )
            results = session.execute(stmt).fetchall()
            
            resources = []
            for result in results:
                resource_id = result[0]
                resource = self.load_resource(resource_id)
                if resource:
                    resources.append(resource)
            
            return resources
    
    def get_resources_paginated(self, page: int, page_size: int) -> List[Resource]:
        """
        Retrieve resources with pagination.
        
        Args:
            page: The page number (1-based index)
            page_size: The number of resources per page
            
        Returns:
            List[Resource]: A list of resources for the given page
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.resources_table.c.id).offset((page - 1) * page_size).limit(page_size)
            results = session.execute(stmt).fetchall()
            
            resources = []
            for result in results:
                resource_id = result[0]
                resource = self.load_resource(resource_id)
                if resource:
                    resources.append(resource)
            return resources

    def get_settlement_resource_sites(self, settlement_id: str) -> List[Dict[str, Any]]:
        """
        Get all resource sites for a settlement.
        
        Args:
            settlement_id (str): The settlement ID
            
        Returns:
            List[Dict[str, Any]]: List of resource sites with their details
        """
        try:
            # Get the settlement's resource sites with their types
            sites = self.db.query(ResourceSite, SiteType).join(
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
        except Exception as e:
            logger.error(f"Error fetching resource sites for settlement {settlement_id}: {e}")
            return []
    
    def update_resource_site_rumors(self, settlement_id: str) -> int:
        """
        Check if any undiscovered resource sites should become rumored.
        
        Args:
            settlement_id (str): The settlement ID
            
        Returns:
            int: Number of sites that became rumored
        """
        try:
            # Get undiscovered sites for this settlement
            undiscovered_sites = self.db.query(ResourceSite).filter(
                ResourceSite.settlement_id == settlement_id,
                ResourceSite.current_stage == "undiscovered"
            ).all()
            
            updated_sites = []
            
            from app.game_state.managers.settlement_manager import SettlementManager
            settlement_manager = SettlementManager()
            settlement = settlement_manager.load_settlement(settlement_id)
            
            if not settlement:
                return 0
                
            # Add missing import
            import random
                
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
                    
                    # Check if settlement has an add_event method, if not, add it as a property
                    if hasattr(settlement, 'add_event'):
                        settlement.add_event("Rumors of a potential resource site have been circulating among the villagers.")
                    else:
                        events = settlement.get_property("events", [])
                        events.append({
                            "date": datetime.now().isoformat(),
                            "message": "Rumors of a potential resource site have been circulating among the villagers."
                        })
                        settlement.set_property("events", events)
            
            # Commit changes
            if updated_sites:
                self.db.commit()
                settlement_manager.save_settlement(settlement)
                logger.info(f"Updated {len(updated_sites)} resource sites to 'rumored' status for settlement {settlement_id}")
                
            return len(updated_sites)
            
        except Exception as e:
            logger.error(f"Error updating resource site rumors for settlement {settlement_id}: {e}")
            return 0
    
    def update_resource_site(self, site_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a resource site with the provided updates.
        
        Args:
            site_id (str): The site ID
            updates (Dict[str, Any]): Dictionary of updates to apply
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            site = self.db.query(ResourceSite).filter(ResourceSite.site_id == site_id).first()
            
            if not site:
                logger.warning(f"Resource site not found: {site_id}")
                return False
            
            # Apply updates
            for key, value in updates.items():
                if hasattr(site, key):
                    setattr(site, key, value)
            
            # Always update last_updated
            site.last_updated = datetime.now()
            
            # If changing to discovered, set discovery date
            if "current_stage" in updates and updates["current_stage"] == "discovered" and not site.discovery_date:
                site.discovery_date = datetime.now()
            
            self.db.commit()
            logger.info(f"Updated resource site {site_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating resource site {site_id}: {e}")
            return False
    
    def create_resource_site(self, settlement_id: str, site_type_id: str, 
                            current_stage: str = "undiscovered", 
                            production_multiplier: float = 1.0) -> Optional[str]:
        """
        Create a new resource site.
        
        Args:
            settlement_id (str): The settlement ID
            site_type_id (str): The site type ID
            current_stage (str): Initial stage (default: undiscovered)
            production_multiplier (float): Production multiplier
            
        Returns:
            Optional[str]: Site ID if successful, None otherwise
        """
        try:
            site_id = uuid.uuid4()
            
            site = ResourceSite(
                site_id=site_id,
                settlement_id=settlement_id,
                site_type_id=site_type_id,
                current_stage=current_stage,
                depletion_level=0,
                development_level=0,
                production_multiplier=production_multiplier,
                discovery_date=datetime.now() if current_stage != "undiscovered" else None,
                last_updated=datetime.now()
            )
            
            self.db.add(site)
            self.db.commit()
            
            logger.info(f"Created new resource site {site_id} for settlement {settlement_id}")
            return str(site_id)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating resource site for settlement {settlement_id}: {e}")
            return None
    
    def process_resource_site(self, site_id: str) -> Dict[str, Any]:
        """
        Process a resource site for production and depletion.
        
        Args:
            site_id (str): The site ID
            
        Returns:
            Dict[str, Any]: Processing result
        """
        try:
            site = self.db.query(ResourceSite).options(
                joinedload(ResourceSite.site_type)
            ).filter(ResourceSite.site_id == site_id).first()
            
            if not site or site.current_stage == "undiscovered" or site.current_stage == "rumored":
                return {"status": "error", "message": "Site not found or not discoverable"}
            
            # Only produce resources from operational sites
            if site.current_stage not in ["mine", "farm", "camp", "garden", "outpost"]:
                return {"status": "info", "message": "Site not operational for production"}
            
            # Increase depletion slightly
            depletion_increase = random.uniform(0.001, 0.01)  # 0.1% to 1% per day
            
            # Apply development level to slow depletion
            if site.development_level:
                depletion_increase *= (1 - (site.development_level * 0.5))
            
            # Update depletion
            new_depletion = min(1.0, site.depletion_level + depletion_increase)
            site.depletion_level = new_depletion
            
            # Check if site is now depleted
            if new_depletion >= 1.0 and site.current_stage != "depleted":
                site.current_stage = "depleted"
                
            site.last_updated = datetime.now()
            self.db.commit()
            
            return {
                "status": "success",
                "site_id": str(site.site_id),
                "depletion_level": site.depletion_level,
                "current_stage": site.current_stage
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error processing resource site {site_id}: {e}")
            return {"status": "error", "message": f"Error processing site: {str(e)}"}