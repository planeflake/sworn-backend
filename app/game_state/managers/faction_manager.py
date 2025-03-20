"""
Faction Manager Class Template
==============================

This class manages the lifecycle of Faction objects in the game, handling their loading,
saving, and caching. It serves as the primary interface between your application and 
faction data persistence.

The FactionManager:
1. Acts as a factory for Faction instances
2. Handles database interactions for factions
3. Maintains a cache of loaded factions to improve performance
4. Provides methods for faction-related game operations

Usage:
- Create one FactionManager instance connected to your database
- Use it to retrieve, create, and save faction objects
- Never create Faction objects directly; always use the manager
"""


class FactionManager:
    def __init__(self, database_interface):
        """
        Initialize the FactionManager with a database connection.
        
        Args:
            database_interface: An object that provides database access methods
                                (must implement get_faction, save_faction, etc.)
        """
        self.db = database_interface
        self.factions = {}  # Cache of loaded factions (faction_id -> Faction)
        self.auto_save = True  # Whether to automatically save dirty factions

    #----------------------------------------
    # Faction Loading Methods
    #----------------------------------------
    
    async def load_faction(self, faction_id):
        """
        Load a faction from the database or cache.
        
        API Usage: All faction-related endpoints
        Internal Usage: Game logic requiring faction data
        
        Args:
            faction_id (str): ID of the faction to load
            
        Returns:
            Faction: The loaded faction object or None if not found
        """
        # Return from cache if available
        if faction_id in self.factions:
            return self.factions[faction_id]
            
        # Otherwise load from database
        faction_data = await self.db.get_faction(faction_id)
        if not faction_data:
            return None
            
        # Create faction instance and cache it
        from ..entities.faction import Faction  # Import here to avoid circular imports
        faction = Faction.from_dict(faction_data)
        self.factions[faction_id] = faction
        return faction
    
    async def get_all_factions(self):
        """
        Load all factions from the database.
        
        API Usage: Admin faction list, world map data
        Internal Usage: World initialization, global faction processing
        
        Returns:
            list: List of all Faction objects
        """
        # Get all faction data from database
        faction_data_list = await self.db.get_all_factions()
        
        # Import faction class
        from ..entities.faction import Faction
        
        # Create and cache faction objects
        for data in faction_data_list:
            faction_id = data["id"]
            if faction_id not in self.factions:
                faction = Faction.from_dict(data)
                self.factions[faction_id] = faction
                
        return list(self.factions.values())
    
    async def get_factions_by_territory(self, territory_id):
        """
        Get all factions that control a specific territory.
        
        API Usage: Territory info endpoints
        Internal Usage: Territory disputes, regional events
        
        Args:
            territory_id (str): ID of the territory to check
            
        Returns:
            list: Faction objects controlling this territory
        """
        # This could be optimized with a specific DB query
        # but for simplicity we'll check all factions
        factions = await self.get_all_factions()
        return [f for f in factions if territory_id in f.territories]
    
    async def get_factions_by_relation(self, faction_id, min_relation=0):
        """
        Get factions with at least the specified relation to the given faction.
        
        API Usage: Faction alliance info, diplomatic status
        Internal Usage: Determining potential allies for conflicts
        
        Args:
            faction_id (str): ID of the reference faction
            min_relation (int): Minimum relation value (default 0)
            
        Returns:
            list: Faction objects with sufficient relation
        """
        reference_faction = await self.load_faction(faction_id)
        if not reference_faction:
            return []
            
        related_faction_ids = [
            fid for fid, relation in reference_faction.relations.items()
            if relation >= min_relation
        ]
        
        related_factions = []
        for fid in related_faction_ids:
            faction = await self.load_faction(fid)
            if faction:
                related_factions.append(faction)
                
        return related_factions
    
    #----------------------------------------
    # Faction Creation and Management
    #----------------------------------------
    
    async def create_faction(self, faction_id, name, description):
        """
        Create a new faction and save it to the database.
        
        API Usage: Admin faction creation endpoint
        Internal Usage: World generation, dynamic faction creation
        
        Args:
            faction_id (str): Unique ID for the new faction
            name (str): Display name of the faction
            description (str): Brief description of the faction
            
        Returns:
            Faction: The newly created faction, or None if ID already exists
        """
        # Check if faction already exists
        existing = await self.load_faction(faction_id)
        if existing:
            return None
            
        # Create new faction
        from ..entities.faction import Faction
        faction = Faction(faction_id)
        faction.set_basic_info(name, description)
        
        # Save to database
        await self.save_faction(faction)
        return faction
    
    async def delete_faction(self, faction_id):
        """
        Delete a faction from the database.
        
        API Usage: Admin faction management
        Internal Usage: Faction elimination events
        
        Args:
            faction_id (str): ID of the faction to delete
            
        Returns:
            bool: True if successful, False if faction not found
        """
        # Remove from cache if present
        if faction_id in self.factions:
            del self.factions[faction_id]
            
        # Delete from database
        success = await self.db.delete_faction(faction_id)
        return success
    
    #----------------------------------------
    # Faction Saving Methods
    #----------------------------------------
    
    async def save_faction(self, faction):
        """
        Save a faction to the database.
        
        API Usage: After any faction modification
        Internal Usage: After game events that change faction state
        
        Args:
            faction: The faction object to save
            
        Returns:
            bool: True if save was successful
        """
        # Convert to dictionary
        faction_data = faction.to_dict()
        
        # Save to database
        success = await self.db.save_faction(faction_data)
        
        # Update cache and mark clean if successful
        if success:
            self.factions[faction.id] = faction
            faction.mark_clean()
            
        return success
    
    async def save_all_factions(self):
        """
        Save all modified factions in the cache.
        
        API Usage: System maintenance endpoints
        Internal Usage: Periodic world state saving
        
        Returns:
            int: Number of factions saved
        """
        save_count = 0
        for faction in self.factions.values():
            if faction.is_dirty():
                success = await self.save_faction(faction)
                if success:
                    save_count += 1
                    
        return save_count
    
    #----------------------------------------
    # Faction State Management
    #----------------------------------------
    
    async def get_faction_state(self, faction_id):
        """
        Get a faction state object for AI decision-making.
        
        Internal Usage: Faction AI worker, MCTS decision system
        
        Args:
            faction_id (str): ID of the faction
            
        Returns:
            FactionState: State object for the faction, or None if not found
        """
        faction = await self.load_faction(faction_id)
        if not faction:
            return None
            
        from ..states.faction_state import FactionState
        return FactionState(faction)
    
    #----------------------------------------
    # Cache Management
    #----------------------------------------
    
    def invalidate_cache(self, faction_id=None):
        """
        Invalidate the faction cache, forcing reload from database.
        
        API Usage: Admin cache management
        Internal Usage: After external database changes
        
        Args:
            faction_id (str, optional): Specific faction to invalidate, or all if None
        """
        if faction_id is None:
            # Invalidate all factions
            # (but save dirty ones first if auto_save is enabled)
            if self.auto_save:
                for faction in self.factions.values():
                    if faction.is_dirty():
                        self.db.save_faction_sync(faction.to_dict())  # Synchronous version
            self.factions = {}
        else:
            # Invalidate specific faction
            if faction_id in self.factions:
                if self.auto_save and self.factions[faction_id].is_dirty():
                    self.db.save_faction_sync(self.factions[faction_id].to_dict())
                del self.factions[faction_id]
    
    #----------------------------------------
    # Faction Interaction Methods
    #----------------------------------------
    
    async def update_faction_relations(self, faction_id, other_faction_id, change):
        """
        Update relations between two factions.
        
        This handles updating both sides of the relationship and saving changes.
        
        API Usage: Diplomacy endpoints, quest outcomes
        Internal Usage: World events, faction AI actions
        
        Args:
            faction_id (str): First faction ID
            other_faction_id (str): Second faction ID
            change (int): Amount to change relation by
            
        Returns:
            tuple: (new_relation1, new_relation2) or None if error
        """
        # Load both factions
        faction1 = await self.load_faction(faction_id)
        faction2 = await self.load_faction(other_faction_id)
        
        if not faction1 or not faction2:
            return None
            
        # Update relations
        current1 = faction1.get_relation(other_faction_id)
        current2 = faction2.get_relation(faction_id)
        
        new_relation1 = max(-100, min(100, current1 + change))
        new_relation2 = max(-100, min(100, current2 + change))
        
        faction1.set_relation(other_faction_id, new_relation1)
        faction2.set_relation(faction_id, new_relation2)
        
        # Save changes
        await self.save_faction(faction1)
        await self.save_faction(faction2)
        
        return (new_relation1, new_relation2)
    
    async def transfer_territory(self, territory_id, from_faction_id, to_faction_id):
        """
        Transfer a territory from one faction to another.
        
        API Usage: Conquest results, diplomatic agreement outcomes
        Internal Usage: Faction AI territorial decisions, conflict resolution
        
        Args:
            territory_id (str): ID of the territory to transfer
            from_faction_id (str): ID of the faction losing the territory
            to_faction_id (str): ID of the faction gaining the territory
            
        Returns:
            bool: True if transfer was successful
        """
        # Load factions
        from_faction = await self.load_faction(from_faction_id)
        to_faction = await self.load_faction(to_faction_id)
        
        if not from_faction or not to_faction:
            return False
            
        # Check if from_faction actually controls the territory
        if territory_id not in from_faction.territories:
            return False
            
        # Transfer territory
        from_faction.remove_territory(territory_id)
        to_faction.add_territory(territory_id)
        
        # Save changes
        await self.save_faction(from_faction)
        await self.save_faction(to_faction)
        
        return True