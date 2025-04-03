import logging as logger
from typing import List, Dict, Optional, Any


logger = logger.getLogger(__name__)

class Settlement:
    """
    Settlement entity representing villages, towns, and cities in the game world.
    
    Settlements have:
    1. A unique identifier
    2. Properties relevant to the settlement type
    3. Methods for settlement behaviors
    4. Serialization/deserialization methods for persistence
    5. State tracking to know when it needs to be saved
    """
    
    def __init__(self, settlement_id: str, name: Optional[str] = None, description: Optional[str] = None):
        """
        Initialize a settlement with a unique ID.
        
        Args:
            settlement_id (str): Unique identifier for this settlement
            name (str, optional): The settlement's name
            description (str, optional): A brief description of the settlement
        """
        self.settlement_id = settlement_id
        self.settlement_name = name
        self.description = description or (f"A settlement named {name}" if name else None)
        self.location_id = None
        self.relations = {}
        
        # Settlement-specific attributes
        self.is_repairable = False
        self.is_damaged = False
        self.has_started_building = False
        self.is_under_repair = False
        self.is_built = False
        self.hidden_resources = []
        self.get_required_services = []
        
        # Additional custom properties (for compatibility)
        self._properties = {}  # Ensure this is not None
        self._is_dirty = False
    
    def __repr__(self) -> str:
        return f"Settlement(id={self.settlement_id}, name='{self.settlement_name}')"
    
    def __str__(self) -> str:
        status = []
        if self.is_damaged:
            status.append("damaged")
        if self.is_under_repair:
            status.append("under repair")
        if self.is_built:
            status.append("built")
        
        status_str = ", ".join(status) if status else "normal"
        return f"{self.settlement_name} (Settlement, {status_str})"
    
    def get_hidden_resources(self) -> List[str]:
        """
        Get a list of hidden resources in the
        settlement that players can discover.
        """
        return self.get_property("hidden_resources", [])

    def set_hidden_resources(self, resources: List[str]) -> List[str]:
        """
        Set the list of hidden resources in the settlement.
        
        Args:
            resources (List[str]): List of resource IDs
        
        Returns:
            List[str]: List of resources that were added
        """
        added_resources = []
        for resource in resources:
            if resource not in self.get_hidden_resources():
                logger.info(f"Resource {resource} added to Settlement {self.settlement_id}")
                added_resources.append(resource)
                # Assuming there's a method to actually add the resource
                self.add_hidden_resource(resource)  # Example method call
        self._is_dirty = True
        return added_resources

    def remove_hidden_resources(self, resources: List[str]) -> List[str]:
        """
        Remove the list of hidden resources from the settlement.
        
        Args:
            resources (List[str]): List of resource IDs
        """
        removed_resources = []
        for resource in resources:
            if resource in self.get_hidden_resources():
                logger.info(f"Resource {resource} removed from Settlement {self.settlement_id}")
                removed_resources.append(resource)
                # Assuming there's a method to actually remove the resource
                self.remove_hidden_resource(resource)
        self._is_dirty = True
        return removed_resources

    def add_hidden_resource(self, resource_id: str):
        """
        Add a hidden resource to the settlement.
        
        Args:
            resource_id (str): The ID of the resource
        """
        hidden_resources = self.get_hidden_resources()
        hidden_resources.append(resource_id)
        self.set_property("hidden_resources", hidden_resources)
        self._mark_dirty()

    def set_basic_info(self, name: str, description: Optional[str] = None):
        """
        Set basic information about the settlement.
        
        Args:
            name (str): The settlement's name
            description (str, optional): A brief description of the settlement
        """
        self.settlement_name = name
        self.description = description or f"A settlement named {name}"
        self._mark_dirty()
        logger.info(f"Set basic info for Settlement {self.settlement_id}: name={name}")
    
    def get_required_services(self) -> List[str]:
        """
        Get a list of services required by the settlement.
        This can be used to determine what services need to be built or hired.
        
        Returns:
            List[str]: List of service IDs
        """
        return self.get_property("required_services", [])

    def set_location(self, location_id: Optional[str]):
        """
        Set the current location of the settlement.
        
        Args:
            location_id (str, optional): The ID of the location, or None
        """
        self.location_id = location_id
        self._mark_dirty()
        logger.info(f"Set location for Settlement {self.settlement_id} to {location_id}")
    
    def set_relation(self, entity_id: str, relation_type: str, value: Any = None):
        """
        Set a relationship to another entity.
        
        Args:
            entity_id (str): The ID of the related entity
            relation_type (str): The type of relationship
            value (Any, optional): Optional value/strength of relationship
        """
        if entity_id not in self.relations:
            self.relations[entity_id] = {}
        
        self.relations[entity_id][relation_type] = value
        self._mark_dirty()
        logger.info(f"Set relation {relation_type} to entity {entity_id} for Settlement {self.settlement_id}")
    
    def get_relation(self, entity_id: str, relation_type: str, default: Any = None) -> Any:
        """
        Get a relationship value.
        
        Args:
            entity_id (str): The ID of the related entity
            relation_type (str): The type of relationship
            default (Any, optional): Default value if relation doesn't exist
            
        Returns:
            Any: The relation value or default
        """
        return self.relations.get(entity_id, {}).get(relation_type, default)
    
    # For compatibility with older code
    def set_property(self, key: str, value: Any):
        """
        Set a custom property (use only for properties not covered by direct attributes).
        
        Args:
            key (str): The property name
            value (Any): The property value
        """
        self._properties[key] = value
        self._mark_dirty()
    
    def get_property(self, key: str, default: Any = None) -> Any:
        """
        Get a custom property (use only for properties not covered by direct attributes).
        
        Args:
            key (str): The property name
            default (Any, optional): Default value if property doesn't exist
            
        Returns:
            Any: The property value or default
        """
        return self._properties.get(key, default)
    
    ### Settlement-specific methods ###
    
    def set_is_repairable(self, is_repairable: bool):
        """
        Set whether the settlement is repairable.
        
        Args:
            is_repairable (bool): Whether the settlement is repairable
        """
        self.is_repairable = is_repairable
        self._mark_dirty()
        logger.info(f"Set is_repairable={is_repairable} for Settlement {self.settlement_id}")
    
    def set_is_damaged(self, is_damaged: bool):
        """
        Set whether the settlement is damaged.
        
        Args:
            is_damaged (bool): Whether the settlement is damaged
        """
        self.is_damaged = is_damaged
        self._mark_dirty()
        logger.info(f"Set is_damaged={is_damaged} for Settlement {self.settlement_id}")
    
    def set_has_started_building(self, has_started_building: bool):
        """
        Set whether the settlement has started building.
        
        Args:
            has_started_building (bool): Whether the settlement has started building
        """
        self.has_started_building = has_started_building
        self._mark_dirty()
        logger.info(f"Set has_started_building={has_started_building} for Settlement {self.settlement_id}")
    
    def set_is_under_repair(self, is_under_repair: bool):
        """
        Set whether the settlement is under repair.
        
        Args:
            is_under_repair (bool): Whether the settlement is under repair
        """
        self.is_under_repair = is_under_repair
        self._mark_dirty()
        logger.info(f"Set is_under_repair={is_under_repair} for Settlement {self.settlement_id}")
    
    def set_is_built(self, is_built: bool):
        """
        Set whether the settlement is built.
        
        Args:
            is_built (bool): Whether the settlement is built
        """
        self.is_built = is_built
        self._mark_dirty()
        logger.info(f"Set is_built={is_built} for Settlement {self.settlement_id}")
    
    def get_buildings(self):
        """Get all buildings in this settlement."""
        return self.get_property("buildings", [])

    def add_building(self, building_data):
        """Add a new building to the settlement."""
        buildings = self.get_buildings()
        buildings.append(building_data)
        self.set_property("buildings", buildings)
        self._mark_dirty()

    def get_resources(self):
        """Get all resources in this settlement."""
        return self.get_property("resources", {})

    def add_resource(self, resource_type, amount):
        """Add resources to the settlement."""
        resources = self.get_resources()
        resources[resource_type] = resources.get(resource_type, 0) + amount
        self.set_property("resources", resources)
        self._mark_dirty()

    def get_buildings_under_construction(self):
        """Get all buildings that are currently under construction."""
        return [b for b in self.get_buildings() if b["construction_status"] == 'in_progress']
    
    def get_operational_buildings(self):
        """Get all buildings that are operational."""
        return [b for b in self.get_buildings() if b["is_operational"]]
    
    def get_buildings_by_type(self, building_type):
        """Get all buildings of a specific type."""
        return [b for b in self.get_buildings() if b["type"] == building_type]
    
    def get_damaged_buildings(self):
        """Get all buildings that are damaged."""
        return [b for b in self.get_buildings() if b.get("health", 100) < 100]
    
    def update_building(self, building_id, updates):
        """
        Update a specific building with the provided updates.
        
        Args:
            building_id (str): ID of the building to update
            updates (dict): Dictionary of updates to apply
            
        Returns:
            bool: True if the building was found and updated
        """
        buildings = self.get_buildings()
        for i, building in enumerate(buildings):
            if building["building_id"] == building_id:
                buildings[i].update(updates)
                self.set_property("buildings", buildings)
                self._mark_dirty()
                return True
        return False
    
    def update_buildings(self, updated_buildings):
        """
        Update multiple buildings at once.
        
        Args:
            updated_buildings (list): List of building data to update
            
        Returns:
            int: Number of buildings updated
        """
        buildings = self.get_buildings()
        updated_count = 0
        
        # Create a map of existing buildings by ID
        buildings_map = {b["building_id"]: i for i, b in enumerate(buildings)}
        
        # Update each building
        for updated_building in updated_buildings:
            building_id = updated_building["building_id"]
            if building_id in buildings_map:
                index = buildings_map[building_id]
                buildings[index] = updated_building
                updated_count += 1
        
        # Save the updated buildings
        self.set_property("buildings", buildings)
        self._mark_dirty()
        
        return updated_count

    # State tracking methods
    def _mark_dirty(self):
        """Mark this entity as having unsaved changes."""
        self._is_dirty = True
    
    @property
    def is_dirty(self) -> bool:
        """
        Check if this entity has unsaved changes.
        
        Returns:
            bool: True if there are unsaved changes
        """
        return self._is_dirty
    
    def clean(self):
        """Mark this entity as having no unsaved changes."""
        self._is_dirty = False
    
    # Serialization methods
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert entity to dictionary for storage.
        
        Returns:
            Dict[str, Any]: Dictionary representation of this entity
        """
        # Convert any UUIDs to strings in properties
        import uuid
        
        def convert_uuids(obj):
            """Recursively convert UUIDs to strings in nested structures"""
            if isinstance(obj, uuid.UUID):
                return str(obj)
            elif isinstance(obj, dict):
                return {k: convert_uuids(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_uuids(item) for item in obj]
            else:
                return obj
        
        # Process all properties
        properties = convert_uuids(self._properties)
                
        # Also convert any UUIDs in relations
        relations = convert_uuids(self.relations)
        
        return {
            "id": self.settlement_id,
            "name": self.settlement_name,
            "description": self.description,
            "location_id": self.location_id,
            "relations": relations,
            "is_repairable": self.is_repairable,
            "is_damaged": self.is_damaged,
            "has_started_building": self.has_started_building,
            "is_under_repair": self.is_under_repair, 
            "is_built": self.is_built,
            "properties": properties
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Settlement':
        """
        Create entity from dictionary data.
        
        Args:
            data (Dict[str, Any]): Dictionary data to create entity from
            
        Returns:
            Settlement: New settlement instance
        """
        settlement = cls(settlement_id=data["id"])
        settlement.settlement_name = data.get("name")
        settlement.description = data.get("description")
        settlement.location_id = data.get("location_id")
        settlement.relations = data.get("relations", {})
        settlement.is_repairable = data.get("is_repairable", False)
        settlement.is_damaged = data.get("is_damaged", False)
        settlement.has_started_building = data.get("has_started_building", False)
        settlement.is_under_repair = data.get("is_under_repair", False)
        settlement.is_built = data.get("is_built", False)
        settlement._properties = data.get("properties", {})
        return settlement