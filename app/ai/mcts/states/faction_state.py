"""MCTS state representation for faction decision making.

This module provides a state representation for factions that is compatible
with the Monte Carlo Tree Search algorithm. It includes action generation,
state transition, and reward calculation for faction decision making.
"""

from typing import List, Dict, Any, Optional, Set, Tuple
import random
import logging
import copy

logger = logging.getLogger(__name__)

class FactionAction:
    """Represents an action a faction can take."""
    
    def __init__(self, 
                 action_type: str, 
                 location_id: Optional[str] = None,
                 target_id: Optional[str] = None):
        """
        Initialize a faction action.
        
        Args:
            action_type: Type of action (move, trade, diplomacy, etc.)
            location_id: ID of the location (for move actions)
            target_id: ID of the target entity (for diplomacy/trade actions)
        """
        self.action_type = action_type
        self.location_id = location_id
        self.target_id = target_id
        
        # Optional data for specialized actions
        self.resource_cost = {}  # Resources spent on this action
        self.gold_cost = 0  # Gold cost of this action
        self.influence_gain = 0  # Influence gained from this action
        self.score = 1.0  # Base score for action selection
        
    def __str__(self) -> str:
        """String representation of the action."""
        if self.action_type == "move":
            return f"Move to {self.location_id}"
        elif self.action_type == "trade":
            return f"Trade with {self.target_id}"
        elif self.action_type == "diplomacy":
            return f"Diplomatic action with {self.target_id}"
        elif self.action_type == "recruit":
            return "Recruit new members"
        elif self.action_type == "establish_outpost":
            return f"Establish outpost at {self.location_id}"
        elif self.action_type == "quest":
            return f"Issue quest at {self.location_id}"
        else:
            return f"{self.action_type} action"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert action to dictionary."""
        return {
            "type": self.action_type,
            "location_id": self.location_id,
            "target_id": self.target_id,
            "resource_cost": self.resource_cost,
            "gold_cost": self.gold_cost,
            "influence_gain": self.influence_gain,
            "score": self.score
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FactionAction':
        """Create action from dictionary."""
        action = cls(
            action_type=data.get("type", "unknown"),
            location_id=data.get("location_id"),
            target_id=data.get("target_id")
        )
        action.resource_cost = data.get("resource_cost", {})
        action.gold_cost = data.get("gold_cost", 0)
        action.influence_gain = data.get("influence_gain", 0)
        action.score = data.get("score", 1.0)
        return action

class FactionState:
    """
    State representation for faction AI decision-making using MCTS.
    
    This class represents the state of a faction for use in Monte Carlo Tree Search,
    including information about the faction, the world, and available actions.
    """
    
    def __init__(self, faction_data: Dict[str, Any], world_data: Optional[Dict[str, Any]] = None):
        """
        Initialize faction state.
        
        Args:
            faction_data: Dictionary with faction entity properties
            world_data: Dictionary with world state information
        """
        self.faction_data = faction_data
        self.world_data = world_data or {}
        self._legal_actions = None
        
        # Cache frequently used values for performance
        self.faction_id = faction_data.get("id")
        self.faction_name = faction_data.get("name", "Unknown Faction")
        self.faction_type = faction_data.get("faction_type", "minor")
        self.current_location_id = faction_data.get("current_location_id")
        self.gold = faction_data.get("gold", 0)
        self.resources = faction_data.get("resources", {})
        self.influence = faction_data.get("influence", 0)
        self.members = faction_data.get("members", [])
        self.controlled_locations = faction_data.get("controlled_locations", [])
        self.allies = faction_data.get("allies", [])
        self.enemies = faction_data.get("enemies", [])
        self.preferred_locations = faction_data.get("preferred_locations", [])
        self.preferred_biomes = faction_data.get("preferred_biomes", [])
        self.available_quests = faction_data.get("available_quests", [])
        self.unacceptable_locations = faction_data.get("unacceptable_locations", [])
        
    def get_legal_actions(self) -> List[FactionAction]:
        """
        Get all legal actions in the current state.
        
        Returns:
            List of FactionAction objects representing possible actions
        """
        # Use cached actions if available
        if self._legal_actions is not None:
            return self._legal_actions
        
        actions = []
        
        # Add movement actions
        movement_actions = self._get_movement_actions()
        actions.extend(movement_actions)
        
        # Add trade actions
        trade_actions = self._get_trade_actions()
        actions.extend(trade_actions)
        
        # Add diplomacy actions
        diplomacy_actions = self._get_diplomacy_actions()
        actions.extend(diplomacy_actions)
        
        # Add recruitment actions if appropriate
        if self._can_recruit():
            recruitment_action = FactionAction(
                action_type="recruit",
                location_id=self.current_location_id
            )
            recruitment_action.gold_cost = 50 * (len(self.members) + 1)
            actions.append(recruitment_action)
        
        # Add outpost establishment if in a suitable location
        if self._can_establish_outpost():
            outpost_action = FactionAction(
                action_type="establish_outpost",
                location_id=self.current_location_id
            )
            outpost_action.gold_cost = 200
            outpost_action.resource_cost = {"wood": 50, "stone": 30}
            actions.append(outpost_action)
        
        # Add quest actions
        quest_actions = self._get_quest_actions()
        actions.extend(quest_actions)
        
        # Add rest action (stay in place)
        actions.append(FactionAction(
            action_type="rest",
            location_id=self.current_location_id
        ))
        
        # Calculate action scores based on faction state
        self._calculate_action_scores(actions)
        
        # Cache actions
        self._legal_actions = actions
        return actions
    
    def _get_movement_actions(self) -> List[FactionAction]:
        """
        Get possible movement actions based on the faction's current location.
        
        Returns:
            List of movement actions
        """
        actions = []
        
        # If we have a location graph, use it to find connected locations
        location_graph = self.world_data.get("location_graph", {})
        if self.current_location_id in location_graph:
            connected_locations = location_graph[self.current_location_id]
            
            for location_id in connected_locations:
                # Skip unacceptable locations
                if location_id in self.unacceptable_locations:
                    continue
                    
                # Create movement action
                action = FactionAction(
                    action_type="move",
                    location_id=location_id
                )
                
                # Cost depends on faction size
                action.gold_cost = 10 * len(self.members)
                actions.append(action)
        
        return actions
    
    def _get_trade_actions(self) -> List[FactionAction]:
        """
        Get possible trade actions at the current location.
        
        Returns:
            List of trade actions
        """
        actions = []
        
        # Get other factions or settlements at this location
        location_data = self.world_data.get("locations", {})
        if self.current_location_id in location_data:
            present_entities = location_data[self.current_location_id].get("entities", [])
            
            for entity_id in present_entities:
                # Skip self and enemies
                if entity_id == self.faction_id or entity_id in self.enemies:
                    continue
                
                # Get entity type (faction or settlement)
                entity_type = self._get_entity_type(entity_id)
                
                if entity_type in ["faction", "settlement"]:
                    action = FactionAction(
                        action_type="trade",
                        target_id=entity_id,
                        location_id=self.current_location_id
                    )
                    actions.append(action)
        
        return actions
    
    def _get_diplomacy_actions(self) -> List[FactionAction]:
        """
        Get possible diplomacy actions with other factions.
        
        Returns:
            List of diplomacy actions
        """
        actions = []
        
        # Get other factions at this location for direct diplomacy
        location_data = self.world_data.get("locations", {})
        if self.current_location_id in location_data:
            present_factions = [
                entity_id for entity_id in location_data[self.current_location_id].get("entities", [])
                if self._get_entity_type(entity_id) == "faction" and entity_id != self.faction_id
            ]
            
            for faction_id in present_factions:
                # Alliance action (if not already allies or enemies)
                if faction_id not in self.allies and faction_id not in self.enemies:
                    alliance_action = FactionAction(
                        action_type="diplomacy_alliance",
                        target_id=faction_id,
                        location_id=self.current_location_id
                    )
                    alliance_action.gold_cost = 100
                    alliance_action.influence_gain = 20
                    actions.append(alliance_action)
                
                # Peace action (if currently enemies)
                if faction_id in self.enemies:
                    peace_action = FactionAction(
                        action_type="diplomacy_peace",
                        target_id=faction_id,
                        location_id=self.current_location_id
                    )
                    peace_action.gold_cost = 200
                    actions.append(peace_action)
        
        return actions
    
    def _get_quest_actions(self) -> List[FactionAction]:
        """
        Get possible quest-related actions.
        
        Returns:
            List of quest actions
        """
        actions = []
        
        # Can only issue quests at controlled locations
        if self.current_location_id in self.controlled_locations:
            # Check if we have available quests
            for quest_id in self.available_quests:
                action = FactionAction(
                    action_type="issue_quest",
                    location_id=self.current_location_id,
                    target_id=quest_id
                )
                action.influence_gain = 10
                actions.append(action)
        
        return actions
    
    def _can_recruit(self) -> bool:
        """
        Check if the faction can recruit new members.
        
        Returns:
            True if recruitment is possible, False otherwise
        """
        # Can recruit if there's enough gold and at a settlement
        if self.gold < 50 * (len(self.members) + 1):
            return False
            
        # Check if current location is a settlement
        location_data = self.world_data.get("locations", {})
        if self.current_location_id in location_data:
            location_type = location_data[self.current_location_id].get("type")
            return location_type == "settlement"
            
        return False
    
    def _can_establish_outpost(self) -> bool:
        """
        Check if the faction can establish an outpost at current location.
        
        Returns:
            True if outpost establishment is possible, False otherwise
        """
        # Cannot establish outpost in existing controlled locations
        if self.current_location_id in self.controlled_locations:
            return False
            
        # Check if we have enough resources
        if self.gold < 200:
            return False
            
        if self.resources.get("wood", 0) < 50 or self.resources.get("stone", 0) < 30:
            return False
            
        # Check if current location is suitable
        location_data = self.world_data.get("locations", {})
        if self.current_location_id in location_data:
            # Check if already controlled by enemy faction
            controlled_by = location_data[self.current_location_id].get("controlled_by")
            if controlled_by and controlled_by in self.enemies:
                return False
                
            # Preferred locations are better for outposts
            return self.current_location_id in self.preferred_locations
            
        return False
    
    def _get_entity_type(self, entity_id: str) -> str:
        """
        Determine the type of an entity by its ID.
        
        Args:
            entity_id: The ID of the entity
            
        Returns:
            String representing entity type ("faction", "settlement", etc.)
        """
        # Check factions
        factions = self.world_data.get("factions", {})
        if entity_id in factions:
            return "faction"
            
        # Check settlements
        settlements = self.world_data.get("settlements", {})
        if entity_id in settlements:
            return "settlement"
            
        # Check traders
        traders = self.world_data.get("traders", {})
        if entity_id in traders:
            return "trader"
            
        return "unknown"
    
    def _calculate_action_scores(self, actions: List[FactionAction]) -> None:
        """
        Calculate scores for each action based on faction state and preferences.
        
        Args:
            actions: List of actions to score
        """
        for action in actions:
            score = 1.0  # Base score
            
            if action.action_type == "move":
                # Prefer preferred locations
                if action.location_id in self.preferred_locations:
                    score += 1.0
                
                # Prefer locations with preferred biomes
                location_data = self.world_data.get("locations", {})
                if action.location_id in location_data:
                    biome = location_data[action.location_id].get("biome")
                    if biome in self.preferred_biomes:
                        score += 0.5
                
                # Prefer locations with allies
                if action.location_id in self._get_ally_locations():
                    score += 0.5
                    
                # Avoid enemy locations unless we're strong
                if action.location_id in self._get_enemy_locations():
                    if len(self.members) > 10:
                        # Strong enough to challenge
                        score += 0.2
                    else:
                        # Too weak to risk conflict
                        score -= 1.0
            
            elif action.action_type == "trade":
                # Trading is generally beneficial
                score += 0.8
                
                # Trading with allies is preferred
                if action.target_id in self.allies:
                    score += 0.5
            
            elif action.action_type == "diplomacy_alliance":
                # Alliances are valuable for smaller factions
                if len(self.members) < 10:
                    score += 1.0
                
                # Alliances with strong factions are more valuable
                target_strength = self._get_faction_strength(action.target_id)
                score += target_strength * 0.1
            
            elif action.action_type == "diplomacy_peace":
                # Peace is valuable when we have many enemies
                if len(self.enemies) > 2:
                    score += 1.0
                
                # Peace with strong enemies is more valuable
                target_strength = self._get_faction_strength(action.target_id)
                score += target_strength * 0.2
            
            elif action.action_type == "recruit":
                # Recruiting is more valuable for smaller factions
                if len(self.members) < 5:
                    score += 1.5
                elif len(self.members) < 10:
                    score += 1.0
                else:
                    score += 0.5
            
            elif action.action_type == "establish_outpost":
                # Establishing outposts in preferred locations is valuable
                if action.location_id in self.preferred_locations:
                    score += 1.5
                
                # More valuable if we have few controlled locations
                if len(self.controlled_locations) < 3:
                    score += 1.0
                
                # Strategic value based on connections
                location_graph = self.world_data.get("location_graph", {})
                if action.location_id in location_graph:
                    connections = len(location_graph[action.location_id])
                    score += min(1.0, connections * 0.1)
            
            elif action.action_type == "issue_quest":
                # Quests increase influence
                score += 0.7
                
                # More valuable if we have low influence
                if self.influence < 50:
                    score += 0.5
            
            elif action.action_type == "rest":
                # Resting is a fallback option
                score = 0.3
            
            # Adjust score based on cost
            if action.gold_cost > 0:
                # Reduce score if gold cost is high relative to available gold
                if self.gold > 0:
                    cost_ratio = action.gold_cost / self.gold
                    if cost_ratio > 0.5:
                        score -= cost_ratio
            
            # Adjust for resource costs
            for resource, amount in action.resource_cost.items():
                if resource in self.resources and self.resources[resource] > 0:
                    # Reduce score if resource cost is high relative to available resources
                    cost_ratio = amount / self.resources[resource]
                    if cost_ratio > 0.5:
                        score -= cost_ratio * 0.5
            
            # Ensure minimum score
            action.score = max(0.1, score)
    
    def _get_ally_locations(self) -> List[str]:
        """
        Get locations where allies are present.
        
        Returns:
            List of location IDs
        """
        ally_locations = []
        
        for ally_id in self.allies:
            faction_location = self._get_faction_location(ally_id)
            if faction_location:
                ally_locations.append(faction_location)
        
        return ally_locations
    
    def _get_enemy_locations(self) -> List[str]:
        """
        Get locations where enemies are present.
        
        Returns:
            List of location IDs
        """
        enemy_locations = []
        
        for enemy_id in self.enemies:
            faction_location = self._get_faction_location(enemy_id)
            if faction_location:
                enemy_locations.append(faction_location)
        
        return enemy_locations
    
    def _get_faction_location(self, faction_id: str) -> Optional[str]:
        """
        Get the current location of a faction.
        
        Args:
            faction_id: The ID of the faction
            
        Returns:
            Location ID or None if not found
        """
        factions = self.world_data.get("factions", {})
        if faction_id in factions:
            return factions[faction_id].get("current_location_id")
        
        return None
    
    def _get_faction_strength(self, faction_id: str) -> float:
        """
        Calculate the relative strength of a faction.
        
        Args:
            faction_id: The ID of the faction
            
        Returns:
            Strength value (0.0-10.0)
        """
        factions = self.world_data.get("factions", {})
        if faction_id in factions:
            faction = factions[faction_id]
            
            # Base strength on number of members
            members = faction.get("members", [])
            member_strength = len(members) * 0.5
            
            # Add controlled locations
            controlled_locations = faction.get("controlled_locations", [])
            location_strength = len(controlled_locations) * 0.3
            
            # Add allies
            allies = faction.get("allies", [])
            ally_strength = len(allies) * 0.2
            
            return min(10.0, member_strength + location_strength + ally_strength)
        
        return 0.0
    
    def apply_action(self, action: FactionAction) -> 'FactionState':
        """
        Apply an action to this state and return the new state.
        
        Args:
            action: The action to apply
            
        Returns:
            A new FactionState resulting from the action
        """
        # Create a deep copy of the current state
        new_faction_data = copy.deepcopy(self.faction_data)
        new_state = FactionState(new_faction_data, copy.deepcopy(self.world_data))
        
        # Apply the action effect based on type
        if action.action_type == "move":
            # Update location
            new_state.faction_data["current_location_id"] = action.location_id
            new_state.current_location_id = action.location_id
            
            # Deduct gold cost
            if action.gold_cost > 0:
                new_state.faction_data["gold"] = max(0, new_state.gold - action.gold_cost)
                new_state.gold = new_state.faction_data["gold"]
        
        elif action.action_type == "trade":
            # Simple trade model: random resource gain and gold change
            # In a real implementation, this would involve specific resource exchanges
            
            # Generate some random resource changes
            resource_types = ["wood", "stone", "food", "iron"]
            for resource in resource_types:
                if resource not in new_state.faction_data["resources"]:
                    new_state.faction_data["resources"][resource] = 0
                
                # Random change (-10 to +20)
                change = random.randint(-10, 20)
                new_state.faction_data["resources"][resource] = max(0, new_state.faction_data["resources"][resource] + change)
            
            # Update resources cache
            new_state.resources = new_state.faction_data["resources"]
            
            # Random gold change (-50 to +100)
            gold_change = random.randint(-50, 100)
            new_state.faction_data["gold"] = max(0, new_state.gold + gold_change)
            new_state.gold = new_state.faction_data["gold"]
            
            # Small influence gain
            influence_gain = random.randint(1, 5)
            new_state.faction_data["influence"] = new_state.influence + influence_gain
            new_state.influence = new_state.faction_data["influence"]
        
        elif action.action_type == "diplomacy_alliance":
            # Add the target to allies if not already there
            if action.target_id not in new_state.allies:
                if "allies" not in new_state.faction_data:
                    new_state.faction_data["allies"] = []
                new_state.faction_data["allies"].append(action.target_id)
                new_state.allies = new_state.faction_data["allies"]
            
            # Remove from enemies if present
            if action.target_id in new_state.enemies:
                new_state.faction_data["enemies"].remove(action.target_id)
                new_state.enemies = new_state.faction_data["enemies"]
            
            # Deduct gold cost
            if action.gold_cost > 0:
                new_state.faction_data["gold"] = max(0, new_state.gold - action.gold_cost)
                new_state.gold = new_state.faction_data["gold"]
            
            # Gain influence
            if action.influence_gain > 0:
                new_state.faction_data["influence"] = new_state.influence + action.influence_gain
                new_state.influence = new_state.faction_data["influence"]
        
        elif action.action_type == "diplomacy_peace":
            # Remove the target from enemies if present
            if action.target_id in new_state.enemies:
                new_state.faction_data["enemies"].remove(action.target_id)
                new_state.enemies = new_state.faction_data["enemies"]
            
            # Deduct gold cost
            if action.gold_cost > 0:
                new_state.faction_data["gold"] = max(0, new_state.gold - action.gold_cost)
                new_state.gold = new_state.faction_data["gold"]
        
        elif action.action_type == "recruit":
            # Add a new member with a random ID
            new_member_id = f"member_{random.randint(1000, 9999)}"
            if "members" not in new_state.faction_data:
                new_state.faction_data["members"] = []
            new_state.faction_data["members"].append(new_member_id)
            new_state.members = new_state.faction_data["members"]
            
            # Deduct gold cost
            if action.gold_cost > 0:
                new_state.faction_data["gold"] = max(0, new_state.gold - action.gold_cost)
                new_state.gold = new_state.faction_data["gold"]
        
        elif action.action_type == "establish_outpost":
            # Add the location to controlled locations
            if action.location_id not in new_state.controlled_locations:
                if "controlled_locations" not in new_state.faction_data:
                    new_state.faction_data["controlled_locations"] = []
                new_state.faction_data["controlled_locations"].append(action.location_id)
                new_state.controlled_locations = new_state.faction_data["controlled_locations"]
            
            # Deduct gold cost
            if action.gold_cost > 0:
                new_state.faction_data["gold"] = max(0, new_state.gold - action.gold_cost)
                new_state.gold = new_state.faction_data["gold"]
            
            # Deduct resource costs
            for resource, amount in action.resource_cost.items():
                if resource in new_state.faction_data["resources"]:
                    new_state.faction_data["resources"][resource] = max(0, new_state.faction_data["resources"][resource] - amount)
            
            # Update resources cache
            new_state.resources = new_state.faction_data["resources"]
            
            # Gain influence
            new_state.faction_data["influence"] = new_state.influence + 10
            new_state.influence = new_state.faction_data["influence"]
        
        elif action.action_type == "issue_quest":
            # Remove the quest from available quests
            if action.target_id in new_state.available_quests:
                new_state.faction_data["available_quests"].remove(action.target_id)
                new_state.available_quests = new_state.faction_data["available_quests"]
            
            # Gain influence
            if action.influence_gain > 0:
                new_state.faction_data["influence"] = new_state.influence + action.influence_gain
                new_state.influence = new_state.faction_data["influence"]
        
        elif action.action_type == "rest":
            # Resting - nothing happens except time passes
            pass
        
        # Clear cached actions
        new_state._legal_actions = None
        
        return new_state
    
    def is_terminal(self) -> bool:
        """
        Check if this is a terminal state (simulation should end).
        
        Returns:
            True if terminal, False otherwise
        """
        # For factions, a simulation might end if:
        
        # 1. Faction has been eliminated (no members)
        if len(self.members) <= 0:
            return True
        
        # 2. Faction has achieved dominance (many controlled locations)
        if len(self.controlled_locations) >= 10:
            return True
        
        # 3. Faction has very high influence
        if self.influence >= 500:
            return True
        
        return False
    
    def get_reward(self) -> float:
        """
        Calculate reward value for this state.
        
        Returns:
            Float reward value (higher is better)
        """
        reward = 0.0
        
        # Reward for controlled locations
        reward += len(self.controlled_locations) * 10.0
        
        # Reward for members
        reward += len(self.members) * 5.0
        
        # Reward for allies
        reward += len(self.allies) * 3.0
        
        # Reward for influence
        reward += self.influence * 0.1
        
        # Reward for gold
        reward += self.gold * 0.05
        
        # Reward for resources
        resource_value = 0
        for resource, amount in self.resources.items():
            resource_value += amount
        reward += resource_value * 0.02
        
        # Penalty for enemies
        reward -= len(self.enemies) * 2.0
        
        # Reward for being in preferred locations
        if self.current_location_id in self.preferred_locations:
            reward += 5.0
        
        # Reward for being in preferred biomes
        location_data = self.world_data.get("locations", {})
        if self.current_location_id in location_data:
            biome = location_data[self.current_location_id].get("biome")
            if biome in self.preferred_biomes:
                reward += 3.0
        
        return reward
    
    def __str__(self) -> str:
        """String representation of the state."""
        return f"{self.faction_name} ({self.faction_type}) at {self.current_location_id} with {len(self.members)} members, {len(self.controlled_locations)} controlled locations, {self.influence} influence"
        
    # Method for compatibility with the FactionEntity interface
    @classmethod
    def from_faction_entity(cls, faction, world_info=None):
        """
        Create a FactionState from a Faction entity.
        
        Args:
            faction: The faction entity
            world_info: Optional world information
            
        Returns:
            FactionState: A new state object representing the faction
        """
        # Convert faction entity to data dictionary
        faction_data = faction.to_dict() if hasattr(faction, 'to_dict') else {}
        
        # If to_dict isn't available, get properties directly
        if not faction_data and hasattr(faction, 'get_property'):
            faction_data = {
                "id": getattr(faction, 'id', None),
                "name": faction.get_property("name"),
                "faction_type": faction.get_property("faction_type", "minor"),
                "current_location_id": faction.get_property("current_location_id"),
                "gold": faction.get_property("gold", 0),
                "resources": faction.get_property("resources", {}),
                "influence": faction.get_property("influence", 0),
                "members": faction.get_property("members", []),
                "controlled_locations": faction.get_property("controlled_locations", []),
                "allies": faction.get_property("allies", []),
                "enemies": faction.get_property("enemies", []),
                "preferred_locations": faction.get_property("preferred_locations", []),
                "preferred_biomes": faction.get_property("preferred_biomes", []),
                "available_quests": faction.get_property("available_quests", []),
                "unacceptable_locations": faction.get_property("unacceptable_locations", [])
            }
            
        return cls(faction_data, world_info or {})