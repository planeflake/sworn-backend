from app.game_state.mcts import MCTS
import logging as logger

class AnimalState:
    """
    State representation for animal AI decision-making using MCTS.
    This class represents the state of an animal for use in Monte Carlo Tree Search.
    """
    
    def __init__(self, animal, world_info=None, location_graph=None):
        """
        Initialize an animal state for decision-making.
        
        Args:
            animal: The animal object this state represents
            world_info: Information about the game world (optional)
            location_graph: Graph of location connections (optional)
        """
        self.animal = animal
        self.world_info = world_info or {}
        self.location_graph = location_graph or {}
        
        # Cache of possible actions for this state
        self._possible_actions = None

    ### Base Methods ###

    def get_possible_actions(self):
        """
        Get all possible actions the animal can take in the current state.
        
        Returns:
            list: List of possible action objects
        """
        if self._possible_actions is not None:
            return self._possible_actions
            
        actions = []
        
        # Add movement actions
        movement_actions = self._get_movement_actions()
        actions.extend(movement_actions)
        
        # Add hunting actions
        hunting_actions = self._get_hunting_actions()
        actions.extend(hunting_actions)
        
        # Add rest action (stay in place)
        actions.append({"type": "rest", "location_id": self.animal.area_id})
        
        self._possible_actions = actions
        return actions
    
    def _get_movement_actions(self):
        """
        Get possible movement actions based on the animal's current location.
        
        Returns:
            list: List of possible movement actions
        """
        actions = []
        
        # If we have a location graph, use it to find connected locations
        current_location = self.animal.area_id
        if current_location in self.location_graph:
            connected_locations = self.location_graph[current_location]
            
            for location_id in connected_locations:
                # Skip unacceptable locations
                if location_id in self.animal.territory:
                    continue
                    
                # Create movement action
                action = {
                    "type": "move",
                    "location_id": location_id,
                    "score": self._score_location(location_id)
                }
                actions.append(action)
        
        return actions
    
    def _score_location(self, location_id):
        """
        Score a location based on animal preferences.
        
        Args:
            location_id: The ID of the location to score
            
        Returns:
            float: A score for this location (higher is better)
        """
        score = 1.0  # Base score
        
        # Preferred locations get a bonus
        if location_id in self.animal.territory:
            score += 2.0
        
        # Get location biome if available in world_info
        if 'locations' in self.world_info and location_id in self.world_info['locations']:
            biome = self.world_info['locations'][location_id].get('biome')
            
            # Preferred biomes get a bonus
            if biome in self.animal.diet:
                score += 1.5
        
        return score
    
    def _get_hunting_actions(self):
        """
        Get possible hunting actions at the current location.
        
        Returns:
            list: List of possible hunting actions
        """
        actions = []
        
        # Check if there are prey opportunities at the current location
        current_location = self.animal.area_id
        if 'prey_data' in self.world_info and current_location in self.world_info['prey_data']:
            prey_list = self.world_info['prey_data'][current_location]
            
            for prey in prey_list:
                action = {
                    "type": "hunt",
                    "prey_id": prey['id'],
                    "difficulty": prey['difficulty'],
                    "location_id": current_location
                }
                actions.append(action)
        
        return actions

    def _simulate_hunt(self, difficulty):
        """
        Simulate the outcome of a hunt based on difficulty.
        
        Args:
            difficulty (float): The difficulty of the hunt
            
        Returns:
            bool: True if the hunt was successful, False otherwise
        """
        import random
        success_chance = max(0.1, 1.0 - (difficulty / 10.0))
        return random.random() < success_chance
    
    def _simulate_migration(self):
        """
        Simulate the animal migrating to a new location.
        This is a placeholder for future work.
        
        Returns:
            str: The new location ID if migrated, None otherwise
        """
        # Placeholder for future work
        return None

    ### MCTS Methods ###

    def apply_action(self, action):
        """
        Apply an action to this state and return the new state.
        
        Args:
            action: The action to apply
            
        Returns:
            AnimalState: A new state resulting from the action
        """
        # Create a copy of this state
        new_state = self.clone()
        
        # Apply the action based on its type
        if action["type"] == "move":
            new_state.animal.set_location(action["location_id"])
            # Clear destination if we've reached it
            if new_state.animal.destination_id == action["location_id"]:
                new_state.animal.set_location(None, is_home=False)
                
        elif action["type"] == "hunt":
            # Simulate hunting success or failure
            success = self._simulate_hunt(action["difficulty"])
            if success:
                logger.info(f"Animal {self.animal.name} successfully hunted prey {action['prey_id']}")
                # Add resources from prey
                prey_resources = self.world_info['prey_data'][self.animal.area_id][action['prey_id']]['resources']
                for resource, quantity in prey_resources.items():
                    new_state.animal.add_resource(resource, quantity)
            else:
                logger.info(f"Animal {self.animal.name} failed to hunt prey {action['prey_id']}")
        
        elif action["type"] == "rest":
            # Nothing to do - staying in place
            pass
        
        # Clear cached actions since the state has changed
        new_state._possible_actions = None
        
        return new_state

    def get_reward(self):
        """
        Get the reward value for this state.
        Higher means better state for the animal.
        
        Returns:
            float: The calculated reward value
        """
        reward = 0.0
        
        # Reward for resources
        for resource, amount in self.animal.resources.items():
            reward += amount * 0.1  # Resources are valuable
        
        # Reward for being in preferred locations
        current_location = self.animal.area_id
        if current_location in self.animal.territory:
            reward += 2.0
        
        # Check biome if we have world info
        if 'locations' in self.world_info and current_location in self.world_info['locations']:
            biome = self.world_info['locations'][current_location].get('biome')
            if biome in self.animal.diet:
                reward += 1.5
        
        return reward

    def is_terminal(self):
        """
        Check if this is a terminal state.
        For animals, there's no real "terminal" state in normal gameplay.
        
        Returns:
            bool: Always False in this implementation
        """
        return False

    ### New Methods ###

    def calculate_encounter_chance(self, time_of_day: str, weather: str) -> float:
        """
        Calculate the chance of encountering this animal.
        
        Args:
            time_of_day (str): Time of day (morning, day, evening, night).
            weather (str): Current weather condition.
            
        Returns:
            float: Chance of encounter (0.0-1.0).
        """
        return self.animal.calculate_encounter_chance(time_of_day, weather)

    def calculate_risk_to_traders(self) -> dict:
        """
        Calculate the risk this animal poses to traders.
        
        Returns:
            dict: Risk information.
        """
        return self.animal.calculate_risk_to_traders()

    def migrate(self, current_season: str):
        """
        Migrate the animal to a new location based on the season.
        
        Args:
            current_season (str): Current season name.
            
        Returns:
            str: New location ID if migrated, None otherwise.
        """
        new_location = self.animal.migrate(current_season)
        if new_location:
            logger.info(f"Animal {self.animal.name} migrated to {new_location}")
        return new_location

    def apply_seasonal_changes(self, current_season: str):
        """
        Apply seasonal changes to the animal's state.
        
        Args:
            current_season (str): Current season name.
            
        Returns:
            bool: True if changes were applied.
        """
        applied = self.animal.apply_seasonal_changes(current_season)
        if applied:
            logger.info(f"Applied seasonal changes for {current_season} to animal {self.animal.name}")
        return applied

    def calculate_hunting_difficulty(self) -> float:
        """
        Calculate the difficulty of hunting this animal.
        
        Returns:
            float: Hunting difficulty score (higher is harder).
        """
        base_difficulty = self.animal.difficulty_to_hunt
        size_factor = {"tiny": 0.5, "small": 0.8, "medium": 1.0, "large": 1.2, "huge": 1.5}.get(self.animal.size, 1.0)
        behavior_factor = 1.0
        if "skittish" in self.animal.behaviors:
            behavior_factor *= 1.2
        if "aggressive" in self.animal.behaviors:
            behavior_factor *= 0.8
        return base_difficulty * size_factor * behavior_factor

    def get_resources(self) -> dict:
        """
        Get the resources this animal provides if hunted.
        
        Returns:
            dict: Resources and their quantities.
        """
        return self.animal.resources

    ### Utility Methods ###

    def clone(self):
        """
        Create a deep copy of this state.
        
        Returns:
            AnimalState: A new identical state object
        """
        # Convert animal to dict and back for deep copy
        animal_dict = self.animal.to_dict()
        new_animal = self.animal.__class__.from_dict(animal_dict)
        
        # Create new state with copied data
        new_state = AnimalState(
            new_animal,
            world_info=self.world_info.copy(),
            location_graph=self.location_graph.copy()
        )
        
        return new_state

    def __str__(self):
        """String representation of the state"""
        return f"AnimalState({self.animal.name} at {self.animal.area_id})"

    def __repr__(self):
        return f"AnimalState(animal={self.animal.name}, location={self.animal.area_id})"