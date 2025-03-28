from typing import List, Dict, Optional, Any, Tuple
import logging
import json
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

class World:
    """
    Represents the game world containing all geographic features, entities,
    and global state for the game simulation.
    
    The World entity is the top-level container that manages:
    1. Time progression and seasons
    2. Geographic features (settlements, areas, resources)
    3. Global state (weather, events, economy)
    4. Relationships between major entities
    
    It serves as the central coordinating entity for the entire game simulation.
    """
    
    def __init__(self, world_id: str):
        """
        Initialize a world with a unique ID.
        
        Args:
            world_id (str): Unique identifier for this world
        """
        # Basic identification
        self.world_id = world_id
        self.name = None
        self.description = None
        self.world_seed = None
        self.creation_date = datetime.now()
        self.last_updated = datetime.now()
        self.active = True
        self.is_premium = False
        self.max_players = 100
        self.theme_id = None  # References a theme setting
        
        # Time and seasons
        self.current_game_day = 1
        self.current_season = "spring"
        self.day_of_season = 1
        self.days_per_season = 30
        self.current_year = 1
        
        # World state
        self.properties = {}  # Flexible properties dictionary
        self.regions = {}  # Region-specific data
        self.settlements = {}  # settlement_id -> metadata
        self.areas = {}  # area_id -> metadata
        self.resource_sites = {}  # site_id -> metadata
        self.travel_routes = {}  # route_id -> metadata
        
        # World systems
        self.weather_system = {
            "current": {},  # region_id -> weather_state
            "forecast": []  # Future weather patterns
        }
        self.economy_state = {
            "global_inflation": 1.0,
            "resource_scarcity": {},  # resource_type -> scarcity_level
            "trade_volume": 0
        }
        self.faction_relations = {}  # faction_id -> {other_faction_id -> relation_value}
        
        # Events and encounters
        self.active_events = []  # List of active world events
        self.scheduled_events = []  # Future events
        
        # State tracking
        self._dirty = False
    
    def is_active(self) -> bool:
        """
        Check if this world is currently active.
        
        Returns:
            bool: True if the world is active
        """
        return self.active

    def set_basic_info(self, name: str, description: Optional[str] = None, theme_id: Optional[str] = None):
        """
        Set basic information about the world.
        
        Args:
            name (str): The world's name
            description (str, optional): A brief description of the world
            theme_id (str, optional): ID of the theme for this world
        """
        self.name = name
        self.description = description or f"A world named {name}"
        self.theme_id = theme_id
        self._dirty = True
        logger.info(f"Set basic info for world {self.world_id}: name={name}")
    
    def set_seed(self, seed: str):
        """
        Set the seed value for world generation.
        
        Args:
            seed (str): The seed value to use for consistent procedural generation
        """
        self.world_seed = seed
        self._dirty = True
        logger.info(f"Set world seed for world {self.world_id}: seed={seed}")
    
    def set_property(self, key: str, value: Any):
        """
        Set a property value in the flexible properties dictionary.
        
        Args:
            key (str): The property name
            value (Any): The property value
        """
        self.properties[key] = value
        self._dirty = True
        logger.info(f"Set property {key}={value} for world {self.world_id}")
    
    def get_property(self, key: str, default: Any = None) -> Any:
        """
        Get a property value from the properties dictionary.
        
        Args:
            key (str): The property name
            default (Any, optional): Default value if property doesn't exist
            
        Returns:
            Any: The property value or default
        """
        return self.properties.get(key, default)
    
    def advance_day(self) -> bool:
        """
        Advance the world by one game day, updating seasons if needed.
        
        Returns:
            bool: True if season changed, False otherwise
        """
        self.current_game_day += 1
        self.day_of_season += 1
        self.last_updated = datetime.now()
        self._dirty = True
        
        # Check for season change
        if self.day_of_season > self.days_per_season:
            self.change_season()
            return True
        return False
    
    def change_season(self):
        """
        Change to the next season and reset day counter.
        """
        seasons = ["spring", "summer", "autumn", "winter"]
        current_index = seasons.index(self.current_season)
        next_index = (current_index + 1) % 4
        
        self.current_season = seasons[next_index]
        self.day_of_season = 1
        
        # If we completed a full cycle, increment year
        if next_index == 0:
            self.current_year += 1
            
        self._dirty = True
        logger.info(f"Season changed in world {self.world_id}: now {self.current_season}, year {self.current_year}")
    
    def set_theme(self, theme_id: str):
        """
        Set the theme for this world.
        
        Args:
            theme_id (str): ID of the theme to apply
        """
        self.theme_id = theme_id
        self._dirty = True
        logger.info(f"Set theme for world {self.world_id}: theme_id={theme_id}")

    def register_settlement(self, settlement_id: str, name: str, location: Tuple[float, float], size: str = "hamlet"):
        """
        Register a settlement in the world.
        
        Args:
            settlement_id (str): Unique identifier for the settlement
            name (str): Name of the settlement
            location (Tuple[float, float]): (x, y) coordinates
            size (str, optional): Size category of the settlement
        """
        self.settlements[settlement_id] = {
            "name": name,
            "location": location,
            "size": size,
            "registered_at": self.current_game_day
        }
        self._dirty = True
        logger.info(f"Registered settlement {name} (ID: {settlement_id}) in world {self.world_id}")
    
    def unregister_settlement(self, settlement_id: str):
        """
        Remove a settlement from the world registry.
        
        Args:
            settlement_id (str): ID of the settlement to remove
        
        Returns:
            bool: True if settlement was found and removed, False otherwise
        """
        if settlement_id in self.settlements:
            settlement_name = self.settlements[settlement_id]["name"]
            del self.settlements[settlement_id]
            self._dirty = True
            logger.info(f"Unregistered settlement {settlement_name} (ID: {settlement_id}) from world {self.world_id}")
            return True
        return False
    
    def register_area(self, area_id: str, name: str, area_type: str, location: Tuple[float, float], radius: float):
        """
        Register a natural area in the world.
        
        Args:
            area_id (str): Unique identifier for the area
            name (str): Name of the area
            area_type (str): Type of area (forest, mountains, plains, etc.)
            location (Tuple[float, float]): (x, y) coordinates
            radius (float): Size/radius of the area
        """
        self.areas[area_id] = {
            "name": name,
            "type": area_type,
            "location": location,
            "radius": radius,
            "registered_at": self.current_game_day
        }
        self._dirty = True
        logger.info(f"Registered area {name} (ID: {area_id}) in world {self.world_id}")
    
    def register_resource_site(self, site_id: str, name: str, site_type: str, area_id: str):
        """
        Register a resource site in the world.
        
        Args:
            site_id (str): Unique identifier for the resource site
            name (str): Name of the resource site
            site_type (str): Type of resource site (mine, forest, etc.)
            area_id (str): ID of the area containing this resource site
        """
        if area_id not in self.areas:
            logger.warning(f"Attempted to register resource site in non-existent area: {area_id}")
            return False
            
        self.resource_sites[site_id] = {
            "name": name,
            "type": site_type,
            "area_id": area_id,
            "registered_at": self.current_game_day,
            "current_stage": "undiscovered"  # Initial stage
        }
        self._dirty = True
        logger.info(f"Registered resource site {name} (ID: {site_id}) in area {area_id}")
        return True
    
    def register_travel_route(self, route_id: str, start_id: str, end_id: str, path: List[str], distance: float):
        """
        Register a travel route between locations.
        
        Args:
            route_id (str): Unique identifier for the route
            start_id (str): ID of the starting location
            end_id (str): ID of the ending location
            path (List[str]): List of area IDs that form the path
            distance (float): Total travel distance
        """
        self.travel_routes[route_id] = {
            "start_id": start_id,
            "end_id": end_id,
            "path": path,
            "distance": distance,
            "registered_at": self.current_game_day,
            "condition": "good"  # Initial condition
        }
        self._dirty = True
        logger.info(f"Registered travel route (ID: {route_id}) from {start_id} to {end_id}")
    
    def update_weather(self, region_id: str, weather_state: Dict[str, Any]):
        """
        Update the weather in a specific region.
        
        Args:
            region_id (str): ID of the region to update
            weather_state (Dict[str, Any]): New weather state
        """
        self.weather_system["current"][region_id] = weather_state
        self._dirty = True
        logger.info(f"Updated weather in region {region_id} to {weather_state['condition']}")
    
    def generate_weather(self):
        """
        Generate weather patterns across all regions based on season and other factors.
        """
        # This would be a more complex implementation using the current season
        # and geographic factors to determine weather for each region
        for region_id in self.regions:
            # Simple random weather based on season
            if self.current_season == "winter":
                conditions = ["snow", "blizzard", "clear_cold", "overcast"]
            elif self.current_season == "spring":
                conditions = ["rain", "light_rain", "cloudy", "clear"]
            elif self.current_season == "summer":
                conditions = ["clear_hot", "thunderstorm", "partly_cloudy", "heatwave"]
            else:  # autumn
                conditions = ["rain", "windy", "fog", "clear_cool"]
                
            import random
            condition = random.choice(conditions)
            temperature = self._get_temperature_for_condition(condition)
            
            self.weather_system["current"][region_id] = {
                "condition": condition,
                "temperature": temperature,
                "wind_speed": random.randint(0, 30),
                "precipitation": random.randint(0, 100) if "rain" in condition or "snow" in condition else 0
            }
        
        self._dirty = True
        logger.info(f"Generated weather for all regions in world {self.world_id}")
    
    def _get_temperature_for_condition(self, condition: str) -> int:
        """
        Helper method to get a suitable temperature range for a weather condition.
        
        Args:
            condition (str): Weather condition
            
        Returns:
            int: Temperature value
        """
        import random
        
        # Very simplified temperature ranges by condition
        if "hot" in condition or "heatwave" in condition:
            return random.randint(30, 40)  # Hot
        elif "cold" in condition or "snow" in condition or "blizzard" in condition:
            return random.randint(-10, 5)  # Cold
        elif "cool" in condition:
            return random.randint(5, 15)  # Cool
        else:
            return random.randint(15, 25)  # Moderate
    
    def trigger_world_event(self, event_type: str, location: Tuple[float, float], 
                          radius: float, duration: int, name: str = None, 
                          description: str = None) -> str:
        """
        Create a new world event.
        
        Args:
            event_type (str): Type of event (natural_disaster, war, festival, etc.)
            location (Tuple[float, float]): (x, y) coordinates of event center
            radius (float): Area of effect
            duration (int): Duration in game days
            name (str, optional): Name of the event
            description (str, optional): Description of the event
            
        Returns:
            str: ID of the created event
        """
        event_id = str(uuid.uuid4())
        
        # Create event data
        event = {
            "event_id": event_id,
            "type": event_type,
            "location": location,
            "radius": radius,
            "start_day": self.current_game_day,
            "duration": duration,
            "end_day": self.current_game_day + duration,
            "name": name or f"{event_type.replace('_', ' ').title()} Event",
            "description": description or f"A {event_type} event",
            "effects": self._get_default_effects_for_event(event_type)
        }
        
        # Add to active events
        self.active_events.append(event)
        self._dirty = True
        
        logger.info(f"Triggered world event: {event['name']} (ID: {event_id})")
        return event_id
    
    def _get_default_effects_for_event(self, event_type: str) -> Dict[str, Any]:
        """
        Get default effects for different event types.
        
        Args:
            event_type (str): Type of event
            
        Returns:
            Dict[str, Any]: Default effects for this event type
        """
        # Different event types would have different default effects
        if event_type == "natural_disaster":
            return {
                "area_damage": 0.5,  # 50% damage to affected areas
                "travel_difficulty": 2.0,  # Double travel time
                "resource_scarcity": 1.5  # 50% increase in resource scarcity
            }
        elif event_type == "festival":
            return {
                "trade_bonus": 0.2,  # 20% bonus to trade
                "settlement_happiness": 0.3,  # 30% boost to happiness
                "visitor_increase": 0.5  # 50% more visitors
            }
        elif event_type == "war":
            return {
                "danger_level_increase": 0.5,  # 50% increase in danger
                "trade_penalty": -0.3,  # 30% penalty to trade
                "resource_consumption": 1.5  # 50% increase in resource consumption
            }
        else:
            # Default generic effects
            return {
                "generic_effect": 0.1
            }
    
    def update_events(self):
        """
        Update all active world events, removing expired ones.
        
        Returns:
            List[Dict[str, Any]]: List of events that ended this update
        """
        ended_events = []
        active_events = []
        
        for event in self.active_events:
            # Check if event has expired
            if self.current_game_day >= event["end_day"]:
                ended_events.append(event)
                logger.info(f"World event ended: {event['name']} (ID: {event['event_id']})")
            else:
                active_events.append(event)
        
        # Update active events list
        self.active_events = active_events
        
        if ended_events:
            self._dirty = True
            
        return ended_events
    
    def set_faction_relation(self, faction_id: str, other_faction_id: str, value: float):
        """
        Set the relation value between two factions.
        
        Args:
            faction_id (str): ID of the first faction
            other_faction_id (str): ID of the second faction
            value (float): Relation value (-1.0 to 1.0, where -1 is hostile, 0 is neutral, 1 is allied)
        """
        if faction_id not in self.faction_relations:
            self.faction_relations[faction_id] = {}
            
        self.faction_relations[faction_id][other_faction_id] = max(-1.0, min(1.0, value))  # Clamp to valid range
        
        # Mirror the relation (both factions have same relation to each other)
        if other_faction_id not in self.faction_relations:
            self.faction_relations[other_faction_id] = {}
            
        self.faction_relations[other_faction_id][faction_id] = max(-1.0, min(1.0, value))
        
        self._dirty = True
        logger.info(f"Set faction relation between {faction_id} and {other_faction_id} to {value}")
    
    def get_faction_relation(self, faction_id: str, other_faction_id: str) -> float:
        """
        Get the relation value between two factions.
        
        Args:
            faction_id (str): ID of the first faction
            other_faction_id (str): ID of the second faction
            
        Returns:
            float: Relation value (-1.0 to 1.0) or 0.0 if not set
        """
        return self.faction_relations.get(faction_id, {}).get(other_faction_id, 0.0)
    
    def update_economy(self):
        """
        Update the global economy state based on various factors.
        """
        # This would be a complex implementation in a real system
        # Here we just update a few sample values
        
        # Adjust inflation based on trade volume
        trade_factor = min(1.0, self.economy_state["trade_volume"] / 1000)
        self.economy_state["global_inflation"] = max(0.8, min(1.5, self.economy_state["global_inflation"] * (1 + 0.01 * trade_factor)))
        
        # Reset trade volume for next cycle
        self.economy_state["trade_volume"] = 0
        
        self._dirty = True
        logger.info(f"Updated economy state for world {self.world_id}")
    
    def record_trade(self, value: float):
        """
        Record a trade transaction to track economic activity.
        
        Args:
            value (float): Value of the trade in gold or other currency
        """
        self.economy_state["trade_volume"] += value
        self._dirty = True
    
    def calculate_resource_scarcity(self):
        """
        Calculate resource scarcity levels across the world.
        """
        # This would use resource site data, production rates, and consumption
        # to determine global scarcity levels for different resources
        
        # Example implementation
        resources = ["wood", "stone", "iron", "food", "luxury_goods"]
        import random
        
        for resource in resources:
            # Simplified random scarcity based on season
            if resource == "food" and self.current_season == "winter":
                base_scarcity = random.uniform(1.2, 1.5)  # Food more scarce in winter
            elif resource == "wood" and self.current_season == "summer":
                base_scarcity = random.uniform(0.8, 0.9)  # Wood less scarce in summer
            else:
                base_scarcity = random.uniform(0.9, 1.1)
                
            self.economy_state["resource_scarcity"][resource] = base_scarcity
            
        self._dirty = True
        logger.info(f"Calculated resource scarcity for world {self.world_id}")
    
    # State tracking methods
    def is_dirty(self) -> bool:
        """
        Check if this world has unsaved changes.
        
        Returns:
            bool: True if there are unsaved changes
        """
        return self._dirty
    
    def mark_clean(self):
        """Mark this world as having no unsaved changes."""
        self._dirty = False
    
    # Serialization methods
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert world to dictionary for storage.
        
        Returns:
            Dict[str, Any]: Dictionary representation of this world
        """
        return {
            "world_id": self.world_id,
            "name": self.name,
            "description": self.description,
            "world_seed": self.world_seed,
            "creation_date": self.creation_date.isoformat() if self.creation_date else None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "active": self.active,
            "is_premium": self.is_premium,
            "max_players": self.max_players,
            "theme_id": self.theme_id,
            
            # Time and seasons
            "current_game_day": self.current_game_day,
            "current_season": self.current_season,
            "day_of_season": self.day_of_season,
            "days_per_season": self.days_per_season,
            "current_year": self.current_year,
            
            # World state
            "properties": self.properties,
            "regions": self.regions,
            "settlements": self.settlements,
            "areas": self.areas,
            "resource_sites": self.resource_sites,
            "travel_routes": self.travel_routes,
            
            # World systems
            "weather_system": self.weather_system,
            "economy_state": self.economy_state,
            "faction_relations": self.faction_relations,
            
            # Events
            "active_events": self.active_events,
            "scheduled_events": self.scheduled_events
        }
    
    @classmethod #
    def from_dict(cls, data: Dict[str, Any]) -> 'World':
        """
        Create world from dictionary data.
        
        Args:
            data (Dict[str, Any]): Dictionary data to create world from
            
        Returns:
            World: New world instance
        """
        world = cls(world_id=data["world_id"])
        
        # Basic information
        world.name = data.get("name")
        world.description = data.get("description")
        world.world_seed = data.get("world_seed")
        
        # Parse dates if they exist
        if data.get("creation_date"):
            world.creation_date = datetime.fromisoformat(data["creation_date"])
        if data.get("last_updated"):
            world.last_updated = datetime.fromisoformat(data["last_updated"])
            
        world.active = data.get("active", True)
        world.is_premium = data.get("is_premium", False)
        world.max_players = data.get("max_players", 100)
        world.theme_id = data.get("theme_id")
        
        # Time and seasons
        world.current_game_day = data.get("current_game_day", 1)
        world.current_season = data.get("current_season", "spring")
        world.day_of_season = data.get("day_of_season", 1)
        world.days_per_season = data.get("days_per_season", 30)
        world.current_year = data.get("current_year", 1)
        
        # World state
        world.properties = data.get("properties", {})
        world.regions = data.get("regions", {})
        world.settlements = data.get("settlements", {})
        world.areas = data.get("areas", {})
        world.resource_sites = data.get("resource_sites", {})
        world.travel_routes = data.get("travel_routes", {})
        
        # World systems
        world.weather_system = data.get("weather_system", {"current": {}, "forecast": []})
        world.economy_state = data.get("economy_state", {
            "global_inflation": 1.0,
            "resource_scarcity": {},
            "trade_volume": 0
        })
        world.faction_relations = data.get("faction_relations", {})
        
        # Events
        world.active_events = data.get("active_events", [])
        world.scheduled_events = data.get("scheduled_events", [])
        
        return world