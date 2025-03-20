"""
Faction Class Template
======================

This class represents a faction entity in the game world. It contains all data structures
and methods for interacting with factions, both through the API and for internal game logic.

The Faction class serves as:
1. A data model for faction information
2. A container for faction-related business logic
3. An interface for both API endpoints and background game processes

Usage:
- Create instances via FactionManager, not directly
- Modify faction data through provided methods, not by changing attributes directly
- Always save changes through FactionManager after modifications
"""


class Faction:
    def __init__(self, faction_id):
        """
        Initialize a faction with the given ID.
        
        The rest of the faction data should be loaded from the database.
        Don't create factions directly; use FactionManager.load_faction() instead.
        
        Args:
            faction_id (str): Unique identifier for this faction
        """
        self.id = faction_id
        
        # Basic information
        self.name = None  # Name of the faction
        self.description = None  # Brief description of the faction
        
        # Reputation system
        self.reputation_levels = {}  # Dict mapping threshold values to reputation tiers
        
        # Relations with other factions
        self.relations = {}  # Dict mapping faction_id to relation value (-100 to 100)
        
        # Territory control
        self.territories = []  # List of territory IDs controlled by this faction
        
        # Resources and economy
        self.resources = {}  # Dict mapping resource_type to amount
        
        # NPCs and members
        self.members = []  # List of NPC IDs affiliated with this faction
        
        # Quest offerings
        self.available_quests = []  # List of quest IDs this faction can offer
        
        # Faction policies and behavior
        self.policies = {}  # Dict of policy settings that influence faction behavior
        
        # Internal state tracking
        self._dirty = False  # Flag to indicate unsaved changes

    #----------------------------------------
    # Basic Information Methods
    #----------------------------------------
    
    def set_basic_info(self, name, description):
        """
        Set the basic information for this faction.
        
        Args:
            name (str): The display name of the faction
            description (str): A brief description of the faction
        """
        self.name = name
        self.description = description
        self._dirty = True
    
    #----------------------------------------
    # Reputation System Methods
    #----------------------------------------
    
    def add_reputation_level(self, threshold, label, benefits=None):
        """
        Define a reputation level with associated benefits.
        
        API Usage: Admin endpoints for configuring reputation levels
        Internal Usage: Initial game setup, faction modification events
        
        Args:
            threshold (int): The reputation value threshold for this level
            label (str): Display name for this reputation level
            benefits (dict, optional): Benefits granted at this level
        """
        if benefits is None:
            benefits = {}
        self.reputation_levels[threshold] = {
            "label": label,
            "benefits": benefits
        }
        self._dirty = True
    
    def get_reputation_tier(self, reputation_value):
        """
        Get the current reputation tier based on a reputation value.
        
        API Usage: Player reputation status endpoint
        Internal Usage: Determining player benefits, quest availability
        
        Args:
            reputation_value (int): The player's reputation with this faction
            
        Returns:
            dict: The reputation tier info or None if no tier applies
        """
        current_tier = None
        for threshold in sorted(self.reputation_levels.keys()):
            if reputation_value >= threshold:
                current_tier = self.reputation_levels[threshold]
            else:
                break
        return current_tier
    
    #----------------------------------------
    # Inter-Faction Relations Methods
    #----------------------------------------
    
    def set_relation(self, other_faction_id, value):
        """
        Set relation value with another faction.
        
        API Usage: Admin faction management, faction quest rewards
        Internal Usage: Faction AI decision making, world events
        
        Args:
            other_faction_id (str): ID of the other faction
            value (int): Relation value from -100 (enemies) to 100 (allies)
        """
        self.relations[other_faction_id] = max(-100, min(100, value))
        self._dirty = True
    
    def get_relation(self, other_faction_id):
        """
        Get current relation value with another faction.
        
        API Usage: Player faction info endpoint
        Internal Usage: Determining faction behavior toward others
        
        Args:
            other_faction_id (str): ID of the other faction
            
        Returns:
            int: Relation value from -100 to 100, 0 if not set
        """
        return self.relations.get(other_faction_id, 0)
    
    def get_allied_factions(self, min_relation=50):
        """
        Get list of factions this faction is allied with.
        
        API Usage: Faction status endpoints
        Internal Usage: Determining joint faction actions, territory defense
        
        Args:
            min_relation (int): Minimum relation value to consider as allied
            
        Returns:
            list: List of faction IDs considered allies
        """
        return [f_id for f_id, relation in self.relations.items() 
                if relation >= min_relation]
    
    #----------------------------------------
    # Territory Control Methods
    #----------------------------------------
    
    def add_territory(self, territory_id):
        """
        Add a territory to faction control.
        
        API Usage: Faction conquest results, admin territory management
        Internal Usage: Faction expansion AI, conflict resolution
        
        Args:
            territory_id (str): ID of the territory to add
        """
        if territory_id not in self.territories:
            self.territories.append(territory_id)
            self._dirty = True
    
    def remove_territory(self, territory_id):
        """
        Remove a territory from faction control.
        
        API Usage: Faction conquest results, admin territory management
        Internal Usage: Faction AI territory management, conflict resolution
        
        Args:
            territory_id (str): ID of the territory to remove
        """
        if territory_id in self.territories:
            self.territories.remove(territory_id)
            self._dirty = True
    
    #----------------------------------------
    # Resource Management Methods
    #----------------------------------------
    
    def set_resource(self, resource_type, amount):
        """
        Set a resource amount for this faction.
        
        API Usage: Admin resource management
        Internal Usage: Resource generation, consumption, trading
        
        Args:
            resource_type (str): Type of resource
            amount (int/float): Amount of the resource
        """
        self.resources[resource_type] = amount
        self._dirty = True
    
    def modify_resource(self, resource_type, delta):
        """
        Change a resource amount by the given delta.
        
        API Usage: Quest rewards, faction actions
        Internal Usage: Periodic resource updates, faction expenses
        
        Args:
            resource_type (str): Type of resource
            delta (int/float): Amount to change (positive or negative)
            
        Returns:
            bool: True if successful, False if insufficient resources
        """
        current = self.resources.get(resource_type, 0)
        new_amount = current + delta
        
        if new_amount < 0:
            return False
            
        self.resources[resource_type] = new_amount
        self._dirty = True
        return True
    
    #----------------------------------------
    # Quest Management Methods
    #----------------------------------------
    
    def add_quest(self, quest_id):
        """
        Add a quest to the faction's available quests.
        
        API Usage: Admin quest management
        Internal Usage: Dynamic quest generation
        
        Args:
            quest_id (str): ID of the quest to add
        """
        if quest_id not in self.available_quests:
            self.available_quests.append(quest_id)
            self._dirty = True
    
    def get_available_quests(self, player_reputation):
        """
        Get quests available to a player based on their reputation.
        
        API Usage: Player quest discovery endpoint
        Internal Usage: Quest offering mechanics
        
        Args:
            player_reputation (int): Player's reputation with this faction
            
        Returns:
            list: List of available quest IDs
        """
        tier = self.get_reputation_tier(player_reputation)
        if not tier or not tier.get("benefits", {}).get("quest_access", False):
            return []
            
        return self.available_quests
    
    #----------------------------------------
    # Faction Policy Methods
    #----------------------------------------
    
    def set_policy(self, policy_name, value):
        """
        Set a faction policy value.
        
        API Usage: Admin faction management
        Internal Usage: Faction AI decision making
        
        Args:
            policy_name (str): Name of the policy
            value: Value for the policy (type depends on policy)
        """
        self.policies[policy_name] = value
        self._dirty = True
    
    #----------------------------------------
    # Serialization Methods
    #----------------------------------------
    
    def to_dict(self):
        """
        Convert faction to dictionary for storage.
        
        Returns:
            dict: Dictionary representation of this faction
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "reputation_levels": self.reputation_levels,
            "relations": self.relations,
            "territories": self.territories,
            "resources": self.resources,
            "members": self.members,
            "available_quests": self.available_quests,
            "policies": self.policies
        }
    
    @classmethod
    def from_dict(cls, data):
        """
        Create faction from dictionary data.
        
        Args:
            data (dict): Dictionary containing faction data
            
        Returns:
            Faction: New faction instance
        """
        faction = cls(faction_id=data["id"])
        faction.name = data.get("name")
        faction.description = data.get("description")
        faction.reputation_levels = data.get("reputation_levels", {})
        faction.relations = data.get("relations", {})
        faction.territories = data.get("territories", [])
        faction.resources = data.get("resources", {})
        faction.members = data.get("members", [])
        faction.available_quests = data.get("available_quests", [])
        faction.policies = data.get("policies", {})
        return faction
    
    #----------------------------------------
    # State Management Methods
    #----------------------------------------
    
    def is_dirty(self):
        """
        Check if this faction has unsaved changes.
        
        Returns:
            bool: True if unsaved changes exist
        """
        return self._dirty
    
    def mark_clean(self):
        """
        Mark this faction as having no unsaved changes.
        Called by FactionManager after saving.
        """
        self._dirty = False