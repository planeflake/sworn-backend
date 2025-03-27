import logging
import json
import uuid
from typing import List, Dict, Set, Optional, Any, Callable
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

# Define all resource classifications as enums
class ResourceType(Enum):
    """Base classification of the resource"""
    MINERAL = "mineral"
    METAL = "metal"
    GEM = "gem"
    PLANT = "plant"
    HERB = "herb"
    ANIMAL = "animal"
    FOOD = "food"
    POTION = "potion"
    ARTIFACT = "artifact"
    TOOL = "tool"
    WEAPON = "weapon"
    ARMOR = "armor"
    CLOTHING = "clothing"
    BOOK = "book"
    CURRENCY = "currency"
    CONTAINER = "container"

class ResourceRarity(Enum):
    """How rare/common the resource is"""
    COMMON = 0
    UNCOMMON = 1
    RARE = 2
    EPIC = 3
    LEGENDARY = 4
    MYTHIC = 5

class ResourceQuality(Enum):
    """The condition/quality of the resource"""
    POOR = 0
    COMMON = 1
    GOOD = 2
    EXCELLENT = 3
    MASTERWORK = 4

class MaterialState(Enum):
    """The processing state of materials"""
    RAW = "raw"
    PROCESSED = "processed" 
    REFINED = "refined"
    CRAFTED = "crafted"

class ElementalAffinity(Enum):
    """Elemental alignment if applicable"""
    NONE = "none"
    FIRE = "fire"
    WATER = "water"
    EARTH = "earth"
    AIR = "air"
    LIGHT = "light"
    DARK = "dark"
    ARCANE = "arcane"

class UsageCategory(Enum):
    """Primary usage of the resource"""
    CRAFTING = "crafting"
    CONSUMABLE = "consumable"
    EQUIPMENT = "equipment"
    TRADE = "trade"
    QUEST = "quest"
    BUILDING = "building"
    DECORATION = "decoration"

class DynamicTag(Enum):
    """Tags that might change during gameplay"""
    QUEST_ITEM = "quest_item"
    CURSED = "cursed"
    BLESSED = "blessed"
    STOLEN = "stolen"
    MARKED = "marked"
    HIDDEN = "hidden"
    NEW = "new"
    FAVORITE = "favorite"
    EQUIPPED = "equipped"
    LOCKED = "locked"
    HIGH_DEMAND = "high_demand"
    SURPLUS = "surplus"
    LOCAL_SPECIALTY = "local_specialty"
    FORBIDDEN = "forbidden"
    SEASONAL = "seasonal"
    BROKEN = "broken"

class ResourceEventType(Enum):
    """Types of events that can happen to a resource"""
    CREATED = "created"
    DISCOVERED = "discovered"
    ACQUIRED = "acquired"
    MODIFIED = "modified"
    CONSUMED = "consumed"
    TRADED = "traded"
    QUALITY_CHANGED = "quality_changed"
    TAG_ADDED = "tag_added"
    TAG_REMOVED = "tag_removed"
    MOVED = "moved"

