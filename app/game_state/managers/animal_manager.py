from sqlalchemy import Column, String, Text, Table, MetaData, select, insert, update, delete
from sqlalchemy.orm import Session
from database.connection import get_db
from pydantic import BaseModel
from typing import List, Optional
import logging as logger
import random
import json
import uuid

from ..entities.animal import Wildlife  # Using the updated Wildlife class from your entity definitions

# Pydantic model for database operations
class AnimalDB(BaseModel):
    """Database model for the Animal table"""
    animal_id: str
    name: Optional[str] = None
    location_id: Optional[str] = None
    data: str  # JSON string of animal (Wildlife) data

class AnimalManager:
    def __init__(self,db):
        """Initialize the AnimalManager."""
        self.animals = {}  # Cache for loaded animals keyed by animal_id
        self.db = db
        logger.info("AnimalManager initialized")
    
    def _setup_db_metadata(self):
        """Set up SQLAlchemy metadata for the animals table."""
        self.metadata = MetaData()
        self.animals_table = Table(
            'animals', 
            self.metadata,
            Column('animal_id', String(36), primary_key=True),
            Column('name', String(100)),
            Column('location_id', String(36)),
            Column('data', Text)
        )
    
    def create_animal(self, name: str, description: Optional[str] = None) -> Wildlife:
        """
        Create a new animal (Wildlife) with a unique ID.
        
        Args:
            name (str): The animal's name.
            description (Optional[str]): Description for the animal.
            
        Returns:
            Wildlife: The newly created animal instance.
        """
        animal_id = str(uuid.uuid4())
        animal = Wildlife(animal_id)
        animal.set_name(name)
        animal.set_description(description or f"An animal named {name}")
        
        # Optionally, set default ecological properties (these could be randomized or based on type)
        animal.set_ecological_role(random.choice(['predator', 'prey', 'omnivore']))
        animal.set_size(random.choice(['small', 'medium', 'large']))
        animal.set_reproduction_rate(round(random.uniform(0.8, 1.2), 2))
        animal.set_attack_power(random.randint(3, 10))
        
        # Cache the animal and persist it
        self.animals[animal_id] = animal
        self.save_animal(animal)
        
        logger.info(f"Created new animal: {name} (ID: {animal_id})")
        return animal

    def load_animal(self, animal_id: str) -> Optional[Wildlife]:
        """
        Load an animal from the database.
        
        Args:
            animal_id (str): The ID of the animal to load.
            
        Returns:
            Wildlife: The loaded animal instance, or None if not found.
        """
        if animal_id in self.animals:
            return self.animals[animal_id]
        
        db = get_db()
        with Session(db) as session:
            stmt = select(self.animals_table).where(self.animals_table.c.animal_id == animal_id)
            result = session.execute(stmt).first()
            if result is None:
                logger.warning(f"Animal not found: {animal_id}")
                return None
            
            animal_data = json.loads(result.data)
            animal = Wildlife.from_dict(animal_data)
            self.animals[animal_id] = animal
            
            logger.info(f"Loaded animal: {animal.name} (ID: {animal_id})")
            return animal

    def save_animal(self, animal: Wildlife) -> bool:
        """
        Save an animal to the database.
        
        Args:
            animal (Wildlife): The animal instance to save.
            
        Returns:
            bool: True if save was successful, False otherwise.
        """
        if not animal.is_dirty():
            return True
        
        animal_dict = animal.to_dict()
        animal_data = json.dumps(animal_dict)
        animal_db = AnimalDB(
            animal_id=animal.wildlife_id,
            name=getattr(animal, 'name', None),
            location_id=getattr(animal, 'current_location', None),
            data=animal_data
        )
        
        db = get_db()
        with Session(db) as session:
            try:
                stmt = select(self.animals_table).where(self.animals_table.c.animal_id == animal.wildlife_id)
                exists = session.execute(stmt).first() is not None
                
                if exists:
                    stmt = update(self.animals_table).where(
                        self.animals_table.c.animal_id == animal.wildlife_id
                    ).values(
                        name=animal_db.name,
                        location_id=animal_db.location_id,
                        data=animal_db.data
                    )
                    session.execute(stmt)
                else:
                    stmt = insert(self.animals_table).values(
                        animal_id=animal_db.animal_id,
                        name=animal_db.name,
                        location_id=animal_db.location_id,
                        data=animal_db.data
                    )
                    session.execute(stmt)
                
                session.commit()
                animal.mark_clean()
                logger.info(f"Saved animal: {animal.name} (ID: {animal.wildlife_id})")
                return True
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to save animal {animal.wildlife_id}: {str(e)}")
                return False

    def get_all_animals(self) -> List[Wildlife]:
        """
        Get all animals from the database.
        
        Returns:
            list: List of all animal instances.
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.animals_table.c.animal_id)
            results = session.execute(stmt).fetchall()
            animals_list = []
            for result in results:
                animal_id = result[0]
                animal = self.load_animal(animal_id)
                if animal:
                    animals_list.append(animal)
            return animals_list

    def get_animals_at_location(self, location_id: str) -> List[Wildlife]:
        """
        Get all animals at a specific location.
        
        Args:
            location_id (str): The location ID.
            
        Returns:
            list: List of animal instances at the location.
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.animals_table.c.animal_id).where(
                self.animals_table.c.location_id == location_id
            )
            results = session.execute(stmt).fetchall()
            animals_list = []
            for result in results:
                animal_id = result[0]
                animal = self.load_animal(animal_id)
                if animal:
                    animals_list.append(animal)
            return animals_list

    def get_predators_by_area(self, location_id: str) -> List[Wildlife]:
        """
        Get all predators at
        a specific location.
        """
        animals = self.get_animals_at_location(location_id)
        return [animal for animal in animals if animal.ecological_role == 'predator']

    def get_prey_by_area(self, location_id: str) -> List[Wildlife]:
        """
        Get all prey at a specific location.
        """
        animals = self.get_animals_at_location(location_id)
        return [animal for animal in animals if animal.ecological_role == 'prey']

    def get_prey_by_area(self, location_id: str, predator_prey_list: List[str]) -> List[Wildlife]:
        """
        Get all valid prey for a predator at a specific location.

        Args:
            location_id (str): The location ID.
            predator_prey_list (List[str]): List of species or prey types the predator can hunt.

        Returns:
            List[Wildlife]: List of prey animals at the location that match the predator's prey preferences.
        """
        # Get all animals at the location
        animals = self.get_animals_at_location(location_id)
        
        # Filter animals that are prey and match the predator's prey list
        valid_prey = [
            animal for animal in animals
            if animal.ecological_role == 'prey' and animal.type in predator_prey_list
        ]
        
        return valid_prey

    def delete_animal(self, animal_id: str) -> bool:
        """
        Delete an animal from the database.
        
        Args:
            animal_id (str): The ID of the animal to delete.
            
        Returns:
            bool: True if deletion was successful, False otherwise.
        """
        if animal_id in self.animals:
            del self.animals[animal_id]
        
        db = get_db()
        with Session(db) as session:
            try:
                stmt = delete(self.animals_table).where(self.animals_table.c.animal_id == animal_id)
                session.execute(stmt)
                session.commit()
                logger.info(f"Deleted animal: {animal_id}")
                return True
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to delete animal {animal_id}: {str(e)}")
                return False

    def update_animal_location(self, animal_id: str, location_id: str) -> bool:
        """
        Update an animal's current location.
        
        Args:
            animal_id (str): The ID of the animal.
            location_id (str): The new location ID.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        animal = self.load_animal(animal_id)
        if not animal:
            logger.warning(f"Cannot update location: Animal not found: {animal_id}")
            return False
        
        animal.move_to(location_id)
        return self.save_animal(animal)

    def process_animal_decisions(self):
        """
        Process decisions for all active animals.
        For instance, this method could handle movement, hunting, or fleeing behaviors.
        """
        all_animals = self.get_all_animals()
        for animal in all_animals:
            self._process_single_animal_decision(animal)
    
    def _process_single_animal_decision(self, animal: Wildlife):
        """
        Process decisions for a single animal.
        
        Args:
            animal (Wildlife): The animal to process.
        """
        # For predators, attempt to hunt if prey is nearby.
        # For prey, try to flee if a predator is close.
        # Otherwise, execute a random action.
        decision = animal.decide_next_action()
        logger.info(f"Processed decision for animal {animal.name}: {decision}")
        self.save_animal(animal)

    def generate_random_animal(self, location_id: Optional[str] = None) -> Wildlife:
        """
        Generate a random animal for testing or world population.
        
        Args:
            location_id (str, optional): Initial location for the animal.
            
        Returns:
            Wildlife: The newly created animal.
        """
        animal_names = ["Wolf", "Bear", "Fox", "Deer", "Boar", "Eagle", "Lynx", "Rabbit"]
        name = random.choice(animal_names) + f"_{str(uuid.uuid4())[:4]}"
        descriptions = [
            "A swift and agile creature.",
            "A fierce predator with a keen eye.",
            "A gentle herbivore roaming its territory.",
            "An adaptable animal thriving in various environments."
        ]
        description = random.choice(descriptions)
        animal = self.create_animal(name, description)
        
        # Optionally set a starting location if provided
        if location_id:
            animal.move_to(location_id)
        
        # For predators, assign some potential prey (here, as an example, we use random animal names)
        if animal.ecological_role == 'predator':
            potential_prey = [n for n in animal_names if n != name.split('_')[0]]
            for _ in range(random.randint(1, 3)):
                animal.add_prey(random.choice(potential_prey))
        
        self.save_animal(animal)
        return animal

    def initialize_animals(self, count: int = 10) -> List[Wildlife]:
        """
        Initialize a number of random animals in the world.
        
        Args:
            count (int): Number of animals to create.
            
        Returns:
            list: The list of created animal instances.
        """
        # For a realistic initialization, you might query available locations from the database.
        # Here, we use a placeholder list of location IDs.
        placeholder_locations = [str(uuid.uuid4()) for _ in range(5)]
        animals_list = []
        for _ in range(count):
            location = random.choice(placeholder_locations)
            animal = self.generate_random_animal(location)
            animals_list.append(animal)
        logger.info(f"Initialized {len(animals_list)} random animals")
        return animals_list

    def get_animal_count(self) -> int:
        """
        Get the total number of animals.
        
        Returns:
            int: The total count of animals.
        """
        db = get_db()
        with Session(db) as session:
            stmt = select(self.animals_table)
            results = session.execute(stmt).all()
            return len(results)
