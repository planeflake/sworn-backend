# app/game_state/entities/quest.py
import uuid
import copy
from typing import List, Dict, Optional, Any

class Quest:
    """
    Entity class representing a quest in the game world.
    """
    
    def __init__(self, name: str, description: str, type: str, area: str, 
                 difficulty: int = 1, rewards: Optional[Dict[str, Any]] = None):
        self.id = str(uuid.uuid4())  # Unique identifier
        self.name = name
        self.description = description
        self.type = type               # e.g., "trader_stranded", "monster_sighted"r
        self.area = area               # Area ID where the quest takes place
        self.difficulty = difficulty   # 1-5 scale
        self.rewards = rewards or {}   # Dict of rewards (gold, items, xp, etc.)
        self.status = "inactive"       # inactive, active, failed, succeeded, canceled
        self.objectives = []           # List of objectives/steps for the quest
        self.prerequisites = []        # Quests or conditions required before this quest
        self.settlement = None         # Settlement ID where quest is available
        self.quest_giver = None        # NPC who gives the quest
        self._properties = {}          # Additional properties
        self._is_dirty = False         # Track if the quest has been modified

    def __repr__(self) -> str:
        return f"Quest(id={self.id}, name='{self.name}', type='{self.type}', status='{self.status}')"
    
    def __str__(self) -> str:
        return f"{self.name} ({self.type}, {self.status}) - {self.get_progress()}% complete"
    
    def _mark_dirty(self) -> None:
        """Mark the quest as needing to be saved to the database."""
        self._is_dirty = True
    
    @property
    def is_dirty(self) -> bool:
        """Check if the quest has unsaved changes."""
        return self._is_dirty
    
    def clean(self) -> None:
        """Mark the quest as saved/synchronized."""
        self._is_dirty = False

    def set_property(self, key: str, value: Any) -> None:
        """Set a custom property on the quest."""
        self._properties[key] = value
        self._mark_dirty()
    
    def get_property(self, key: str, default: Any = None) -> Any:
        """Get a custom property from the quest."""
        return self._properties.get(key, default)
    
    def start(self, player_id: str) -> bool:
        """Start the quest."""
        if self.status == "inactive":
            self.status = "active"
            self.set_property("assigned_player", player_id)
            self.set_property("start_time", import_timestamp())
            self._mark_dirty()
            return True
        return False

    def complete(self, outcome: str = "succeeded") -> bool:
        """Complete the quest with the given outcome."""
        if self.status == "active":
            self.status = outcome  # succeeded, failed, or canceled
            self.set_property("end_time", import_timestamp())
            self._mark_dirty()
            return True
        return False

    def update_objective(self, objective_id: str, completed: bool = True, progress: Optional[float] = None) -> bool:
        """Update an objective's completion status."""
        for objective in self.objectives:
            if objective.get("id") == objective_id:
                objective["completed"] = completed
                if progress is not None:
                    objective["progress"] = progress
                self._mark_dirty()
                
                # Check if all objectives are completed
                if all(obj.get("completed", False) for obj in self.objectives):
                    self.complete("succeeded")
                
                return True
        return False
    
    def get_progress(self) -> int:
        """Get overall quest progress as a percentage."""
        if not self.objectives:
            return 0 if self.status == "inactive" else 100
            
        completed_count = sum(1 for obj in self.objectives if obj.get("completed", False))
        return int((completed_count / len(self.objectives)) * 100)
    
    def copy(self):
        """Create a deep copy of this quest."""
        new_quest = copy.deepcopy(self)
        new_quest.id = str(uuid.uuid4())  # Generate a new ID for the copy
        return new_quest


def import_timestamp() -> float:
    """Get the current timestamp."""
    import time
    return time.time()