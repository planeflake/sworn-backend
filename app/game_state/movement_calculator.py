import logging
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
import random
from sqlalchemy.orm import Session

from models.seasons import (
    Biome, Weather, TransportMethod, RoadType, Area, Season,
    MovementFactors, MovementParams, MovementResult
)

from models.biomes import Biomes

logger = logging.getLogger(__name__)

class MovementCalculator:
    """Utility class to calculate travel times and movement costs."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def calculate_movement(self, params: MovementParams) -> MovementResult:
        """
        Calculate the full movement result for a journey.
        
        Args:
            params: Movement parameters including trader, path, transport, etc.
            
        Returns:
            Complete movement calculation with times, costs, and risks
        """
        # Load all the necessary data
        trader = self._get_trader(params.trader_id)
        transport = self._get_transport(params.transport_id)
        
        # Get current world state (season, time of day)
        world_id = trader.world_id
        world = self._get_world(world_id)
        current_season = self._get_season(world.current_season)
        
        # Prepare the result
        result = MovementResult(
            total_distance=0.0,
            total_travel_time=0.0,
            arrival_time=params.start_time,
            area_times={},
            encounter_chances={}
        )
        
        # Process each area in the path
        current_time = params.start_time
        previous_area_id = None
        
        for area_id in params.path:
            area = self._get_area(area_id)
            biome = self._get_biome(area.biome_id)
            
            # Get road type between previous area and this one (if any)
            road_type = None
            if previous_area_id:
                road_type = self._get_road_between(previous_area_id, area_id)
            
            # Get current weather for this area
            weather = self._get_current_weather(world_id, area_id)
            
            # Calculate distance for this segment
            distance = self._calculate_distance(previous_area_id, area_id)
            result.total_distance += distance
            
            # Calculate movement factors
            factors = self._calculate_movement_factors(
                transport=transport,
                biome=biome,
                road_type=road_type,
                weather=weather,
                season=current_season,
                trader=trader
            )
            
            # Calculate time to traverse this area
            travel_time = self._calculate_travel_time(distance, factors)
            result.area_times[area_id] = travel_time
            result.total_travel_time += travel_time
            
            # Update current time
            current_time += timedelta(hours=travel_time)
            
            # Calculate encounter chance
            encounter_chance = self._calculate_encounter_chance(
                area=area,
                transport=transport,
                weather=weather,
                trader=trader
            )
            result.encounter_chances[area_id] = encounter_chance
            
            # Calculate costs for this segment
            segment_costs = self._calculate_segment_costs(
                area=area,
                road_type=road_type,
                transport=transport,
                travel_time=travel_time
            )
            
            # Add costs to the total
            result.gold_costs += segment_costs.get('gold', 0)
            for resource, amount in segment_costs.get('resources', {}).items():
                if resource in result.resource_costs:
                    result.resource_costs[resource] += amount
                else:
                    result.resource_costs[resource] = amount
            
            # Calculate risks for this segment
            segment_risks = self._calculate_segment_risks(
                area=area,
                transport=transport,
                weather=weather,
                travel_time=travel_time
            )
            result.risks.extend(segment_risks)
            
            # Update previous area
            previous_area_id = area_id
        
        # Set final arrival time
        result.arrival_time = current_time
        
        return result
    
    def _get_trader(self, trader_id: str) -> Any:
        """Get trader data from database."""
        # Implement based on your ORM model
        from models.core import Traders
        return self.db.query(Traders).filter(Traders.trader_id == trader_id).first()
    
    def _get_transport(self, transport_id: int) -> TransportMethod:
        """Get transport data from database."""
        # Implement based on your ORM model
        from models.core import TransportMethods
        transport_data = self.db.query(TransportMethods).filter(TransportMethods.transport_id == transport_id).first()
        
        # Convert to Pydantic model
        return TransportMethod.from_orm(transport_data)
    
    def _get_world(self, world_id: str) -> Any:
        """Get world data from database."""
        # Implement based on your ORM model
        from models.core import Worlds
        return self.db.query(Worlds).filter(Worlds.world_id == world_id).first()
    
    def _get_season(self, season_name: str) -> Season:
        """Get season data from database."""
        # Implement based on your ORM model
        from models.seasons import Seasons
        season_data = self.db.query(Seasons).filter(Seasons.name == season_name).first()
        
        # Convert to Pydantic model
        return Season.from_orm(season_data)
    
    def _get_area(self, area_id: str) -> Area:
        """Get area data from database."""
        # Implement based on your ORM model
        from models.core import Areas
        area_data = self.db.query(Areas).filter(Areas.area_id == area_id).first()
        
        # Convert to Pydantic model
        return Area.from_orm(area_data)
    
    def _get_biome(self, biome_id: int) -> Biome:
        """Get biome data from database."""
        # Implement based on your ORM model
        from models.biomes import Biomes
        biome_data = self.db.query(Biomes).filter(Biomes.biome_id == biome_id).first()
        
        # Convert to Pydantic model
        return Biomes.has_attribute(biome_data)
    
    def _get_road_between(self, area1_id: str, area2_id: str) -> Optional[RoadType]:
        """Get road type between two areas if one exists."""
        # Implement based on your ORM model
        from models.transport import AreaRoad, RoadType
        
        road_data = self.db.query(AreaRoad).filter(
            ((AreaRoad.area_id == area1_id) & (AreaRoad.connecting_area_id == area2_id)) |
            ((AreaRoad.area_id == area2_id) & (AreaRoad.connecting_area_id == area1_id))
        ).first()
        
        if not road_data:
            return None
        
        road_type_data = self.db.query(RoadType).filter(RoadType.road_type_id == road_data.road_type_id).first()
        
        # Convert to Pydantic model
        return RoadType.has_attribute(road_type_data) if road_type_data else None
    
    def _get_current_weather(self, world_id: str, area_id: str) -> Optional[Weather]:
        """Get current weather for an area."""
        # Implement based on your ORM model
        from models.travel import WorldWeatherState, WeatherTypes
        
        # Get active weather for this world and area
        weather_state = self.db.query(WorldWeatherState).filter(
            (WorldWeatherState.world_id == world_id) &
            (WorldWeatherState.is_active == True) &
            (
                (WorldWeatherState.affected_biomes.is_(None)) |  # Affects all biomes
                self._check_area_in_affected_biomes(area_id)  # Or specifically affects this area's biome
            )
        ).first()
        
        if not weather_state:
            # No active weather, use "clear" as default
            weather_data = self.db.query(WeatherTypes).filter(WeatherTypes.name == 'clear').first()
        else:
            weather_data = self.db.query(WeatherTypes).filter(WeatherTypes.weather_id == weather_state.weather_id).first()
        
        # Convert to Pydantic model
        return Weather.from_orm(weather_data) if weather_data else None
    
    def _check_area_in_affected_biomes(self, area_id: str) -> bool:
        """Check if an area's biome is in the affected biomes list."""
        # This would be a custom SQL query or ORM expression
        # Implementation depends on your database structure
        return True  # Placeholder
    
    def _calculate_distance(self, area1_id: Optional[str], area2_id: str) -> float:
        """Calculate the distance between two areas."""
        if not area1_id:
            return 0.0  # First area in path
        
        # Get area coordinates
        area1 = self._get_area(area1_id)
        area2 = self._get_area(area2_id)
        
        # Calculate Euclidean distance
        import math
        dx = area2.location_x - area1.location_x
        dy = area2.location_y - area1.location_y
        distance = math.sqrt(dx*dx + dy*dy)
        
        return distance
    
    def _calculate_movement_factors(
        self,
        transport: TransportMethod,
        biome: Biome,
        road_type: Optional[RoadType],
        weather: Optional[Weather],
        season: Season,
        trader: Any
    ) -> MovementFactors:
        """Calculate all movement factors for a segment."""
        factors = MovementFactors(
            base_speed=transport.base_speed,
            biome_modifier=1.0,
            road_modifier=1.0,
            weather_modifier=1.0,
            season_modifier=1.0,
            transport_modifier=1.0,
            additional_modifiers={}
        )
        
        # Apply biome modifier
        biome_id_str = str(biome.biome_id)
        if biome_id_str in transport.terrain_modifiers:
            factors.biome_modifier = transport.terrain_modifiers[biome_id_str]
        else:
            factors.biome_modifier = biome.base_movement_modifier
        
        # Apply road modifier
        if road_type:
            factors.road_modifier = road_type.movement_modifier
        
        # Apply weather modifier
        if weather:
            factors.weather_modifier = weather.movement_modifier
            
            # Apply specific terrain effect if available
            if biome_id_str in weather.terrain_effects:
                factors.weather_modifier *= weather.terrain_effects[biome_id_str]
        
        # Apply season modifier
        factors.season_modifier = season.travel_modifier
        
        # Apply trader-specific modifiers
        # For example, trader skills or traits
        trader_biome_preference = getattr(trader, 'biome_preferences', None)
        if trader_biome_preference and biome.name in trader_biome_preference:
            factors.additional_modifiers['trader_familiarity'] = 1.2  # 20% boost in preferred biome
        
        # Factor in trader's transport proficiency
        # This could be based on a skill system
        transport_skill = getattr(trader, 'transport_skill', 0)
        if transport_skill > 0:
            factors.additional_modifiers['skill_bonus'] = 1.0 + (transport_skill * 0.05)  # 5% per skill level
        
        return factors
    
    def _calculate_travel_time(self, distance: float, factors: MovementFactors) -> float:
        """Calculate the time to travel a distance with given factors."""
        # Base calculation: distance / speed = time
        speed = factors.calculate_total_speed()
        
        if speed <= 0:
            return float('inf')  # Impassable
        
        return distance / speed
    
    def _calculate_encounter_chance(
        self,
        area: Area,
        transport: TransportMethod,
        weather: Optional[Weather],
        trader: Any
    ) -> float:
        """Calculate the chance of an encounter in this area."""
        # Base chance from area danger level
        base_chance = 0.05 + (area.danger_level * 0.02)  # 5% + 2% per danger level
        
        # Modify based on weather
        if weather:
            base_chance *= weather.encounter_modifier
        
        # Modify based on transport (e.g., larger/slower transports are more noticeable)
        if transport.name == 'on_foot':
            transport_modifier = 1.0
        elif transport.name in ['horse', 'griffon']:
            transport_modifier = 0.8  # Faster means fewer encounters
        else:
            transport_modifier = 1.2  # Carts/wagons attract more attention
        
        # Modify based on trader guards
        guard_count = getattr(trader, 'hired_guards', 0)
        guard_modifier = max(0.5, 1.0 - (guard_count * 0.1))  # Each guard reduces chance by 10%, min 50%
        
        final_chance = base_chance * transport_modifier * guard_modifier
        
        # Cap the chance at reasonable values
        return max(0.01, min(0.75, final_chance))
    
    def _calculate_segment_costs(
        self,
        area: Area,
        road_type: Optional[RoadType],
        transport: TransportMethod,
        travel_time: float
    ) -> Dict[str, Any]:
        """Calculate the costs for traveling through a segment."""
        costs = {
            'gold': 0,
            'resources': {}
        }
        
        # Toll costs if road has a toll
        if road_type and hasattr(road_type, 'toll_cost') and road_type.toll_cost > 0:
            costs['gold'] += road_type.toll_cost
        
        # Maintenance costs based on time traveled
        maintenance_per_day = transport.maintenance_cost
        days_traveled = travel_time / 24  # Convert hours to days
        costs['gold'] += int(maintenance_per_day * days_traveled)
        
        # Resource consumption (food, water, etc.)
        # This would depend on your game's resource system
        food_per_day = 1  # Base food unit per day
        food_consumed = food_per_day * days_traveled
        costs['resources']['food'] = food_consumed
        
        return costs
    
    def _calculate_segment_risks(
        self,
        area: Area,
        transport: TransportMethod,
        weather: Optional[Weather],
        travel_time: float
    ) -> List[Dict[str, Any]]:
        """Calculate the risks for traveling through a segment."""
        risks = []
        
        # Risk of cart damage
        if transport.name in ['cart', 'horse_cart', 'wagon', 'caravan']:
            damage_chance = 0.05 + (area.danger_level * 0.01)  # 5% + 1% per danger level
            damage_amount = 5 + (area.danger_level * 2)  # Base damage + extra by danger
            
            risks.append({
                'type': 'cart_damage',
                'chance': damage_chance,
                'severity': damage_amount,
                'description': f"Potential cart damage of {damage_amount}% due to {area.area_type} terrain"
            })
        
        # Risk of weather delay
        if weather and weather.name not in ['clear']:
            delay_chance = 0.1 * weather.encounter_modifier
            delay_hours = travel_time * 0.5  # 50% additional time
            
            risks.append({
                'type': 'weather_delay',
                'chance': delay_chance,
                'severity': delay_hours,
                'description': f"Potential delay of {int(delay_hours)} hours due to {weather.display_name}"
            })
        
        # Risk of bandit encounter
        if area.danger_level >= 3:
            bandit_chance = 0.05 * (area.danger_level - 2)
            
            risks.append({
                'type': 'bandit_encounter',
                'chance': bandit_chance,
                'severity': area.danger_level,
                'description': f"Risk of bandit encounter in {area.area_name}"
            })
        
        return risks