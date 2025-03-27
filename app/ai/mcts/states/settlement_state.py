"""MCTS state representation for settlement decision making.

This module provides a state representation for settlements that is compatible
with the Monte Carlo Tree Search algorithm. It includes action generation,
state transition, and reward calculation for settlement decision making.
"""

from typing import List, Dict, Any, Optional, Set, Tuple
import random
import logging
import copy

logger = logging.getLogger(__name__)

class SettlementAction:
    """Represents an action a settlement can take."""
    
    def __init__(self, 
                 action_type: str, 
                 target_id: Optional[str] = None,
                 resource_type: Optional[str] = None,
                 building_type: Optional[str] = None):
        """
        Initialize a settlement action.
        
        Args:
            action_type: Type of action (build, upgrade, trade, etc.)
            target_id: ID of the target entity (for trade/diplomacy actions)
            resource_type: Type of resource (for resource-focused actions)
            building_type: Type of building (for construction actions)
        """
        self.action_type = action_type
        self.target_id = target_id
        self.resource_type = resource_type
        self.building_type = building_type
        
        # Optional data for specialized actions
        self.resource_cost = {}  # Resources spent on this action
        self.gold_cost = 0  # Gold cost of this action
        self.population_change = 0  # Population change from this action
        self.prosperity_change = 0  # Prosperity change from this action
        self.score = 1.0  # Base score for action selection
        
    def __str__(self) -> str:
        """String representation of the action."""
        if self.action_type == "build":
            return f"Build {self.building_type}"
        elif self.action_type == "upgrade":
            return f"Upgrade {self.building_type or self.target_id}"
        elif self.action_type == "trade":
            return f"Trade with {self.target_id}"
        elif self.action_type == "harvest":
            return f"Harvest {self.resource_type}"
        elif self.action_type == "expand":
            return "Expand settlement"
        elif self.action_type == "establish_route":
            return f"Establish trade route to {self.target_id}"
        else:
            return f"{self.action_type} action"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert action to dictionary."""
        return {
            "type": self.action_type,
            "target_id": self.target_id,
            "resource_type": self.resource_type,
            "building_type": self.building_type,
            "resource_cost": self.resource_cost,
            "gold_cost": self.gold_cost,
            "population_change": self.population_change,
            "prosperity_change": self.prosperity_change,
            "score": self.score
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SettlementAction':
        """Create action from dictionary."""
        action = cls(
            action_type=data.get("type", "unknown"),
            target_id=data.get("target_id"),
            resource_type=data.get("resource_type"),
            building_type=data.get("building_type")
        )
        action.resource_cost = data.get("resource_cost", {})
        action.gold_cost = data.get("gold_cost", 0)
        action.population_change = data.get("population_change", 0)
        action.prosperity_change = data.get("prosperity_change", 0)
        action.score = data.get("score", 1.0)
        return action

class SettlementState:
    """
    State representation for settlement AI decision-making using MCTS.
    
    This class represents the state of a settlement for use in Monte Carlo Tree Search,
    including information about the settlement, the world, and available actions.
    """
    
    def __init__(self, settlement_data: Dict[str, Any], world_data: Optional[Dict[str, Any]] = None):
        """
        Initialize settlement state.
        
        Args:
            settlement_data: Dictionary with settlement entity properties
            world_data: Dictionary with world state information
        """
        self.settlement_data = settlement_data
        self.world_data = world_data or {}
        self._legal_actions = None
        
        # Cache frequently used values for performance
        self.settlement_id = settlement_data.get("id")
        self.settlement_name = settlement_data.get("name", "Unknown Settlement")
        self.settlement_type = settlement_data.get("settlement_type", "village")
        self.population = settlement_data.get("population", 0)
        self.resources = settlement_data.get("resources", {})
        self.gold = settlement_data.get("gold", 0)
        self.buildings = settlement_data.get("buildings", {})
        self.prosperity = settlement_data.get("prosperity", 0)
        self.growth_rate = settlement_data.get("growth_rate", 0)
        self.faction_id = settlement_data.get("faction_id")
        self.trade_routes = settlement_data.get("trade_routes", [])
        self.connected_settlements = settlement_data.get("connected_settlements", [])
        self.available_resources = settlement_data.get("available_resources", {})
        self.biome = settlement_data.get("biome", "temperate")
        self.defense_rating = settlement_data.get("defense_rating", 0)
        self.happiness = settlement_data.get("happiness", 50)
        
    def get_legal_actions(self) -> List[SettlementAction]:
        """
        Get all legal actions in the current state.
        
        Returns:
            List of SettlementAction objects representing possible actions
        """
        # Use cached actions if available
        if self._legal_actions is not None:
            return self._legal_actions
        
        actions = []
        
        # Add building actions
        building_actions = self._get_building_actions()
        actions.extend(building_actions)
        
        # Add upgrade actions for existing buildings
        upgrade_actions = self._get_upgrade_actions()
        actions.extend(upgrade_actions)
        
        # Add trade actions with connected settlements
        trade_actions = self._get_trade_actions()
        actions.extend(trade_actions)
        
        # Add resource harvesting actions
        harvest_actions = self._get_harvest_actions()
        actions.extend(harvest_actions)
        
        # Add expansion action if population is high enough
        if self._can_expand():
            expand_action = SettlementAction(action_type="expand")
            expand_action.resource_cost = {
                "wood": 100,
                "stone": 50,
                "food": 100
            }
            expand_action.gold_cost = 200
            expand_action.population_change = 0
            expand_action.prosperity_change = 10
            actions.append(expand_action)
        
        # Add trade route establishment actions
        trade_route_actions = self._get_trade_route_actions()
        actions.extend(trade_route_actions)
        
        # Calculate action scores based on settlement state
        self._calculate_action_scores(actions)
        
        # Cache actions
        self._legal_actions = actions
        return actions
    
    def _get_building_actions(self) -> List[SettlementAction]:
        """
        Get possible building construction actions.
        
        Returns:
            List of building actions
        """
        actions = []
        
        # Define building types with their costs and benefits
        building_types = {
            "house": {
                "resource_cost": {"wood": 20, "stone": 5},
                "gold_cost": 10,
                "population_change": 5,
                "prosperity_change": 1,
                "min_settlement_type": "village"
            },
            "farm": {
                "resource_cost": {"wood": 15},
                "gold_cost": 20,
                "population_change": 0,
                "prosperity_change": 2,
                "min_settlement_type": "village"
            },
            "market": {
                "resource_cost": {"wood": 30, "stone": 10},
                "gold_cost": 50,
                "population_change": 0,
                "prosperity_change": 5,
                "min_settlement_type": "village"
            },
            "blacksmith": {
                "resource_cost": {"wood": 20, "stone": 15, "iron": 10},
                "gold_cost": 40,
                "population_change": 0,
                "prosperity_change": 3,
                "min_settlement_type": "village"
            },
            "tavern": {
                "resource_cost": {"wood": 25, "stone": 5},
                "gold_cost": 30,
                "population_change": 0,
                "prosperity_change": 3,
                "min_settlement_type": "village"
            },
            "church": {
                "resource_cost": {"wood": 20, "stone": 30},
                "gold_cost": 60,
                "population_change": 0,
                "prosperity_change": 5,
                "min_settlement_type": "town"
            },
            "town_hall": {
                "resource_cost": {"wood": 40, "stone": 50},
                "gold_cost": 100,
                "population_change": 0,
                "prosperity_change": 10,
                "min_settlement_type": "town"
            },
            "walls": {
                "resource_cost": {"stone": 100},
                "gold_cost": 150,
                "population_change": 0,
                "prosperity_change": 0,  # No direct prosperity, but increases defense
                "min_settlement_type": "town"
            },
            "castle": {
                "resource_cost": {"stone": 200, "iron": 50},
                "gold_cost": 300,
                "population_change": 0,
                "prosperity_change": 15,
                "min_settlement_type": "city"
            }
        }
        
        # Check each building type if it can be built
        for building_type, building_info in building_types.items():
            # Skip buildings we already have the maximum of
            existing_count = self.buildings.get(building_type, 0)
            max_count = self._get_max_building_count(building_type)
            if existing_count >= max_count:
                continue
            
            # Skip buildings that require higher settlement type
            if not self._meets_settlement_type_requirement(building_info["min_settlement_type"]):
                continue
            
            # Check if we have enough resources
            if not self._can_afford_resources(building_info["resource_cost"]):
                continue
                
            # Check if we have enough gold
            if self.gold < building_info["gold_cost"]:
                continue
            
            # Create build action
            build_action = SettlementAction(
                action_type="build",
                building_type=building_type
            )
            build_action.resource_cost = building_info["resource_cost"]
            build_action.gold_cost = building_info["gold_cost"]
            build_action.population_change = building_info["population_change"]
            build_action.prosperity_change = building_info["prosperity_change"]
            
            actions.append(build_action)
        
        return actions
    
    def _get_upgrade_actions(self) -> List[SettlementAction]:
        """
        Get possible building upgrade actions.
        
        Returns:
            List of upgrade actions
        """
        actions = []
        
        # Define upgrade costs and benefits for building types
        upgrade_info = {
            "house": {
                "resource_cost": {"wood": 10, "stone": 5},
                "gold_cost": 5,
                "population_change": 2,
                "prosperity_change": 1
            },
            "farm": {
                "resource_cost": {"wood": 5, "stone": 5},
                "gold_cost": 10,
                "population_change": 0,
                "prosperity_change": 1
            },
            "market": {
                "resource_cost": {"wood": 15, "stone": 10},
                "gold_cost": 25,
                "population_change": 0,
                "prosperity_change": 3
            },
            "blacksmith": {
                "resource_cost": {"wood": 10, "stone": 5, "iron": 5},
                "gold_cost": 20,
                "population_change": 0,
                "prosperity_change": 2
            },
            "tavern": {
                "resource_cost": {"wood": 10, "stone": 5},
                "gold_cost": 15,
                "population_change": 0,
                "prosperity_change": 2
            }
            # Other buildings can be upgraded as needed
        }
        
        # Check each building type that we have for potential upgrades
        for building_type, count in self.buildings.items():
            if count < 1 or building_type not in upgrade_info:
                continue
            
            # Check if we have enough resources
            if not self._can_afford_resources(upgrade_info[building_type]["resource_cost"]):
                continue
                
            # Check if we have enough gold
            if self.gold < upgrade_info[building_type]["gold_cost"]:
                continue
            
            # Create upgrade action
            upgrade_action = SettlementAction(
                action_type="upgrade",
                building_type=building_type
            )
            upgrade_action.resource_cost = upgrade_info[building_type]["resource_cost"]
            upgrade_action.gold_cost = upgrade_info[building_type]["gold_cost"]
            upgrade_action.population_change = upgrade_info[building_type]["population_change"]
            upgrade_action.prosperity_change = upgrade_info[building_type]["prosperity_change"]
            
            actions.append(upgrade_action)
        
        return actions
    
    def _get_trade_actions(self) -> List[SettlementAction]:
        """
        Get possible trade actions with connected settlements.
        
        Returns:
            List of trade actions
        """
        actions = []
        
        # Check each connected settlement
        for settlement_id in self.connected_settlements:
            # Get the settlement data
            settlement_data = self._get_settlement_data(settlement_id)
            if not settlement_data:
                continue
            
            # Check what resources they have that we need
            for resource_type, amount in settlement_data.get("resources", {}).items():
                if amount > 0 and (resource_type not in self.resources or self.resources[resource_type] < 50):
                    # Create trade action to acquire resource
                    trade_action = SettlementAction(
                        action_type="trade",
                        target_id=settlement_id,
                        resource_type=resource_type
                    )
                    trade_action.gold_cost = 10
                    actions.append(trade_action)
            
            # Check what resources we have that they might need
            for resource_type, amount in self.resources.items():
                if amount > 50:
                    # Create trade action to sell resource
                    trade_action = SettlementAction(
                        action_type="trade_sell",
                        target_id=settlement_id,
                        resource_type=resource_type
                    )
                    trade_action.gold_cost = -20  # Negative cost means gain
                    actions.append(trade_action)
        
        return actions
    
    def _get_harvest_actions(self) -> List[SettlementAction]:
        """
        Get possible resource harvesting actions.
        
        Returns:
            List of harvest actions
        """
        actions = []
        
        # Check what resources are available in the vicinity
        for resource_type, amount in self.available_resources.items():
            if amount > 0:
                # Create harvest action
                harvest_action = SettlementAction(
                    action_type="harvest",
                    resource_type=resource_type
                )
                
                # Different resources have different costs and yields
                if resource_type == "wood":
                    harvest_action.population_change = -2  # Requires workers
                    harvest_action.prosperity_change = 0
                elif resource_type == "stone":
                    harvest_action.population_change = -3  # Requires more workers
                    harvest_action.prosperity_change = 0
                elif resource_type == "food":
                    harvest_action.population_change = -1
                    harvest_action.prosperity_change = 1
                elif resource_type == "iron":
                    harvest_action.population_change = -3
                    harvest_action.prosperity_change = 1
                
                actions.append(harvest_action)
        
        return actions
    
    def _get_trade_route_actions(self) -> List[SettlementAction]:
        """
        Get possible actions to establish new trade routes.
        
        Returns:
            List of trade route establishment actions
        """
        actions = []
        
        # Check nearby settlements that aren't already connected
        nearby_settlements = self._get_nearby_settlements()
        for settlement_id in nearby_settlements:
            if settlement_id not in self.trade_routes and settlement_id not in self.connected_settlements:
                settlement_data = self._get_settlement_data(settlement_id)
                if not settlement_data:
                    continue
                
                # Create action to establish trade route
                route_action = SettlementAction(
                    action_type="establish_route",
                    target_id=settlement_id
                )
                route_action.resource_cost = {"wood": 30}
                route_action.gold_cost = 50
                route_action.prosperity_change = 3
                
                actions.append(route_action)
        
        return actions
    
    def _can_expand(self) -> bool:
        """
        Check if the settlement can expand.
        
        Returns:
            True if expansion is possible, False otherwise
        """
        # Need minimum population and prosperity
        min_population = {
            "village": 50,
            "town": 100,
            "city": 200
        }
        
        min_prosperity = {
            "village": 20,
            "town": 50,
            "city": 100
        }
        
        # Check current settlement type
        if self.settlement_type == "city":
            return False  # Already at highest type
            
        next_type = "town" if self.settlement_type == "village" else "city"
        
        return (self.population >= min_population[self.settlement_type] and 
                self.prosperity >= min_prosperity[self.settlement_type])
    
    def _get_max_building_count(self, building_type: str) -> int:
        """
        Get the maximum number of a specific building type allowed.
        
        Args:
            building_type: The type of building
            
        Returns:
            Maximum allowed count
        """
        # Base limits by settlement type
        base_limits = {
            "village": {
                "house": 10,
                "farm": 5,
                "market": 1,
                "blacksmith": 1,
                "tavern": 1,
                "church": 0,
                "town_hall": 0,
                "walls": 0,
                "castle": 0
            },
            "town": {
                "house": 20,
                "farm": 10,
                "market": 2,
                "blacksmith": 2,
                "tavern": 2,
                "church": 1,
                "town_hall": 1,
                "walls": 1,
                "castle": 0
            },
            "city": {
                "house": 40,
                "farm": 15,
                "market": 3,
                "blacksmith": 3,
                "tavern": 3,
                "church": 2,
                "town_hall": 1,
                "walls": 1,
                "castle": 1
            }
        }
        
        # Get limit for current settlement type
        if self.settlement_type in base_limits and building_type in base_limits[self.settlement_type]:
            return base_limits[self.settlement_type][building_type]
        
        return 0  # Default limit is zero
    
    def _meets_settlement_type_requirement(self, required_type: str) -> bool:
        """
        Check if the settlement meets a settlement type requirement.
        
        Args:
            required_type: The required settlement type
            
        Returns:
            True if requirement is met, False otherwise
        """
        # Settlement type hierarchy
        type_hierarchy = {
            "village": 1,
            "town": 2,
            "city": 3
        }
        
        current_level = type_hierarchy.get(self.settlement_type, 0)
        required_level = type_hierarchy.get(required_type, 0)
        
        return current_level >= required_level
    
    def _can_afford_resources(self, resource_cost: Dict[str, int]) -> bool:
        """
        Check if the settlement has enough resources for a cost.
        
        Args:
            resource_cost: Dictionary of resource types to amounts
            
        Returns:
            True if the settlement can afford the cost, False otherwise
        """
        for resource_type, amount in resource_cost.items():
            if resource_type not in self.resources or self.resources[resource_type] < amount:
                return False
        
        return True
    
    def _get_settlement_data(self, settlement_id: str) -> Dict[str, Any]:
        """
        Get data for a settlement by ID.
        
        Args:
            settlement_id: The ID of the settlement
            
        Returns:
            Settlement data dictionary or empty dict if not found
        """
        settlements = self.world_data.get("settlements", {})
        return settlements.get(settlement_id, {})
    
    def _get_nearby_settlements(self) -> List[str]:
        """
        Get list of nearby settlements.
        
        Returns:
            List of settlement IDs
        """
        # In a real implementation, this would use geographic data
        # For this example, we'll use the world data's "nearby_settlements" if available
        if "nearby_settlements" in self.settlement_data:
            return self.settlement_data["nearby_settlements"]
        
        # Alternative: use connected settlements and their connections (up to 2 hops)
        nearby = set(self.connected_settlements)
        
        for connected_id in self.connected_settlements:
            settlement_data = self._get_settlement_data(connected_id)
            if settlement_data:
                for second_hop in settlement_data.get("connected_settlements", []):
                    if second_hop != self.settlement_id:  # Avoid self-reference
                        nearby.add(second_hop)
        
        return list(nearby)
    
    def _calculate_action_scores(self, actions: List[SettlementAction]) -> None:
        """
        Calculate scores for each action based on settlement state and priorities.
        
        Args:
            actions: List of actions to score
        """
        for action in actions:
            score = 1.0  # Base score
            
            # Apply different scoring strategies based on action type
            if action.action_type == "build":
                # Higher score for buildings that increase population if population is low
                if action.population_change > 0 and self.population < 50:
                    score += 1.0
                
                # Higher score for buildings that increase prosperity
                score += action.prosperity_change * 0.2
                
                # Balance against resource costs
                total_resource_cost = sum(amount for amount in action.resource_cost.values())
                total_resources = sum(amount for amount in self.resources.values())
                
                # If resources are scarce, building is less appealing
                if total_resources > 0:
                    resource_ratio = total_resource_cost / total_resources
                    if resource_ratio > 0.5:
                        score -= 0.5
                
                # Adjust for settlement needs
                if action.building_type == "house" and self.population > 100:
                    score += 0.5  # More housing for growing population
                elif action.building_type == "farm" and "food" in self.resources and self.resources["food"] < 50:
                    score += 1.0  # Need food
                elif action.building_type == "walls" and self.defense_rating < 20:
                    score += 1.0  # Need defense
            
            elif action.action_type == "upgrade":
                # Upgrading is generally good if we have the resources
                score += 0.5
                
                # Specific building type priorities
                if action.building_type == "farm" and "food" in self.resources and self.resources["food"] < 30:
                    score += 1.0  # Prioritize food production
                elif action.building_type == "market":
                    score += 0.5  # Markets help with trade
            
            elif action.action_type == "trade":
                # Trading to acquire resources we need
                if action.resource_type in self.resources and self.resources[action.resource_type] < 20:
                    score += 1.0  # High priority if we're low on this resource
                
                # Biome-specific resource needs
                if self.biome == "desert" and action.resource_type == "wood":
                    score += 0.5  # Desert settlements need wood
                elif self.biome == "forest" and action.resource_type == "stone":
                    score += 0.5  # Forest settlements need stone
            
            elif action.action_type == "trade_sell":
                # Trading to get gold
                if self.gold < 50:
                    score += 0.5  # Need gold
                
                # Sell excess resources
                if action.resource_type in self.resources and self.resources[action.resource_type] > 100:
                    score += 0.5  # Have surplus
            
            elif action.action_type == "harvest":
                # Harvesting resources we need
                if action.resource_type in self.resources and self.resources[action.resource_type] < 30:
                    score += 1.0
                elif action.resource_type not in self.resources:
                    score += 0.5  # Don't have any of this resource yet
            
            elif action.action_type == "expand":
                # Expansion is high priority if all conditions are met
                score += 2.0
                
                # But reduce score if resources are tight
                total_resource_cost = sum(amount for amount in action.resource_cost.values())
                total_resources = sum(amount for amount in self.resources.values())
                
                if total_resources > 0:
                    resource_ratio = total_resource_cost / total_resources
                    if resource_ratio > 0.7:
                        score -= 1.0  # Too expensive right now
            
            elif action.action_type == "establish_route":
                # Trade routes are good for prosperity
                score += 0.7
                
                # Check if target settlement has resources we need
                target_settlement = self._get_settlement_data(action.target_id)
                for resource, amount in target_settlement.get("resources", {}).items():
                    if amount > 0 and (resource not in self.resources or self.resources[resource] < 30):
                        score += 0.3  # They have something we need
            
            # Adjust score based on costs
            if action.gold_cost > 0:
                # Reduce score if gold cost is high relative to available gold
                if self.gold > 0:
                    cost_ratio = action.gold_cost / self.gold
                    if cost_ratio > 0.5:
                        score -= cost_ratio * 0.5
            
            # Adjust for population cost
            if action.population_change < 0:
                # Actions that require workers are less appealing if population is low
                if self.population < 20:
                    score -= 0.5
            
            # Ensure minimum score
            action.score = max(0.1, score)
    
    def apply_action(self, action: SettlementAction) -> 'SettlementState':
        """
        Apply an action to this state and return the new state.
        
        Args:
            action: The action to apply
            
        Returns:
            A new SettlementState resulting from the action
        """
        # Create a deep copy of the current state
        new_settlement_data = copy.deepcopy(self.settlement_data)
        new_state = SettlementState(new_settlement_data, copy.deepcopy(self.world_data))
        
        # Apply the action effect based on type
        if action.action_type == "build":
            # Add building
            if action.building_type not in new_state.settlement_data["buildings"]:
                new_state.settlement_data["buildings"][action.building_type] = 0
            new_state.settlement_data["buildings"][action.building_type] += 1
            new_state.buildings = new_state.settlement_data["buildings"]
            
            # Deduct resources
            for resource_type, amount in action.resource_cost.items():
                if resource_type in new_state.settlement_data["resources"]:
                    new_state.settlement_data["resources"][resource_type] -= amount
            new_state.resources = new_state.settlement_data["resources"]
            
            # Deduct gold
            new_state.settlement_data["gold"] -= action.gold_cost
            new_state.gold = new_state.settlement_data["gold"]
            
            # Add population
            new_state.settlement_data["population"] += action.population_change
            new_state.population = new_state.settlement_data["population"]
            
            # Add prosperity
            new_state.settlement_data["prosperity"] += action.prosperity_change
            new_state.prosperity = new_state.settlement_data["prosperity"]
            
            # Special effects for certain buildings
            if action.building_type == "walls":
                defense_bonus = 10
                if "defense_rating" not in new_state.settlement_data:
                    new_state.settlement_data["defense_rating"] = 0
                new_state.settlement_data["defense_rating"] += defense_bonus
                new_state.defense_rating = new_state.settlement_data["defense_rating"]
        
        elif action.action_type == "upgrade":
            # Deduct resources
            for resource_type, amount in action.resource_cost.items():
                if resource_type in new_state.settlement_data["resources"]:
                    new_state.settlement_data["resources"][resource_type] -= amount
            new_state.resources = new_state.settlement_data["resources"]
            
            # Deduct gold
            new_state.settlement_data["gold"] -= action.gold_cost
            new_state.gold = new_state.settlement_data["gold"]
            
            # Add population
            new_state.settlement_data["population"] += action.population_change
            new_state.population = new_state.settlement_data["population"]
            
            # Add prosperity
            new_state.settlement_data["prosperity"] += action.prosperity_change
            new_state.prosperity = new_state.settlement_data["prosperity"]
        
        elif action.action_type == "trade":
            # Trading to acquire resources
            if action.resource_type not in new_state.settlement_data["resources"]:
                new_state.settlement_data["resources"][action.resource_type] = 0
            new_state.settlement_data["resources"][action.resource_type] += 20  # Gain 20 units
            new_state.resources = new_state.settlement_data["resources"]
            
            # Deduct gold
            new_state.settlement_data["gold"] -= action.gold_cost
            new_state.gold = new_state.settlement_data["gold"]
        
        elif action.action_type == "trade_sell":
            # Trading to sell resources
            if action.resource_type in new_state.settlement_data["resources"]:
                new_state.settlement_data["resources"][action.resource_type] -= 20  # Lose 20 units
                if new_state.settlement_data["resources"][action.resource_type] < 0:
                    new_state.settlement_data["resources"][action.resource_type] = 0
            new_state.resources = new_state.settlement_data["resources"]
            
            # Add gold (negative cost means gain)
            new_state.settlement_data["gold"] -= action.gold_cost  # Remember, it's negative
            new_state.gold = new_state.settlement_data["gold"]
        
        elif action.action_type == "harvest":
            # Harvesting resources
            if action.resource_type not in new_state.settlement_data["resources"]:
                new_state.settlement_data["resources"][action.resource_type] = 0
                
            # Resource yields vary by type
            resource_yield = 0
            if action.resource_type == "wood":
                resource_yield = 30
            elif action.resource_type == "stone":
                resource_yield = 20
            elif action.resource_type == "food":
                resource_yield = 40
            elif action.resource_type == "iron":
                resource_yield = 15
            else:
                resource_yield = 10
                
            new_state.settlement_data["resources"][action.resource_type] += resource_yield
            new_state.resources = new_state.settlement_data["resources"]
            
            # Adjust population (workers allocated)
            new_state.settlement_data["population"] += action.population_change
            new_state.population = new_state.settlement_data["population"]
            
            # Add prosperity
            new_state.settlement_data["prosperity"] += action.prosperity_change
            new_state.prosperity = new_state.settlement_data["prosperity"]
        
        elif action.action_type == "expand":
            # Upgrade settlement type
            if new_state.settlement_data["settlement_type"] == "village":
                new_state.settlement_data["settlement_type"] = "town"
            elif new_state.settlement_data["settlement_type"] == "town":
                new_state.settlement_data["settlement_type"] = "city"
            new_state.settlement_type = new_state.settlement_data["settlement_type"]
            
            # Deduct resources
            for resource_type, amount in action.resource_cost.items():
                if resource_type in new_state.settlement_data["resources"]:
                    new_state.settlement_data["resources"][resource_type] -= amount
            new_state.resources = new_state.settlement_data["resources"]
            
            # Deduct gold
            new_state.settlement_data["gold"] -= action.gold_cost
            new_state.gold = new_state.settlement_data["gold"]
            
            # Add prosperity
            new_state.settlement_data["prosperity"] += action.prosperity_change
            new_state.prosperity = new_state.settlement_data["prosperity"]
            
            # Increase growth rate
            growth_bonus = 5 if new_state.settlement_type == "town" else 10
            new_state.settlement_data["growth_rate"] += growth_bonus
            new_state.growth_rate = new_state.settlement_data["growth_rate"]
        
        elif action.action_type == "establish_route":
            # Add trade route
            if "trade_routes" not in new_state.settlement_data:
                new_state.settlement_data["trade_routes"] = []
            new_state.settlement_data["trade_routes"].append(action.target_id)
            new_state.trade_routes = new_state.settlement_data["trade_routes"]
            
            # Add to connected settlements
            if "connected_settlements" not in new_state.settlement_data:
                new_state.settlement_data["connected_settlements"] = []
            if action.target_id not in new_state.settlement_data["connected_settlements"]:
                new_state.settlement_data["connected_settlements"].append(action.target_id)
            new_state.connected_settlements = new_state.settlement_data["connected_settlements"]
            
            # Deduct resources
            for resource_type, amount in action.resource_cost.items():
                if resource_type in new_state.settlement_data["resources"]:
                    new_state.settlement_data["resources"][resource_type] -= amount
            new_state.resources = new_state.settlement_data["resources"]
            
            # Deduct gold
            new_state.settlement_data["gold"] -= action.gold_cost
            new_state.gold = new_state.settlement_data["gold"]
            
            # Add prosperity
            new_state.settlement_data["prosperity"] += action.prosperity_change
            new_state.prosperity = new_state.settlement_data["prosperity"]
        
        # Clear cached actions
        new_state._legal_actions = None
        
        return new_state
    
    def is_terminal(self) -> bool:
        """
        Check if this is a terminal state (simulation should end).
        
        Returns:
            True if terminal, False otherwise
        """
        # For settlements, a simulation might end if:
        
        # 1. Settlement has reached city status with high prosperity
        if self.settlement_type == "city" and self.prosperity >= 200:
            return True
        
        # 2. Settlement has completely depleted its resources and gold
        total_resources = sum(amount for amount in self.resources.values())
        if total_resources == 0 and self.gold == 0:
            return True
        
        # 3. Settlement has no population
        if self.population <= 0:
            return True
        
        return False
    
    def get_reward(self) -> float:
        """
        Calculate reward value for this state.
        
        Returns:
            Float reward value (higher is better)
        """
        reward = 0.0
        
        # Reward for population
        reward += self.population * 0.1
        
        # Reward for buildings
        total_buildings = sum(count for count in self.buildings.values())
        reward += total_buildings * 5.0
        
        # Reward for prosperity
        reward += self.prosperity * 0.5
        
        # Reward for settlement type
        type_value = {
            "village": 10,
            "town": 30,
            "city": 60
        }
        reward += type_value.get(self.settlement_type, 0)
        
        # Reward for trade routes
        reward += len(self.trade_routes) * 10.0
        
        # Reward for resources
        total_resources = sum(amount for amount in self.resources.values())
        reward += total_resources * 0.05
        
        # Reward for gold
        reward += self.gold * 0.1
        
        # Reward for defense
        reward += self.defense_rating * 0.2
        
        # Reward for happiness
        reward += self.happiness * 0.1
        
        return reward
    
    def __str__(self) -> str:
        """String representation of the state."""
        return f"{self.settlement_name} ({self.settlement_type}) with population {self.population}, prosperity {self.prosperity}, and {len(self.buildings)} buildings"
        
    # Method for compatibility with the SettlementEntity interface
    @classmethod
    def from_settlement_entity(cls, settlement, world_info=None):
        """
        Create a SettlementState from a Settlement entity.
        
        Args:
            settlement: The settlement entity
            world_info: Optional world information
            
        Returns:
            SettlementState: A new state object representing the settlement
        """
        # Convert settlement entity to data dictionary
        settlement_data = settlement.to_dict() if hasattr(settlement, 'to_dict') else {}
        
        # If to_dict isn't available, get properties directly
        if not settlement_data and hasattr(settlement, 'get_property'):
            settlement_data = {
                "id": getattr(settlement, 'settlement_id', None),
                "name": settlement.get_property("name") or getattr(settlement, 'settlement_name', "Unknown"),
                "settlement_type": settlement.get_property("settlement_type", "village"),
                "population": settlement.get_property("population", 0),
                "resources": settlement.get_property("resources", {}),
                "gold": settlement.get_property("gold", 0),
                "buildings": settlement.get_property("buildings", {}),
                "prosperity": settlement.get_property("prosperity", 0),
                "growth_rate": settlement.get_property("growth_rate", 0),
                "faction_id": settlement.get_property("faction_id"),
                "trade_routes": settlement.get_property("trade_routes", []),
                "connected_settlements": settlement.get_property("connected_settlements", []),
                "available_resources": settlement.get_property("available_resources", {}),
                "biome": settlement.get_property("biome", "temperate"),
                "defense_rating": settlement.get_property("defense_rating", 0),
                "happiness": settlement.get_property("happiness", 50)
            }
            
        return cls(settlement_data, world_info or {})