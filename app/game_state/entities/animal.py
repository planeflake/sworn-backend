import logging as logger
import random
from typing import List, Dict, Optional, Any

class Wildlife:
    def __init__(self, wildlife_id):
        self.wildlife_id = wildlife_id
        self._dirty = False
        self.properties = {}  # Dictionary to store all properties
        
        # Set default values
        self.set_property("health", 100)
        self.set_property("status_effects", [])
        self.set_property("inventory", [])
        self.set_property("ecological_role", "prey")  # 'predator', 'prey', or 'omnivore'
        self.set_property("size", "medium")  # e.g., 'small', 'medium', 'large'
        self.set_property("reproduction_rate", 1.0)
        self.set_property("attack_power", 5)
        self.set_property("prey_list", [])  # For predators: list of potential prey IDs or types

    def set_type(self, type):
        """
        Set the type of wildlife.
        
        Args:
            type (str): The type of wildlife
        """
        self.set_property("type", type)
        logger.info(f"Set type for wildlife {self.wildlife_id}: {type}")

    def set_name(self, name):
        """
        Set the name of the wildlife.
        
        Args:
            name (str): The name of the wildlife
        """
        self.set_property("name", name)
        logger.info(f"Set name for wildlife {self.wildlife_id}: {name}")

    def set_description(self, description):
        """
        Set the description of the wildlife.
        
        Args:
            description (str): The description of the wildlife
        """
        self.set_property("description", description)
        logger.info(f"Set description for wildlife {self.wildlife_id}: {description}")

    def set_base_movement(self, base_movement):
        """
        Set the base movement of the wildlife.
        
        Args:
            base_movement (int): The base movement of the wildlife
        """
        self.set_property("base_movement", base_movement)
        logger.info(f"Set base movement for wildlife {self.wildlife_id}: {base_movement}")

    def set_actions(self, actions):
        """
        Set the actions of the wildlife.
        
        Args:
            actions (list): The actions of the wildlife
        """
        self.set_property("actions", actions)
        logger.info(f"Set actions for wildlife {self.wildlife_id}: {actions}")

    def set_danger_level_base(self, danger_level_base):
        """
        Set the base danger level of the wildlife.
        
        Args:
            danger_level_base (int): The base danger level of the wildlife
        """
        self.set_property("danger_level_base", danger_level_base)
        logger.info(f"Set danger level base for wildlife {self.wildlife_id}: {danger_level_base}")

    def set_food_types(self, food_types):
        """
        Set the food types of the wildlife.
        
        Args:
            food_types (list): The food types of the wildlife
        """
        self.set_property("food_types", food_types)
        logger.info(f"Set food types for wildlife {self.wildlife_id}: {food_types}")

    def set_natural_enemies(self, natural_enemies):
        """
        Set the natural enemies of the wildlife.
        
        Args:
            natural_enemies (list): The natural enemies of the wildlife
        """
        self.set_property("natural_enemies", natural_enemies)
        logger.info(f"Set natural enemies for wildlife {self.wildlife_id}: {natural_enemies}")

    def set_fears(self, fears):
        """
        Set the fears of the wildlife.
        
        Args:
            fears (list): The fears of the wildlife
        """
        self.set_property("fears", fears)
        logger.info(f"Set fears for wildlife {self.wildlife_id}: {fears}")

    def set_likes(self, likes):
        """
        Set the likes of the wildlife.
        
        Args:
            likes (list): The likes of the wildlife
        """
        self.set_property("likes", likes)
        logger.info(f"Set likes for wildlife {self.wildlife_id}: {likes}")

    def set_dislikes(self, dislikes):
        """
        Set the dislikes of the wildlife.
        
        Args:
            dislikes (list): The dislikes of the wildlife
        """
        self.set_property("dislikes", dislikes)
        logger.info(f"Set dislikes for wildlife {self.wildlife_id}: {dislikes}")

    # New ecological setters
    def set_ecological_role(self, role):
        """
        Set the ecological role of the wildlife.
        
        Args:
            role (str): The ecological role ('predator', 'prey', or 'omnivore')
        """
        self.set_property("ecological_role", role)
        logger.info(f"Set ecological role for wildlife {self.wildlife_id}: {role}")

    def set_size(self, size):
        """
        Set the size category for the wildlife.
        
        Args:
            size (str): The size ('small', 'medium', or 'large')
        """
        self.set_property("size", size)
        logger.info(f"Set size for wildlife {self.wildlife_id}: {size}")

    def set_reproduction_rate(self, rate):
        """
        Set the reproduction rate for the wildlife.
        
        Args:
            rate (float): The reproduction rate
        """
        self.set_property("reproduction_rate", rate)
        logger.info(f"Set reproduction rate for wildlife {self.wildlife_id}: {rate}")

    def set_attack_power(self, power):
        """
        Set the attack power for the wildlife.
        
        Args:
            power (int): The attack power
        """
        self.set_property("attack_power", power)
        logger.info(f"Set attack power for wildlife {self.wildlife_id}: {power}")

    def add_prey(self, prey_identifier):
        """
        For predators, add a potential prey identifier (could be an ID or type).
        
        Args:
            prey_identifier (str): The prey identifier
        """
        prey_list = self.get_property("prey_list", [])
        prey_list.append(prey_identifier)
        self.set_property("prey_list", prey_list)
        logger.info(f"Added prey {prey_identifier} to wildlife {self.wildlife_id}")

    # Property accessors
    def set_property(self, key: str, value: Any):
        """
        Set a property value.
        
        Args:
            key (str): The property name
            value (Any): The property value
        """
        self.properties[key] = value
        self._dirty = True
        
    def get_property(self, key: str, default: Any = None) -> Any:
        """
        Get a property value.
        
        Args:
            key (str): The property name
            default (Any, optional): Default value if property doesn't exist
            
        Returns:
            Any: The property value or default
        """
        return self.properties.get(key, default)

    # Advanced functions
    def take_damage(self, amount):
        """
        Apply damage to the wildlife.
        
        Args:
            amount (int): The amount of damage
        """
        health = self.get_property("health", 100) - amount
        self.set_property("health", health)
        
        if health <= 0:
            self.die()
            
        logger.info(f"Wildlife {self.wildlife_id} took {amount} damage, health is now {health}")

    def heal(self, amount):
        """
        Heal the wildlife.
        
        Args:
            amount (int): The amount to heal
        """
        health = min(100, self.get_property("health", 100) + amount)
        self.set_property("health", health)
        logger.info(f"Wildlife {self.wildlife_id} healed {amount}, health is now {health}")

    def die(self):
        """
        Handle wildlife death.
        """
        logger.info(f"Wildlife {self.wildlife_id} has died")
        # Handle death logic here

    def add_status_effect(self, effect):
        """
        Add a status effect to the wildlife.
        
        Args:
            effect (str): The status effect to add
        """
        status_effects = self.get_property("status_effects", [])
        status_effects.append(effect)
        self.set_property("status_effects", status_effects)
        logger.info(f"Added status effect {effect} to wildlife {self.wildlife_id}")

    def remove_status_effect(self, effect):
        """
        Remove a status effect from the wildlife.
        
        Args:
            effect (str): The status effect to remove
        """
        status_effects = self.get_property("status_effects", [])
        if effect in status_effects:
            status_effects.remove(effect)
            self.set_property("status_effects", status_effects)
            logger.info(f"Removed status effect {effect} from wildlife {self.wildlife_id}")

    def move_to(self, new_location):
        """
        Move the wildlife to a new location.
        
        Args:
            new_location (str): The new location ID
        """
        self.set_property("current_location", new_location)
        logger.info(f"Wildlife {self.wildlife_id} moved to {new_location}")

    def interact_with_environment(self, environment):
        """
        Handle wildlife interaction with the environment.
        
        Args:
            environment (str): The environment to interact with
        """
        # Define interaction logic here
        logger.info(f"Wildlife {self.wildlife_id} interacts with {environment}")

    def decide_next_action(self):
        """
        AI decision-making logic.
        If the wildlife is a predator and prey is nearby, attempt to hunt.
        If it is prey and a predator is near, decide to flee.
        Otherwise, pick an action from its list.
        
        Returns:
            str: The next action
        """
        # This is a placeholder decision logic.
        ecological_role = self.get_property("ecological_role", "prey")
        prey_list = self.get_property("prey_list", [])
        natural_enemies = self.get_property("natural_enemies", [])
        actions = self.get_property("actions", [])
        
        if ecological_role == 'predator' and prey_list:
            action = self.hunt(random.choice(prey_list))
        elif ecological_role == 'prey' and natural_enemies:
            # Simulate detecting a nearby enemy and fleeing
            action = self.flee(random.choice(natural_enemies))
        else:
            action = random.choice(actions) if actions else 'idle'
            
        logger.info(f"Wildlife {self.wildlife_id} decided to {action}")
        return action

    def hunt(self, target):
        """
        Attempt to hunt the specified target.
        The success can be determined by comparing attack power, target's defense, or a random roll.
        
        Args:
            target (str): The target to hunt
            
        Returns:
            str: The result of the hunt attempt
        """
        attack_power = self.get_property("attack_power", 5)
        success_chance = random.random() + (attack_power / 100)
        
        if success_chance > 0.5:
            result = f"successfully hunted {target}"
            # Additional logic for reducing target health, gaining loot, etc.
        else:
            result = f"failed to hunt {target}"
            
        logger.info(f"Wildlife {self.wildlife_id} {result}")
        return f"hunt attempt on {target}: {result}"

    def flee(self, predator):
        """
        Attempt to flee from a predator.
        Success can depend on base movement, size, and random chance.
        
        Args:
            predator (str): The predator to flee from
            
        Returns:
            str: The result of the flee attempt
        """
        base_movement = self.get_property("base_movement", 5)
        escape_chance = random.random() + (base_movement / 10)
        
        if escape_chance > 0.5:
            result = f"successfully fled from {predator}"
            # Additional logic for changing location or status effects.
        else:
            result = f"failed to escape {predator}"
            
        logger.info(f"Wildlife {self.wildlife_id} {result}")
        return f"flee attempt from {predator}: {result}"

    # State tracking methods
    def is_dirty(self):
        """
        Check if this wildlife has unsaved changes.
        
        Returns:
            bool: True if there are unsaved changes
        """
        return self._dirty
        
    def mark_clean(self):
        """
        Mark this wildlife as having no unsaved changes.
        """
        self._dirty = False

    # Serialization methods
    def to_dict(self):
        """
        Convert wildlife to dictionary for storage.
        
        Returns:
            dict: Dictionary representation of this wildlife
        """
        return {
            "wildlife_id": self.wildlife_id,
            "properties": self.properties
        }
    
    @classmethod
    def from_dict(cls, data):
        """
        Create wildlife from dictionary data.
        
        Args:
            data (dict): Dictionary data to create wildlife from
            
        Returns:
            Wildlife: New wildlife instance
        """
        wildlife = cls(wildlife_id=data["wildlife_id"])
        wildlife.properties = data.get("properties", {})
        return wildlife