class ResourceEvent:
    """Records an event that happened to a resource"""
    def __init__(self, event_type: ResourceEventType, details: Dict[str, Any] = None):
        self.event_type = event_type
        self.timestamp = datetime.now().isoformat()
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the event to a dictionary"""
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "details": self.details
        }

class Resource:
    """
    Resource entity representing items, materials, and commodities in the game world.
    
    Resources have:
    1. A unique identifier
    2. Classification properties (type, rarity, etc.)
    3. Physical properties (weight, stackability)
    4. Economic properties (value)
    5. Dynamic tags and states
    6. Event history
    """
    
    def __init__(self, name: str, description: str = None, resource_id: str = None):
        """
        Initialize a resource with a unique ID.
        
        Args:
            name: The resource's name
            description: A brief description of the resource
            resource_id: Optional unique identifier (will generate if None)
        """
        # Core identity
        self.id = resource_id or str(uuid.uuid4())
        self.name = name
        self.description = description or f"A resource named {name}"
        
        # Classification properties
        self.resource_type = None
        self.rarity = ResourceRarity.COMMON
        self.quality = ResourceQuality.COMMON
        self.material_state = None
        self.elemental_affinity = ElementalAffinity.NONE
        self.usage_category = None
        
        # Physical properties 
        self.unit_weight = 0.0
        self.unit_volume = 0.0
        self.stackable = True
        self.max_stack_size = 99
        
        # Economic properties
        self.base_value = 0.0
        
        # Durability/Perishability
        self.max_durability = None
        self.current_durability = None
        self.perishable = False
        self.decay_rate = 0.0
        
        # Status tracking
        self.location_id = None
        self.container_id = None
        self.owner_id = None
        
        # Dynamic state
        self.dynamic_tags = set()
        
        # Custom properties
        self._properties = {}
        
        # History tracking
        self.created_at = datetime.now().isoformat()
        self.last_modified = self.created_at
        self.history = []
        
        # Event callbacks
        self._callbacks = {}
        
        # Record creation event
        self._record_event(ResourceEventType.CREATED)
        
        # State tracking
        self._is_dirty = False
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"Resource(id={self.id}, name='{self.name}', type={self.resource_type.value if self.resource_type else 'None'})"
    
    def __str__(self) -> str:
        """String representation for display."""
        if self.quality and self.resource_type:
            return f"{self.name} ({self.quality.name.lower()} {self.resource_type.value})"
        return self.name
    
    # ---- Tag Management ----
    def add_tag(self, tag: DynamicTag):
        """
        Add a dynamic tag to this resource.
        
        Args:
            tag: The tag to add
        """
        if tag not in self.dynamic_tags:
            self.dynamic_tags.add(tag)
            self._record_event(ResourceEventType.TAG_ADDED, {"tag": tag.value})
            self._mark_dirty()
            logger.info(f"Added tag {tag.value} to resource {self.id} ({self.name})")
    
    def remove_tag(self, tag: DynamicTag):
        """
        Remove a dynamic tag from this resource.
        
        Args:
            tag: The tag to remove
        """
        if tag in self.dynamic_tags:
            self.dynamic_tags.remove(tag)
            self._record_event(ResourceEventType.TAG_REMOVED, {"tag": tag.value})
            self._mark_dirty()
            logger.info(f"Removed tag {tag.value} from resource {self.id} ({self.name})")
    
    def has_tag(self, tag: DynamicTag) -> bool:
        """
        Check if this resource has a specific tag.
        
        Args:
            tag: The tag to check for
            
        Returns:
            bool: True if the resource has the tag
        """
        return tag in self.dynamic_tags
    
    # ---- Quality Management ----
    def set_quality(self, quality: ResourceQuality):
        """
        Set the quality of this resource.
        
        Args:
            quality: The new quality
        """
        old_quality = self.quality
        self.quality = quality
        self._record_event(ResourceEventType.QUALITY_CHANGED, {
            "old_quality": old_quality.value,
            "new_quality": quality.value
        })
        self._mark_dirty()
        logger.info(f"Changed quality of {self.id} ({self.name}) from {old_quality.name} to {quality.name}")
    
    def improve_quality(self, steps: int = 1):
        """
        Improve the quality by a number of steps.
        
        Args:
            steps: Number of quality levels to improve
        """
        current_value = self.quality.value
        max_value = max(q.value for q in ResourceQuality)
        new_value = min(current_value + steps, max_value)
        
        if new_value != current_value:
            self.set_quality(ResourceQuality(new_value))
    
    def degrade_quality(self, steps: int = 1):
        """
        Degrade the quality by a number of steps.
        
        Args:
            steps: Number of quality levels to degrade
        """
        current_value = self.quality.value
        new_value = max(current_value - steps, 0)
        
        if new_value != current_value:
            self.set_quality(ResourceQuality(new_value))
    
    # ---- Durability Management ----
    def damage(self, amount: float):
        """
        Damage the item by reducing its durability.
        
        Args:
            amount: Amount of durability to reduce
        """
        if self.current_durability is None:
            return
        
        old_durability = self.current_durability
        self.current_durability = max(0, self.current_durability - amount)
        self._mark_dirty()
        logger.info(f"Reduced durability of {self.id} ({self.name}) from {old_durability} to {self.current_durability}")
        
        # Check if item is broken
        if self.current_durability == 0:
            self.add_tag(DynamicTag.BROKEN)
    
    def repair(self, amount: float):
        """
        Repair the item by increasing its durability.
        
        Args:
            amount: Amount of durability to restore
        """
        if self.current_durability is None or self.max_durability is None:
            return
        
        old_durability = self.current_durability
        self.current_durability = min(self.max_durability, self.current_durability + amount)
        self._mark_dirty()
        logger.info(f"Repaired {self.id} ({self.name}) from {old_durability} to {self.current_durability}")
        
        # Check if item is no longer broken
        if old_durability == 0 and self.current_durability > 0:
            if DynamicTag.BROKEN in self.dynamic_tags:
                self.remove_tag(DynamicTag.BROKEN)
    
    def decay(self, days: float = 1.0):
        """
        Apply decay over time if perishable.
        
        Args:
            days: Number of days to apply decay for
        """
        if not self.perishable or self.decay_rate <= 0:
            return
        
        self.damage(self.decay_rate * days)
    
    # ---- Value Calculation ----
    def calculate_value(self, market_modifier: float = 1.0) -> float:
        """
        Calculate the current value based on quality, condition, and market.
        
        Args:
            market_modifier: Multiplier based on local market conditions
            
        Returns:
            float: The current value of the resource
        """
        # Start with base value
        value = self.base_value
        
        # Apply quality multiplier
        quality_multipliers = {
            ResourceQuality.POOR: 0.5,
            ResourceQuality.COMMON: 1.0,
            ResourceQuality.GOOD: 1.5,
            ResourceQuality.EXCELLENT: 2.0,
            ResourceQuality.MASTERWORK: 3.0
        }
        value *= quality_multipliers.get(self.quality, 1.0)
        
        # Apply rarity multiplier
        rarity_multipliers = {
            ResourceRarity.COMMON: 1.0,
            ResourceRarity.UNCOMMON: 2.0,
            ResourceRarity.RARE: 5.0,
            ResourceRarity.EPIC: 10.0,
            ResourceRarity.LEGENDARY: 25.0,
            ResourceRarity.MYTHIC: 100.0
        }
        value *= rarity_multipliers.get(self.rarity, 1.0)
        
        # Apply durability modifier if applicable
        if self.current_durability is not None and self.max_durability > 0:
            durability_ratio = self.current_durability / self.max_durability
            value *= max(0.1, durability_ratio)  # Item retains at least 10% value
        
        # Apply market modifier
        value *= market_modifier
        
        # Apply tag-based modifiers
        if DynamicTag.HIGH_DEMAND in self.dynamic_tags:
            value *= 1.5
        if DynamicTag.SURPLUS in self.dynamic_tags:
            value *= 0.7
        if DynamicTag.CURSED in self.dynamic_tags:
            value *= 0.5
        if DynamicTag.BLESSED in self.dynamic_tags:
            value *= 1.3
        
        return value
    
    # ---- Location and Ownership ----
    def move_to(self, location_id: str, container_id: str = None):
        """
        Move this resource to a new location or container.
        
        Args:
            location_id: The ID of the location to move to
            container_id: Optional container ID within the location
        """
        old_location = self.location_id
        old_container = self.container_id
        
        self.location_id = location_id
        self.container_id = container_id
        
        self._record_event(ResourceEventType.MOVED, {
            "old_location": old_location,
            "new_location": location_id,
            "old_container": old_container,
            "new_container": container_id
        })
        
        self._mark_dirty()
        logger.info(f"Moved resource {self.id} ({self.name}) to location {location_id}, container {container_id}")

    def set_location(self, location_id: Optional[str]):
        """
        Set the current location of the resource.
        
        Args:
            location_id: The ID of the location, or None
        """
        self.move_to(location_id, self.container_id)
    
    def set_owner(self, owner_id: str):
        """
        Set the owner of this resource.
        
        Args:
            owner_id: The ID of the new owner
        """
        old_owner = self.owner_id
        self.owner_id = owner_id
        
        self._record_event(ResourceEventType.MODIFIED, {
            "property": "owner",
            "old_value": old_owner,
            "new_value": owner_id
        })
        
        self._mark_dirty()
        logger.info(f"Changed owner of resource {self.id} ({self.name}) from {old_owner} to {owner_id}")
    
    # ---- Property Management ----
    def set_property(self, key: str, value: Any):
        """
        Set a custom property on this resource.
        
        Args:
            key: The property name
            value: The property value
        """
        old_value = self._properties.get(key)
        self._properties[key] = value
        
        self._record_event(ResourceEventType.MODIFIED, {
            "property": key,
            "old_value": old_value,
            "new_value": value
        })
        
        self._mark_dirty()
    
    def get_property(self, key: str, default: Any = None) -> Any:
        """
        Get a custom property from this resource.
        
        Args:
            key: The property name
            default: Default value if property doesn't exist
            
        Returns:
            Any: The property value or default
        """
        return self._properties.get(key, default)
    
    # ---- Event Management ----
    def register_callback(self, event_type: ResourceEventType, callback: Callable):
        """
        Register a callback for a specific event type.
        
        Args:
            event_type: The event type to listen for
            callback: The function to call when the event occurs
        """
        if event_type not in self._callbacks:
            self._callbacks[event_type] = []
        
        self._callbacks[event_type].append(callback)
    
    def _record_event(self, event_type: ResourceEventType, details: Dict[str, Any] = None):
        """
        Record an event in this resource's history and trigger callbacks.
        
        Args:
            event_type: The type of event that occurred
            details: Additional details about the event
        """
        event = ResourceEvent(event_type, details or {})
        self.history.append(event)
        
        # Trigger callbacks
        if event_type in self._callbacks:
            for callback in self._callbacks[event_type]:
                try:
                    callback(self, event)
                except Exception as e:
                    logger.error(f"Error in resource event callback: {e}")
    
    # ---- State Management ----
    def _mark_dirty(self):
        """Mark this resource as modified and update timestamp."""
        self._is_dirty = True
        self.last_modified = datetime.now().isoformat()
    
    @property
    def is_dirty(self) -> bool:
        """
        Check if this resource has unsaved changes.
        
        Returns:
            bool: True if there are unsaved changes
        """
        return self._is_dirty
    
    def clean(self):
        """Mark this resource as having no unsaved changes."""
        self._is_dirty = False
    
    def set_basic_info(self, name: str, description: Optional[str] = None):
        """
        Set basic information about the resource.
        
        Args:
            name: The resource's name
            description: A brief description of the resource
        """
        self.name = name
        self.description = description or f"A resource named {name}"
        self._mark_dirty()
        logger.info(f"Set basic info for Resource {self.id}: name={name}")
    
    # ---- Serialization ----
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert resource to dictionary for storage.
        
        Returns:
            Dict[str, Any]: Dictionary representation of this resource
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "resource_type": self.resource_type.value if self.resource_type else None,
            "rarity": self.rarity.value if self.rarity else None,
            "quality": self.quality.value if self.quality else None,
            "material_state": self.material_state.value if self.material_state else None,
            "elemental_affinity": self.elemental_affinity.value if self.elemental_affinity else None,
            "usage_category": self.usage_category.value if self.usage_category else None,
            "unit_weight": self.unit_weight,
            "unit_volume": self.unit_volume,
            "stackable": self.stackable,
            "max_stack_size": self.max_stack_size,
            "base_value": self.base_value,
            "max_durability": self.max_durability,
            "current_durability": self.current_durability,
            "perishable": self.perishable,
            "decay_rate": self.decay_rate,
            "location_id": self.location_id,
            "container_id": self.container_id,
            "owner_id": self.owner_id,
            "dynamic_tags": [tag.value for tag in self.dynamic_tags],
            "properties": self._properties,
            "created_at": self.created_at,
            "last_modified": self.last_modified,
            "history": [event.to_dict() for event in self.history]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Resource':
        """
        Create resource from dictionary data.
        
        Args:
            data: Dictionary data to create resource from
            
        Returns:
            Resource: New resource instance
        """
        # Create a basic instance
        resource = cls(
            name=data.get("name", "Unknown Resource"),
            description=data.get("description"),
            resource_id=data.get("id")
        )
        
        # Set classification properties (with safety checks)
        if data.get("resource_type"):
            resource.resource_type = next(
                (t for t in ResourceType if t.value == data["resource_type"]), 
                None
            )
        
        if data.get("rarity") is not None:
            resource.rarity = next(
                (r for r in ResourceRarity if r.value == data["rarity"]), 
                ResourceRarity.COMMON
            )
        
        if data.get("quality") is not None:
            resource.quality = next(
                (q for q in ResourceQuality if q.value == data["quality"]), 
                ResourceQuality.COMMON
            )
        
        if data.get("material_state"):
            resource.material_state = next(
                (m for m in MaterialState if m.value == data["material_state"]), 
                None
            )
        
        if data.get("elemental_affinity"):
            resource.elemental_affinity = next(
                (e for e in ElementalAffinity if e.value == data["elemental_affinity"]), 
                ElementalAffinity.NONE
            )
        
        if data.get("usage_category"):
            resource.usage_category = next(
                (u for u in UsageCategory if u.value == data["usage_category"]), 
                None
            )
        
        # Set physical and economic properties
        resource.unit_weight = data.get("unit_weight", 0.0)
        resource.unit_volume = data.get("unit_volume", 0.0)
        resource.stackable = data.get("stackable", True)
        resource.max_stack_size = data.get("max_stack_size", 99)
        resource.base_value = data.get("base_value", 0.0)
        
        # Set durability/perishability
        resource.max_durability = data.get("max_durability")
        resource.current_durability = data.get("current_durability")
        resource.perishable = data.get("perishable", False)
        resource.decay_rate = data.get("decay_rate", 0.0)
        
        # Set location and ownership
        resource.location_id = data.get("location_id")
        resource.container_id = data.get("container_id")
        resource.owner_id = data.get("owner_id")
        
        # Set dynamic tags
        resource.dynamic_tags = {
            next((t for t in DynamicTag if t.value == tag_value), None)
            for tag_value in data.get("dynamic_tags", [])
            if next((t for t in DynamicTag if t.value == tag_value), None) is not None
        }
        
        # Set custom properties
        resource._properties = data.get("properties", {})
        
        # Set timestamps
        resource.created_at = data.get("created_at", datetime.now().isoformat())
        resource.last_modified = data.get("last_modified", resource.created_at)
        
        # Set history
        if "history" in data:
            resource.history = [
                ResourceEvent(
                    event_type=next((t for t in ResourceEventType if t.value == e["event_type"]), 
                                ResourceEventType.MODIFIED),
                    details=e.get("details", {})
                )
                for e in data["history"]
            ]
        
        # Mark as clean since we just loaded it
        resource.clean()
        
        return resource

# Example factory function
def create_iron_ore() -> Resource:
    """Create a standard iron ore resource."""
    iron_ore = Resource("Iron Ore", "A chunk of raw iron ore, useful for smelting.")
    iron_ore.resource_type = ResourceType.MINERAL
    iron_ore.rarity = ResourceRarity.COMMON
    iron_ore.quality = ResourceQuality.COMMON
    iron_ore.material_state = MaterialState.RAW
    iron_ore.elemental_affinity = ElementalAffinity.EARTH
    iron_ore.usage_category = UsageCategory.CRAFTING
    iron_ore.unit_weight = 2.5
    iron_ore.unit_volume = 1.0
    iron_ore.base_value = 5.0
    
    return iron_ore