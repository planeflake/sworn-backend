import logging as logger
import random

class Wildlife:
    def __init__(self, wildlife_id):
        self.wildlife_id = wildlife_id
        self._dirty = False
        self.health = 100
        self.status_effects = []
        self.inventory = []
        # New ecological attributes
        self.ecological_role = 'prey'  # 'predator', 'prey', or 'omnivore'
        self.size = 'medium'           # e.g., 'small', 'medium', 'large'
        self.reproduction_rate = 1.0
        self.attack_power = 5
        self.prey_list = []            # For predators: list of potential prey IDs or types

    def set_type(self, type):
        """
        Set the type of wildlife.
        
        Args:
            type (str): The type of wildlife
        """
        self.type = type
        self._dirty = True
        logger.info(f"Set type for wildlife {self.wildlife_id}: {type}")

    def set_name(self, name):
        self.name = name
        self._dirty = True
        logger.info(f"Set name for wildlife {self.wildlife_id}: {name}")

    def set_description(self, description):
        self.description = description
        self._dirty = True
        logger.info(f"Set description for wildlife {self.wildlife_id}: {description}")

    def set_base_movement(self, base_movement):
        self.base_movement = base_movement
        self._dirty = True
        logger.info(f"Set base movement for wildlife {self.wildlife_id}: {base_movement}")

    def set_actions(self, actions):
        self.actions = actions
        self._dirty = True
        logger.info(f"Set actions for wildlife {self.wildlife_id}: {actions}")

    def set_danger_level_base(self, danger_level_base):
        self.danger_level_base = danger_level_base
        self._dirty = True
        logger.info(f"Set danger level base for wildlife {self.wildlife_id}: {danger_level_base}")

    def set_food_types(self, food_types):
        self.food_types = food_types
        self._dirty = True
        logger.info(f"Set food types for wildlife {self.wildlife_id}: {food_types}")

    def set_natural_enemies(self, natural_enemies):
        self.natural_enemies = natural_enemies
        self._dirty = True
        logger.info(f"Set natural enemies for wildlife {self.wildlife_id}: {natural_enemies}")

    def set_fears(self, fears):
        self.fears = fears
        self._dirty = True
        logger.info(f"Set fears for wildlife {self.wildlife_id}: {fears}")

    def set_likes(self, likes):
        self.likes = likes
        self._dirty = True
        logger.info(f"Set likes for wildlife {self.wildlife_id}: {likes}")

    def set_dislikes(self, dislikes):
        self.dislikes = dislikes
        self._dirty = True
        logger.info(f"Set dislikes for wildlife {self.wildlife_id}: {dislikes}")

    # New ecological setters
    def set_ecological_role(self, role):
        """
        Set the ecological role of the wildlife.
        role: 'predator', 'prey', or 'omnivore'
        """
        self.ecological_role = role
        self._dirty = True
        logger.info(f"Set ecological role for wildlife {self.wildlife_id}: {role}")

    def set_size(self, size):
        """
        Set the size category for the wildlife.
        size: 'small', 'medium', or 'large'
        """
        self.size = size
        self._dirty = True
        logger.info(f"Set size for wildlife {self.wildlife_id}: {size}")

    def set_reproduction_rate(self, rate):
        """
        Set the reproduction rate for the wildlife.
        """
        self.reproduction_rate = rate
        self._dirty = True
        logger.info(f"Set reproduction rate for wildlife {self.wildlife_id}: {rate}")

    def set_attack_power(self, power):
        """
        Set the attack power for the wildlife.
        """
        self.attack_power = power
        self._dirty = True
        logger.info(f"Set attack power for wildlife {self.wildlife_id}: {power}")

    def add_prey(self, prey_identifier):
        """
        For predators, add a potential prey identifier (could be an ID or type).
        """
        self.prey_list.append(prey_identifier)
        self._dirty = True
        logger.info(f"Added prey {prey_identifier} to wildlife {self.wildlife_id}")

    # Advanced functions
    def take_damage(self, amount):
        self.health -= amount
        if self.health <= 0:
            self.die()
        self._dirty = True
        logger.info(f"Wildlife {self.wildlife_id} took {amount} damage, health is now {self.health}")

    def heal(self, amount):
        self.health += amount
        if self.health > 100:
            self.health = 100
        self._dirty = True
        logger.info(f"Wildlife {self.wildlife_id} healed {amount}, health is now {self.health}")

    def die(self):
        logger.info(f"Wildlife {self.wildlife_id} has died")
        # Handle death logic here

    def add_status_effect(self, effect):
        self.status_effects.append(effect)
        self._dirty = True
        logger.info(f"Added status effect {effect} to wildlife {self.wildlife_id}")

    def remove_status_effect(self, effect):
        if effect in self.status_effects:
            self.status_effects.remove(effect)
            self._dirty = True
            logger.info(f"Removed status effect {effect} from wildlife {self.wildlife_id}")

    def move_to(self, new_location):
        self.current_location = new_location
        self._dirty = True
        logger.info(f"Wildlife {self.wildlife_id} moved to {new_location}")

    def interact_with_environment(self, environment):
        # Define interaction logic here
        logger.info(f"Wildlife {self.wildlife_id} interacts with {environment}")

    def decide_next_action(self):
        """
        AI decision-making logic.
        If the wildlife is a predator and prey is nearby, attempt to hunt.
        If it is prey and a predator is near, decide to flee.
        Otherwise, pick an action from its list.
        """
        # This is a placeholder decision logic.
        if self.ecological_role == 'predator' and self.prey_list:
            action = self.hunt(random.choice(self.prey_list))
        elif self.ecological_role == 'prey' and self.natural_enemies:
            # Simulate detecting a nearby enemy and fleeing
            action = self.flee(random.choice(self.natural_enemies))
        else:
            action = random.choice(self.actions) if self.actions else 'idle'
        logger.info(f"Wildlife {self.wildlife_id} decided to {action}")
        return action

    def hunt(self, target):
        """
        Attempt to hunt the specified target.
        The success can be determined by comparing attack power, target's defense, or a random roll.
        """
        success_chance = random.random() + (self.attack_power / 100)
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
        """
        escape_chance = random.random() + (self.base_movement / 10)
        if escape_chance > 0.5:
            result = f"successfully fled from {predator}"
            # Additional logic for changing location or status effects.
        else:
            result = f"failed to escape {predator}"
        logger.info(f"Wildlife {self.wildlife_id} {result}")
        return f"flee attempt from {predator}: {result}"

    # State tracking methods
    def is_dirty(self):
        """Check if this wildlife has unsaved changes."""
        return self._dirty
        
    def mark_clean(self):
        """Mark this wildlife as having no unsaved changes."""
        self._dirty = False

    # Serialization methods
    def to_dict(self):
        """Convert wildlife to dictionary for storage."""
        return {
            "wildlife_id": self.wildlife_id,
            "name": getattr(self, 'name', None),
            "description": getattr(self, 'description', None),
            "base_movement": getattr(self, 'base_movement', None),
            "actions": getattr(self, 'actions', {}),
            "danger_level_base": getattr(self, 'danger_level_base', None),
            "food_types": getattr(self, 'food_types', {}),
            "natural_enemies": getattr(self, 'natural_enemies', []),
            "fears": getattr(self, 'fears', None),
            "likes": getattr(self, 'likes', None),
            "dislikes": getattr(self, 'dislikes', None),
            "health": self.health,
            "status_effects": self.status_effects,
            "inventory": self.inventory,
            "ecological_role": self.ecological_role,
            "size": self.size,
            "reproduction_rate": self.reproduction_rate,
            "attack_power": self.attack_power,
            "prey_list": self.prey_list
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create wildlife from dictionary data."""
        wildlife = cls(wildlife_id=data["wildlife_id"])
        wildlife.name = data.get("name")
        wildlife.description = data.get("description")
        wildlife.base_movement = data.get("base_movement")
        wildlife.actions = data.get("actions", {})
        wildlife.danger_level_base = data.get("danger_level_base")
        wildlife.food_types = data.get("food_types", {})
        wildlife.natural_enemies = data.get("natural_enemies", [])
        wildlife.fears = data.get("fears")
        wildlife.likes = data.get("likes")
        wildlife.dislikes = data.get("dislikes")
        wildlife.health = data.get("health", 100)
        wildlife.status_effects = data.get("status_effects", [])
        wildlife.inventory = data.get("inventory", [])
        wildlife.ecological_role = data.get("ecological_role", 'prey')
        wildlife.size = data.get("size", 'medium')
        wildlife.reproduction_rate = data.get("reproduction_rate", 1.0)
        wildlife.attack_power = data.get("attack_power", 5)
        wildlife.prey_list = data.get("prey_list", [])
        return wildlife
