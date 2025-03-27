# app/game_state/services/encounter_service.py
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
import logging
import random
import math

logger = logging.getLogger(__name__)

class EncounterService:
    """
    Service to determine and generate encounters for NPCs based on multiple factors.
    Uses Monte Carlo Tree Search (MCTS) to select the most appropriate encounter.
    """
    
    def __init__(self, db: Session):
        """Initialize with database session"""
        self.db = db
    
    async def determine_best_encounter(self, npc_id: str, location_id: str) -> Dict[str, Any]:
        """
        Determine the best encounter for an NPC at a given location.
        Uses MCTS to evaluate all factors and select the most appropriate encounter.
        
        Args:
            npc_id: ID of the NPC to check
            location_id: Current location of the NPC
            
        Returns:
            Dict with selected encounter data or None if no encounter
        """
        # Gather all relevant data
        npc_data = self._get_npc_data(npc_id)
        location_data = self._get_location_data(location_id)
        world_state = self._get_world_state(location_id)
        
        # Extract specific factors
        npc_type = npc_data.get("type", "generic")
        npc_health = npc_data.get("health", 100)
        cart_health = npc_data.get("cart_health", 100) if npc_type == "merchant" else None
        biome = location_data.get("biome", "plains")
        weather = world_state.get("weather", "clear")
        time_of_day = world_state.get("time_of_day", "day")
        wildlife_density = location_data.get("wildlife_density", 0.3)
        faction_presence = self._get_faction_presence(location_id)
        danger_level = location_data.get("danger_level", 0.2)
        road_quality = location_data.get("road_quality", 0.5) if "road" in location_data.get("tags", []) else 0.1
        
        # Define possible encounter types
        encounter_types = [
            "none",                 # No encounter
            "bandit_attack",        # Bandits attack
            "wildlife_attack",      # Hostile wildlife attack
            "monster_attack",       # Monster attack
            "patrol_encounter",     # Encounter friendly patrol
            "merchant_encounter",   # Encounter another merchant
            "traveler_encounter",   # Encounter traveler(s)
            "natural_hazard",       # Weather or terrain hazard
            "ambush",               # Planned ambush
            "cargo_accident"        # Problem with cargo/cart
        ]
        
        # Run MCTS to determine best encounter
        selected_encounter, encounter_prob = self._run_encounter_mcts(
            encounter_types,
            {
                "npc_type": npc_type,
                "npc_health": npc_health,
                "cart_health": cart_health,
                "biome": biome,
                "weather": weather,
                "time_of_day": time_of_day,
                "wildlife_density": wildlife_density,
                "faction_presence": faction_presence,
                "danger_level": danger_level,
                "road_quality": road_quality
            }
        )
        
        logger.info(f"Selected encounter for {npc_id} at {location_id}: {selected_encounter} (prob: {encounter_prob:.2f})")
        
        # Check if we should have an encounter (probabilistic)
        if selected_encounter == "none" or random.random() > encounter_prob:
            return None
        
        # Generate the specific encounter
        return await self._generate_encounter(selected_encounter, npc_id, location_id, npc_data, location_data)
    
    def _run_encounter_mcts(self, encounter_types: List[str], 
                          factors: Dict[str, Any]) -> Tuple[str, float]:
        """
        Run Monte Carlo Tree Search to find the most appropriate encounter type.
        
        Args:
            encounter_types: List of possible encounter types
            factors: Dictionary of environmental and NPC factors
            
        Returns:
            Tuple of (selected encounter type, probability)
        """
        # MCTS parameters
        iterations = 100
        exploration_weight = 1.414  # UCB1 exploration parameter
        
        # Initialize scores and visits
        scores = {encounter: 0 for encounter in encounter_types}
        visits = {encounter: 0 for encounter in encounter_types}
        
        # Run MCTS iterations
        for _ in range(iterations):
            # Selection phase - using UCB1 formula
            total_visits = sum(visits.values()) or 1
            ucb_values = {}
            
            for encounter in encounter_types:
                if visits[encounter] == 0:
                    ucb_values[encounter] = float('inf')  # Ensure unexplored nodes are selected
                else:
                    exploitation = scores[encounter] / visits[encounter]
                    exploration = exploration_weight * (math.log(total_visits) / visits[encounter]) ** 0.5
                    ucb_values[encounter] = exploitation + exploration
            
            # Select encounter type with highest UCB value
            selected_type = max(ucb_values, key=ucb_values.get)
            
            # Simulation - evaluate how likely this encounter type would be
            reward = self._evaluate_encounter_probability(selected_type, factors)
            
            # Backpropagation - update scores and visit counts
            scores[selected_type] += reward
            visits[selected_type] += 1
        
        # Find encounter with highest average score
        best_encounter = max(encounter_types, key=lambda e: scores[e] / max(1, visits[e]))
        probability = scores[best_encounter] / max(1, visits[best_encounter])
        
        return best_encounter, probability
    
    def _evaluate_encounter_probability(self, encounter_type: str, 
                                      factors: Dict[str, Any]) -> float:
        """
        Evaluate the probability of a specific encounter type given the factors.
        
        Args:
            encounter_type: Type of encounter to evaluate
            factors: Dictionary of environmental and NPC factors
            
        Returns:
            float: Probability value (0-1)
        """
        # Base probabilities adjusted by various factors
        npc_type = factors.get("npc_type", "generic")
        cart_health = factors.get("cart_health", 100)
        npc_health = factors.get("npc_health", 100)
        danger_level = factors.get("danger_level", 0.2)
        time_of_day = factors.get("time_of_day", "day")
        biome = factors.get("biome", "plains")
        weather = factors.get("weather", "clear")
        wildlife_density = factors.get("wildlife_density", 0.3)
        faction_presence = factors.get("faction_presence", {})
        road_quality = factors.get("road_quality", 0.5)
        
        # Starting probability based on encounter type
        base_probabilities = {
            "none": 0.6,                # Most common is no encounter
            "bandit_attack": 0.08,      # Somewhat common
            "wildlife_attack": 0.07,    # Somewhat common
            "monster_attack": 0.03,     # Rare
            "patrol_encounter": 0.05,   # Uncommon
            "merchant_encounter": 0.05, # Uncommon
            "traveler_encounter": 0.06, # Uncommon
            "natural_hazard": 0.03,     # Rare
            "ambush": 0.02,             # Very rare
            "cargo_accident": 0.01      # Very rare
        }
        
        probability = base_probabilities.get(encounter_type, 0.01)
        
        # Apply modifiers based on factors
        # NPC type modifiers
        if npc_type == "merchant":
            if encounter_type == "bandit_attack":
                probability *= 1.5  # Merchants are more likely to be attacked
            elif encounter_type == "cargo_accident":
                probability *= 2.0  # Merchants can have cargo accidents
                
            # Cart health affects accident probability
            if encounter_type == "cargo_accident" and cart_health < 50:
                probability *= (2.0 - cart_health/100)  # More likely with damaged cart
        
        elif npc_type == "patrol":
            if encounter_type == "bandit_attack":
                probability *= 0.5  # Patrols less likely to be attacked
            elif encounter_type == "ambush":
                probability *= 2.0  # But more likely to be ambushed
        
        # NPC health affects combat encounter probability
        if encounter_type in ["bandit_attack", "wildlife_attack", "monster_attack", "ambush"]:
            if npc_health < 50:
                probability *= 1.3  # Wounded NPCs more likely to be attacked
        
        # Time of day modifiers
        if time_of_day == "night":
            if encounter_type in ["bandit_attack", "monster_attack", "ambush"]:
                probability *= 2.0  # More dangerous at night
            elif encounter_type == "none":
                probability *= 0.7  # Less likely to have no encounter at night
        
        # Biome modifiers
        biome_modifiers = {
            "forest": {
                "wildlife_attack": 1.5,
                "ambush": 1.7,
                "bandit_attack": 1.3
            },
            "mountains": {
                "natural_hazard": 1.8, 
                "monster_attack": 1.5
            },
            "swamp": {
                "natural_hazard": 2.0,
                "monster_attack": 1.7
            },
            "desert": {
                "natural_hazard": 1.8,
                "bandit_attack": 1.2
            },
            "plains": {
                "patrol_encounter": 1.3,
                "merchant_encounter": 1.3,
                "traveler_encounter": 1.4
            },
            "tundra": {
                "natural_hazard": 2.0,
                "wildlife_attack": 1.3
            }
        }
        
        if biome in biome_modifiers and encounter_type in biome_modifiers[biome]:
            probability *= biome_modifiers[biome][encounter_type]
        
        # Weather modifiers
        weather_modifiers = {
            "clear": {"none": 1.2},
            "rain": {
                "natural_hazard": 1.5,
                "cargo_accident": 1.3,
                "none": 0.9
            },
            "storm": {
                "natural_hazard": 2.5,
                "cargo_accident": 2.0,
                "none": 0.6
            },
            "fog": {
                "ambush": 1.8,
                "wildlife_attack": 1.4,
                "none": 0.8
            },
            "snow": {
                "natural_hazard": 2.0,
                "cargo_accident": 1.7,
                "none": 0.7
            }
        }
        
        if weather in weather_modifiers and encounter_type in weather_modifiers[weather]:
            probability *= weather_modifiers[weather][encounter_type]
        
        # Wildlife density affects wildlife encounters
        if encounter_type == "wildlife_attack":
            probability *= wildlife_density * 3.0  # Scale by density
        
        # Faction presence affects bandit and patrol encounters
        bandit_presence = faction_presence.get("bandits", 0)
        guard_presence = faction_presence.get("guards", 0)
        
        if encounter_type == "bandit_attack":
            probability *= bandit_presence * 2.0
            probability *= max(0.2, 1.0 - guard_presence)  # Guards reduce bandit attacks
        elif encounter_type == "patrol_encounter":
            probability *= guard_presence * 2.0
        
        # Road quality affects accidents and encounters
        if encounter_type == "cargo_accident":
            probability *= max(0.2, 1.0 - road_quality)  # Worse roads, more accidents
        elif encounter_type in ["patrol_encounter", "merchant_encounter", "traveler_encounter"]:
            probability *= road_quality * 1.5  # Better roads, more travelers
        
        # Global danger level multiplier
        if encounter_type in ["bandit_attack", "wildlife_attack", "monster_attack", "ambush"]:
            probability *= 1.0 + (danger_level * 2.0)  # Dangerous areas have more threats
        
        # Scale "none" encounter inversely with danger
        if encounter_type == "none":
            probability *= max(0.5, 1.0 - danger_level)
        
        # Add some randomness to simulate real-world variance
        probability = min(0.95, max(0.01, probability * random.uniform(0.8, 1.2)))
        
        return probability
    
    async def _generate_encounter(self, encounter_type: str, npc_id: str, 
                               location_id: str, npc_data: Dict[str, Any], 
                               location_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a specific encounter based on the selected type.
        
        Args:
            encounter_type: Selected encounter type
            npc_id: ID of the NPC
            location_id: Current location
            npc_data: NPC data
            location_data: Location data
            
        Returns:
            Dict with encounter data
        """
        from app.game_state.services.event_service import EventService
        event_service = EventService(self.db)
        
        # Base encounter data
        encounter_data = {
            "type": encounter_type,
            "npc_id": npc_id,
            "location_id": location_id,
            "timestamp": self._get_current_time()
        }
        
        # Generate specific encounter details based on type
        if encounter_type == "bandit_attack":
            # Determine bandit strength based on location danger
            danger = location_data.get("danger_level", 0.2)
            bandit_count = max(1, int(3 + (danger * 5)))
            bandit_level = max(1, int(1 + (danger * 4)))
            
            encounter_data.update({
                "attacker_type": "bandits",
                "attacker_count": bandit_count,
                "attacker_level": bandit_level,
                "severity": 0.5 + (danger * 0.5),
                "loot_quality": 0.2 + (danger * 0.6)  # Better loot from stronger bandits
            })
            
            # Create game event
            if npc_data.get("type") == "merchant":
                await event_service.create_event(
                    "trader_attacked",
                    target_id=npc_id,
                    location_id=location_id,
                    attacker_type="bandits",
                    severity=encounter_data["severity"],
                    nearest_settlement=self._get_nearest_settlement_id(location_id)
                )
            else:
                await event_service.create_event(
                    "npc_attacked",
                    target_id=npc_id,
                    location_id=location_id,
                    attacker_type="bandits",
                    severity=encounter_data["severity"]
                )
        
        elif encounter_type == "wildlife_attack":
            # Determine wildlife type based on biome
            biome = location_data.get("biome", "plains")
            wildlife_by_biome = {
                "forest": ["wolves", "bears", "boars"],
                "mountains": ["wolves", "bears", "mountain_lions"],
                "swamp": ["alligators", "snakes", "spiders"],
                "desert": ["scorpions", "snakes", "jackals"],
                "plains": ["wolves", "boars", "jackals"],
                "tundra": ["wolves", "polar_bears", "snow_leopards"]
            }
            
            wildlife_options = wildlife_by_biome.get(biome, ["wolves"])
            wildlife_type = random.choice(wildlife_options)
            
            # Wildlife amount and danger
            wildlife_density = location_data.get("wildlife_density", 0.3)
            wildlife_count = max(1, int(2 + (wildlife_density * 6)))
            
            encounter_data.update({
                "attacker_type": wildlife_type,
                "attacker_count": wildlife_count,
                "severity": 0.3 + (wildlife_density * 0.5),
                "is_predator": wildlife_type not in ["boars", "deer", "rabbits"]
            })
            
            # Create game event
            if npc_data.get("type") == "merchant":
                await event_service.create_event(
                    "trader_attacked",
                    target_id=npc_id,
                    location_id=location_id,
                    attacker_type=wildlife_type,
                    severity=encounter_data["severity"],
                    nearest_settlement=self._get_nearest_settlement_id(location_id)
                )
            else:
                await event_service.create_event(
                    "npc_attacked",
                    target_id=npc_id,
                    location_id=location_id,
                    attacker_type=wildlife_type,
                    severity=encounter_data["severity"]
                )
        
        elif encounter_type == "cargo_accident":
            # Determine accident type
            road_quality = location_data.get("road_quality", 0.5)
            weather = location_data.get("weather", "clear")
            
            accident_types = ["wheel_broken", "axle_damaged", "cargo_shifted", "cargo_fallen"]
            
            # Weight based on conditions
            weights = {
                "wheel_broken": 1.0 - road_quality,
                "axle_damaged": 0.5 * (1.0 - road_quality),
                "cargo_shifted": 0.2 + (0.3 if weather in ["rain", "storm"] else 0),
                "cargo_fallen": 0.1 + (0.4 if weather in ["storm", "snow"] else 0)
            }
            
            accident_weights = [weights[t] for t in accident_types]
            total_weight = sum(accident_weights)
            accident_probs = [w/total_weight for w in accident_weights]
            
            accident_type = random.choices(accident_types, weights=accident_probs, k=1)[0]
            
            # Determine severity
            severity = 0.3 + (0.6 * (1.0 - road_quality))
            if weather in ["rain", "storm", "snow"]:
                severity += 0.2
            
            encounter_data.update({
                "accident_type": accident_type,
                "severity": min(0.9, severity),
                "cargo_damage": random.uniform(0.1, severity),
                "repair_difficulty": 1.0 - road_quality
            })
            
            # Create game event
            await event_service.create_event(
                "cargo_accident",
                target_id=npc_id,
                location_id=location_id,
                accident_type=accident_type,
                severity=encounter_data["severity"],
                nearest_settlement=self._get_nearest_settlement_id(location_id)
            )
        
        # Implement other encounter types similarly...
        
        return encounter_data
    
    # Helper methods for getting data
    def _get_npc_data(self, npc_id: str) -> Dict[str, Any]:
        """Get NPC data from database"""
        from app.game_state.managers.npc_manager import NPCManager
        npc_manager = NPCManager()
        return npc_manager.get_npc(npc_id) or {}
    
    def _get_location_data(self, location_id: str) -> Dict[str, Any]:
        """Get location data from database"""
        from app.game_state.managers.location_manager import LocationManager
        location_manager = LocationManager()
        return location_manager.get_location(location_id) or {}
    
    def _get_world_state(self, location_id: str) -> Dict[str, Any]:
        """Get current world state for a location"""
        from app.game_state.managers.world_manager import WorldManager
        world_manager = WorldManager()
        return world_manager.get_location_state(location_id) or {}
    
    def _get_faction_presence(self, location_id: str) -> Dict[str, float]:
        """Get faction presence levels at a location"""
        from app.game_state.managers.faction_manager import FactionManager
        faction_manager = FactionManager()
        return faction_manager.get_faction_presence(location_id) or {}
    
    def _get_nearest_settlement_id(self, location_id: str) -> str:
        """Get ID of nearest settlement to a location"""
        from app.game_state.managers.location_manager import LocationManager
        location_manager = LocationManager()
        settlement = location_manager.get_nearest_settlement(location_id)
        return settlement.get("id") if settlement else None
    
    def _get_current_time(self) -> float:
        """Get current game timestamp"""
        import time
        return time.time()