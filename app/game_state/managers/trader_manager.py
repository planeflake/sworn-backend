from app.ai.mcts.states.trader_state import TraderState
from sqlalchemy import Column, String, Text, Table, MetaData
from sqlalchemy import select, insert, update, delete
from sqlalchemy.orm import Session
from database.connection import get_db
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Union
import logging as logger
import random
import json
import uuid

from ..entities.trader import Trader  # Using your original Trader class unchanged

# Pydantic model just for database operations
class TraderDB(BaseModel):
    """Database model for Trader table"""
    trader_id: str
    name: Optional[str] = None
    location_id: Optional[str] = None
    data: str  # JSON string of trader data


class TraderManager:
    def __init__(self):
        """Initialize the TraderManager."""
        self.traders = {}  # Dictionary to store loaded traders by ID
        self._setup_db_metadata()
        logger.info("TraderManager initialized")
    
    def _setup_db_metadata(self):
        """Set up SQLAlchemy metadata for traders table."""
        self.metadata = MetaData()
        self.traders_table = Table(
            'traders', 
            self.metadata,
            Column('trader_id', String(36), primary_key=True),
            Column('name', String(100)),
            Column('location_id', String(36)),
            Column('data', Text)
        )
    
    def create_trader(self, name, description=None):
        """
        Create a new trader with a unique ID.
        
        Args:
            name (str): The trader's name
            description (str): Optional description for the trader
            
        Returns:
            Trader: The newly created trader instance
        """
        # Generate a unique ID for the new trader
        trader_id = str(uuid.uuid4())
        
        # Create a new Trader instance
        trader = Trader(trader_id)
        trader.set_basic_info(name, description or f"A trader named {name}")
        
        # Add the trader to our local cache
        self.traders[trader_id] = trader
        
        # Save the trader to the database
        self.save_trader(trader)
        
        logger.info(f"Created new trader: {name} (ID: {trader_id})")
        return trader
    
    def load_trader(self, trader_id):
        """
        Load a trader from the database.
        
        Args:
            trader_id (str): The ID of the trader to load
            
        Returns:
            Trader: The loaded trader instance, or None if not found
        """
        # Check if the trader is already loaded
        if trader_id in self.traders:
            return self.traders[trader_id]
        
        # If not, load it from the database
        db = get_db()
        with Session(db) as session:
            stmt = select(self.traders_table).where(self.traders_table.c.trader_id == trader_id)
            result = session.execute(stmt).first()
            
            if result is None:
                logger.warning(f"Trader not found: {trader_id}")
                return None
            
            # Deserialize the trader data
            trader_data = json.loads(result.data)
            trader = Trader.from_dict(trader_data)
            
            # Cache the trader
            self.traders[trader_id] = trader
            
            logger.info(f"Loaded trader: {trader.name} (ID: {trader_id})")
            return trader
    
    def save_trader(self, trader):
        """
        Save a trader to the database.
        
        Args:
            trader (Trader): The trader instance to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not trader.is_dirty():
            # No changes to save
            return True
        
        # Convert the trader to a JSON string
        trader_dict = trader.to_dict()
        trader_data = json.dumps(trader_dict)
        
        # Create a Pydantic model for database operations
        trader_db = TraderDB(
            trader_id=trader.trader_id,
            name=trader.name,
            location_id=trader.current_location_id,
            data=trader_data
        )
        
        # Save to database
        db = get_db()
        with Session(db) as session:
            try:
                # Check if the trader already exists
                stmt = select(self.traders_table).where(self.traders_table.c.trader_id == trader.trader_id)
                exists = session.execute(stmt).first() is not None
                
                if exists:
                    # Update existing trader
                    stmt = update(self.traders_table).where(
                        self.traders_table.c.trader_id == trader.trader_id
                    ).values(
                        name=trader_db.name,
                        location_id=trader_db.location_id,
                        data=trader_db.data
                    )
                    session.execute(stmt)
                else:
                    # Insert new trader
                    stmt = insert(self.traders_table).values(
                        trader_id=trader_db.trader_id,
                        name=trader_db.name,
                        location_id=trader_db.location_id,
                        data=trader_db.data
                    )
                    session.execute(stmt)
                
                session.commit()
                
                # Mark the trader as clean (no unsaved changes)
                trader.mark_clean()
                
                logger.info(f"Saved trader: {trader.name} (ID: {trader.trader_id})")
                return True
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to save trader {trader.trader_id}: {str(e)}")
                return False
    
    def get_all_traders(self):
        """
        Get all traders from the database.
        
        Returns:
            list: List of all trader instances
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.traders_table.c.trader_id)
            results = session.execute(stmt).fetchall()
            
            traders = []
            for result in results:
                trader_id = result[0]
                trader = self.load_trader(trader_id)
                if trader:
                    traders.append(trader)
            
            return traders
    
    def get_traders_at_location(self, location_id):
        """
        Get all traders at a specific location.
        
        Args:
            location_id (str): The ID of the location
            
        Returns:
            list: List of trader instances at the location
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.traders_table.c.trader_id).where(self.traders_table.c.location_id == location_id)
            results = session.execute(stmt).fetchall()
            
            traders = []
            for result in results:
                trader_id = result[0]
                trader = self.load_trader(trader_id)
                if trader:
                    traders.append(trader)
            
            return traders
    
    def delete_trader(self, trader_id):
        """
        Delete a trader from the database.
        
        Args:
            trader_id (str): The ID of the trader to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Remove from cache if present
        if trader_id in self.traders:
            del self.traders[trader_id]
        
        # Delete from database
        db = get_db()
        with Session(db) as session:
            try:
                stmt = delete(self.traders_table).where(self.traders_table.c.trader_id == trader_id)
                session.execute(stmt)
                session.commit()
                logger.info(f"Deleted trader: {trader_id}")
                return True
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to delete trader {trader_id}: {str(e)}")
                return False
    
    def update_trader_location(self, trader_id, location_id):
        """
        Update a trader's current location.
        
        Args:
            trader_id (str): The ID of the trader
            location_id (str): The new location ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        trader = self.load_trader(trader_id)
        if not trader:
            logger.warning(f"Cannot update location: Trader not found: {trader_id}")
            return False
        
        trader.set_location(location_id, "current")
        return self.save_trader(trader)
    
    def process_trader_decisions(self):
        """
        Process decisions for all active traders (like movement, trade, etc.)
        
        This method would be called during game updates.
        """
        all_traders = self.get_all_traders()
        
        for trader in all_traders:
            self._process_single_trader_decision(trader)
    
    def _process_single_trader_decision(self, trader):
        """
        Process decisions for a single trader.
        
        Args:
            trader (Trader): The trader to process
        """
        # Check if trader is moving to a destination
        if trader.destination_id and trader.destination_id != trader.current_location_id:
            # In a real implementation, you'd calculate travel time, check for events, etc.
            # For now, we'll just move the trader instantly
            logger.info(f"Trader {trader.name} moving to {trader.destination_id}")
            trader.set_location(trader.destination_id, "current")
            trader.set_location(None, "destination")  # Clear the destination
            self.save_trader(trader)
        else:
            # Trader is staying at current location
            # Here you'd implement other behaviors like:
            # - Deciding to move somewhere else
            # - Trading with local markets
            # - Generating new quests
            # - Etc.
            
            # For example, randomly decide to move to a new location
            self._maybe_choose_new_destination(trader)
    
    def _maybe_choose_new_destination(self, trader):
        """
        Potentially choose a new destination for the trader.
        
        This is a simple example - in a real game you'd use more sophisticated
        decision making based on the trader's preferences, etc.
        
        Args:
            trader (Trader): The trader to choose a destination for
        """
        # 10% chance to decide to move
        if random.random() < 0.1:
            # Get possible destinations (in a real game, get from database)
            # This is placeholder logic
            possible_destinations = self._get_potential_destinations(trader)
            
            if possible_destinations:
                new_destination = random.choice(possible_destinations)
                trader.set_location(new_destination, "destination")
                logger.info(f"Trader {trader.name} decided to travel to {new_destination}")
                self.save_trader(trader)
    
    def _get_potential_destinations(self, trader):
        """
        Get potential destinations for a trader.
        
        Args:
            trader (Trader): The trader to find destinations for
            
        Returns:
            list: List of potential destination IDs
        """
        # In a real implementation, you would:
        # 1. Query the database for connected locations
        # 2. Filter based on trader preferences
        # 3. Consider distance, safety, trade opportunities, etc.
        
        # For now, we'll return a placeholder list
        db = get_db()
        with Session(db) as session:
            # Define settlements table
            settlements = Table(
                'settlements', 
                self.metadata,
                Column('settlement_id', String(36), primary_key=True)
            )
            
            # Query for settlements
            stmt = select(settlements.c.settlement_id).where(
                settlements.c.settlement_id != trader.current_location_id
            ).limit(5)
            
            results = session.execute(stmt).fetchall()
            return [row[0] for row in results]
    
    def save_all_traders(self):
        """
        Save all loaded traders to the database.
        
        Returns:
            bool: True if all saves were successful
        """
        success = True
        for trader in self.traders.values():
            if trader.is_dirty():
                if not self.save_trader(trader):
                    success = False
        
        return success
    
    def get_trader_by_name(self, name):
        """
        Find a trader by name.
        
        Args:
            name (str): The name to search for
            
        Returns:
            Trader: The trader with the given name, or None if not found
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.traders_table.c.trader_id).where(self.traders_table.c.name == name)
            result = session.execute(stmt).first()
            
            if result:
                return self.load_trader(result[0])
            return None
    
    def get_trader_count(self):
        """
        Get the total number of traders.
        
        Returns:
            int: The total count of traders
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.traders_table)
            result = session.execute(stmt).all()
            return len(result)
    
    def generate_random_trader(self, location_id=None):
        """
        Generate a random trader for testing or populating the world.
        
        Args:
            location_id (str, optional): Initial location for the trader
            
        Returns:
            Trader: The newly created trader
        """
        # Sample names for random generation
        first_names = ["Thorne", "Elara", "Garrick", "Lyra", "Rowan", "Seraphina", 
                      "Quill", "Vex", "Zephyr", "Nova"]
        last_names = ["Ironwood", "Silverleaf", "Nightshade", "Frostborn", "Emberforge", 
                     "Stormchaser", "Wildborne", "Shadowveil", "Moonshadow", "Starweaver"]
        
        # Generate random name
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        
        # Generate description
        descriptions = [
            "A cautious trader with a keen eye for valuable artifacts",
            "Known for fair deals and extensive knowledge of rare herbs",
            "A boisterous merchant with connections in every major city",
            "Quiet and reserved, but their goods are always of the highest quality",
            "A shrewd negotiator with a mysterious past"
        ]
        description = random.choice(descriptions)
        
        # Create the trader
        trader = self.create_trader(name, description)
        
        # Add random resources
        resources = ["gold", "silver", "iron", "herbs", "cloth", "gems", "food", "spices"]
        for _ in range(random.randint(3, 6)):
            resource = random.choice(resources)
            amount = random.randint(5, 50)
            trader.add_resource(resource, amount)
        
        # Set location if provided
        if location_id:
            trader.set_location(location_id, "current")
        
        # Add random preferred biomes
        biomes = ["forest", "mountain", "desert", "coastal", "plains", "swamp"]
        for _ in range(random.randint(1, 3)):
            biome = random.choice(biomes)
            trader.add_favourite_biome(biome)
        
        # Save the trader
        self.save_trader(trader)
        return trader
    
    def initialize_traders(self, count=10):
        """
        Initialize a number of random traders in the world.
        Useful for game startup.
        
        Args:
            count (int): Number of traders to create
            
        Returns:
            list: The created traders
        """
        # Get all available settlements
        db = get_db()
        with Session(db) as session:
            # Define settlements table
            settlements = Table(
                'settlements', 
                self.metadata,
                Column('settlement_id', String(36), primary_key=True)
            )
            
            # Query for settlements
            stmt = select(settlements.c.settlement_id)
            settlements_list = [row[0] for row in session.execute(stmt).fetchall()]
        
        if not settlements_list:
            logger.warning("No settlements found for trader initialization")
            return []
        
        # Create random traders
        traders = []
        for _ in range(count):
            location = random.choice(settlements_list)
            trader = self.generate_random_trader(location)
            traders.append(trader)
        
        logger.info(f"Initialized {len(traders)} random traders")
        return traders