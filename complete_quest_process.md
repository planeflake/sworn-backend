# Complete Quest System Implementation Guide

This guide outlines all components needed to fully implement the quest system shown in the sequence diagram.

## 1. QuestService Implementation

The service layer sits between your Celery workers and the QuestManager, handling business logic.

```python
# app/game_state/services/quest_service.py
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session

from app.game_state.managers.quest_manager import QuestManager
from app.game_state.entities.quest import Quest

class QuestService:
    """
    Service for quest-related operations.
    Handles business logic and coordinates between workers and managers.
    """
    
    def __init__(self, db: Session):
        """Initialize with a database session"""
        self.db = db
        self.quest_manager = QuestManager()
    
    async def create_quest(self, quest_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new quest from provided data.
        
        Args:
            quest_data: Dictionary containing quest parameters
            
        Returns:
            Dict with status and quest information
        """
        try:
            # Extract quest data with defaults
            name = quest_data.get("name", "Unnamed Quest")
            description = quest_data.get("description", "")
            quest_type = quest_data.get("type", "generic")
            area = quest_data.get("area_id")
            difficulty = quest_data.get("difficulty", 1)
            rewards = quest_data.get("rewards", {})
            
            # Optional parameters
            settlement = quest_data.get("settlement_id")
            giver = quest_data.get("quest_giver_id")
            objectives = quest_data.get("objectives", [])
            
            # Create the quest
            quest = self.quest_manager.create_quest(
                name, description, quest_type, area, difficulty, rewards
            )
            
            # Set additional properties if provided
            if settlement:
                quest.settlement = settlement
            if giver:
                quest.quest_giver = giver
            
            # Add objectives
            for obj in objectives:
                self._add_objective_to_quest(quest, obj)
            
            # Save quest if modified after creation
            if quest.is_dirty:
                self.quest_manager.save_quest(quest)
            
            return {
                "status": "success",
                "quest_id": quest.id,
                "name": quest.name,
                "message": f"Quest '{name}' created successfully"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to create quest: {str(e)}"
            }
    
    def _add_objective_to_quest(self, quest: Quest, objective_data: Dict[str, Any]) -> None:
        """Add an objective to a quest"""
        objective = {
            "id": objective_data.get("id") or f"obj_{len(quest.objectives) + 1}",
            "description": objective_data.get("description", "Complete the objective"),
            "target": objective_data.get("target"),
            "required_amount": objective_data.get("required_amount", 1),
            "current_amount": objective_data.get("current_amount", 0),
            "completed": False,
            "optional": objective_data.get("optional", False),
            "order": objective_data.get("order", len(quest.objectives)),
            "location_id": objective_data.get("location_id")
        }
        quest.objectives.append(objective)
    
    async def get_quest(self, quest_id: str) -> Dict[str, Any]:
        """Get a quest by ID"""
        quest = self.quest_manager.load_quest(quest_id)
        if not quest:
            return {"status": "error", "message": f"Quest not found: {quest_id}"}
            
        return {
            "status": "success",
            "quest": {
                "id": quest.id,
                "name": quest.name,
                "description": quest.description,
                "type": quest.type,
                "area": quest.area,
                "difficulty": quest.difficulty,
                "status": quest.status,
                "objectives": quest.objectives,
                "progress": quest.get_progress(),
                "rewards": quest.rewards
            }
        }
    
    async def update_objective(self, quest_id: str, objective_id: str, 
                             progress: Optional[float] = None, 
                             completed: Optional[bool] = None) -> Dict[str, Any]:
        """Update an objective's progress or completion status"""
        quest = self.quest_manager.load_quest(quest_id)
        if not quest:
            return {"status": "error", "message": f"Quest not found: {quest_id}"}
        
        # Update the objective
        result = quest.update_objective(objective_id, completed, progress)
        if not result:
            return {"status": "error", "message": f"Objective not found: {objective_id}"}
        
        # Save the quest with updated objective
        self.quest_manager.save_quest(quest)
        
        # Check if quest was completed as a result
        if quest.status == "succeeded":
            await self._process_quest_completion(quest)
            
        return {
            "status": "success",
            "quest_id": quest.id,
            "objective_id": objective_id,
            "quest_status": quest.status,
            "progress": quest.get_progress()
        }
    
    async def _process_quest_completion(self, quest: Quest) -> None:
        """Process rewards and effects when a quest is completed"""
        # This would distribute rewards to the player
        player_id = quest.get_property("assigned_player")
        if player_id and quest.rewards:
            # Here you would call player service to award rewards
            pass
        
        # Trigger any completion effects
        if quest.get_property("completion_effects"):
            # Process effects like spawning items, changing world state, etc.
            pass
    
    async def assign_quest_to_player(self, quest_id: str, player_id: str) -> Dict[str, Any]:
        """Assign a quest to a player and activate it"""
        quest = self.quest_manager.load_quest(quest_id)
        if not quest:
            return {"status": "error", "message": f"Quest not found: {quest_id}"}
        
        # Start the quest and assign to player
        if not quest.start(player_id):
            return {"status": "error", "message": "Quest cannot be started (already active or completed)"}
        
        # Save the updated quest
        self.quest_manager.save_quest(quest)
        
        return {
            "status": "success",
            "quest_id": quest.id,
            "player_id": player_id,
            "quest_status": quest.status
        }
    
    async def cancel_quest(self, quest_id: str) -> Dict[str, Any]:
        """Cancel an active quest"""
        result = self.quest_manager.cancel_quest(quest_id)
        
        if result:
            return {
                "status": "success",
                "quest_id": quest_id,
                "message": "Quest canceled successfully"
            }
        else:
            return {
                "status": "error",
                "message": f"Failed to cancel quest: {quest_id}"
            }
    
    async def get_available_quests(self, location_id: Optional[str] = None, 
                                 player_id: Optional[str] = None) -> Dict[str, Any]:
        """Get available quests for a location or player"""
        quests = []
        
        if location_id:
            # Get quests for a specific location
            settlement_quests = self.quest_manager.get_quests_in_settlement(location_id)
            area_quests = self.quest_manager.get_quests_in_area(location_id)
            # Combine and filter for available quests
            all_quests = settlement_quests + area_quests
            quests = [q for q in all_quests if q.status == "inactive"]
        
        if player_id:
            # Add player's active quests
            player_quests = self.quest_manager.get_player_quests(player_id)
            active_quests = [q for q in player_quests if q.status == "active"]
            quests.extend(active_quests)
        
        return {
            "status": "success",
            "quests": [
                {
                    "id": q.id,
                    "name": q.name,
                    "description": q.description,
                    "type": q.type,
                    "difficulty": q.difficulty,
                    "status": q.status,
                    "progress": q.get_progress()
                }
                for q in quests
            ]
        }
```

## 2. Celery Task Definition

Define Celery tasks that interact with the quest service:

```python
# app/workers/quest_worker.py
from workers.celery_app import app
from database.connection import SessionLocal
from app.game_state.services.quest_service import QuestService
import logging
import asyncio
from typing import Dict, Optional, Any, List

logger = logging.getLogger(__name__)

@app.task
def create_quest(quest_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new quest with the provided data.
    
    Args:
        quest_data: Dictionary containing quest parameters
            
    Returns:
        Dict with status and quest information
    """
    logger.info(f"Creating quest: {quest_data.get('name')}")
    
    db = SessionLocal()
    try:
        # Create quest service
        quest_service = QuestService(db)
        
        # Process quest creation using async function
        result = asyncio.run(quest_service.create_quest(quest_data))
        
        # Log the result
        log_level = logging.ERROR if result.get("status") != "success" else logging.INFO
        logger.log(log_level, f"Quest creation result: {result}")
        
        return result
    
    except Exception as e:
        logger.exception(f"Error creating quest: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@app.task
def update_quest_objective(quest_id: str, objective_id: str, 
                          progress: Optional[float] = None, 
                          completed: Optional[bool] = None) -> Dict[str, Any]:
    """
    Update a quest objective's progress or completion status.
    
    Args:
        quest_id: The ID of the quest to update
        objective_id: The ID of the specific objective
        progress: Optional progress value (0-1)
        completed: Whether the objective is completed
        
    Returns:
        Dict with status and quest information
    """
    logger.info(f"Updating objective {objective_id} for quest {quest_id}")
    
    db = SessionLocal()
    try:
        # Create quest service
        quest_service = QuestService(db)
        
        # Update objective using async function
        result = asyncio.run(quest_service.update_objective(
            quest_id, objective_id, progress, completed
        ))
        
        # Log the result
        log_level = logging.ERROR if result.get("status") != "success" else logging.INFO
        logger.log(log_level, f"Objective update result: {result}")
        
        return result
    
    except Exception as e:
        logger.exception(f"Error updating quest objective: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@app.task
def assign_quest_to_player(quest_id: str, player_id: str) -> Dict[str, Any]:
    """
    Assign a quest to a player and activate it.
    
    Args:
        quest_id: The ID of the quest to assign
        player_id: The ID of the player
        
    Returns:
        Dict with status and quest information
    """
    logger.info(f"Assigning quest {quest_id} to player {player_id}")
    
    db = SessionLocal()
    try:
        # Create quest service
        quest_service = QuestService(db)
        
        # Assign quest using async function
        result = asyncio.run(quest_service.assign_quest_to_player(quest_id, player_id))
        
        # Log the result
        log_level = logging.ERROR if result.get("status") != "success" else logging.INFO
        logger.log(log_level, f"Quest assignment result: {result}")
        
        return result
    
    except Exception as e:
        logger.exception(f"Error assigning quest: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()
```

## 3. Database Schema Creation

Create a migration script for the quests table:

```python
# migrations/versions/xxx_create_quests_table.py
"""create quests table

Revision ID: xxx
Revises: yyy
Create Date: 2023-xx-xx

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'xxx'
down_revision = 'yyy'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'quests',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('area', sa.String(36), nullable=True),
        sa.Column('settlement', sa.String(36), nullable=True),
        sa.Column('data', sa.Text, nullable=False),
        
        # Optional indexes for frequent queries
        sa.Index('idx_quests_type', 'type'),
        sa.Index('idx_quests_status', 'status'),
        sa.Index('idx_quests_area', 'area'),
        sa.Index('idx_quests_settlement', 'settlement')
    )

def downgrade():
    op.drop_table('quests')
```

## 4. Quest Objectives Structure

Enhance the Quest entity to better handle objectives:

```python
# In the Quest entity class (app/game_state/entities/quest.py)

def add_objective(self, description: str, target: Optional[str] = None, 
                 required_amount: int = 1, location_id: Optional[str] = None,
                 optional: bool = False) -> str:
    """
    Add a new objective to this quest.
    
    Args:
        description: Description of what to accomplish
        target: Optional target entity ID (monster, item, location, etc.)
        required_amount: Amount needed to complete (kills, items, etc.)
        location_id: Location where the objective must be completed
        optional: Whether this objective is optional for quest completion
        
    Returns:
        str: The ID of the newly created objective
    """
    objective_id = f"obj_{len(self.objectives) + 1}"
    
    objective = {
        "id": objective_id,
        "description": description,
        "target": target,
        "required_amount": required_amount,
        "current_amount": 0,
        "completed": False,
        "optional": optional,
        "order": len(self.objectives),
        "location_id": location_id
    }
    
    self.objectives.append(objective)
    self._mark_dirty()
    
    return objective_id

def update_objective_progress(self, objective_id: str, amount: int = 1) -> bool:
    """
    Update an objective's progress by a specified amount.
    
    Args:
        objective_id: The ID of the objective to update
        amount: The amount of progress to add
        
    Returns:
        bool: True if the objective was updated, False if not found
    """
    for objective in self.objectives:
        if objective.get("id") == objective_id:
            # Update progress
            old_amount = objective.get("current_amount", 0)
            required = objective.get("required_amount", 1)
            new_amount = min(old_amount + amount, required)
            objective["current_amount"] = new_amount
            
            # Check if completed
            if new_amount >= required:
                objective["completed"] = True
                
                # Check if quest is now completed (all non-optional objectives)
                required_objectives = [obj for obj in self.objectives if not obj.get("optional", False)]
                if all(obj.get("completed", False) for obj in required_objectives):
                    self.complete("succeeded")
            
            self._mark_dirty()
            return True
    return False
```

## 5. Quest Rewards Implementation

Enhance the Quest entity to handle rewards:

```python
# In the Quest entity class (app/game_state/entities/quest.py)

def set_rewards(self, gold: int = 0, experience: int = 0, items: List[Dict[str, Any]] = None,
               reputation: Dict[str, int] = None) -> None:
    """
    Set the rewards for completing this quest.
    
    Args:
        gold: Amount of gold to reward
        experience: Amount of XP to reward
        items: List of item dictionaries (id, amount, etc.)
        reputation: Dictionary mapping faction IDs to reputation amounts
    """
    self.rewards = {
        "gold": gold,
        "experience": experience,
        "items": items or [],
        "reputation": reputation or {}
    }
    self._mark_dirty()

def add_item_reward(self, item_id: str, amount: int = 1, quality: Optional[str] = None) -> None:
    """
    Add an item reward to this quest.
    
    Args:
        item_id: The ID of the item to reward
        amount: Number of items to give
        quality: Optional quality level of the item
    """
    if "items" not in self.rewards:
        self.rewards["items"] = []
    
    self.rewards["items"].append({
        "item_id": item_id,
        "amount": amount,
        "quality": quality
    })
    self._mark_dirty()

def get_gold_reward(self) -> int:
    """Get the gold reward amount"""
    return self.rewards.get("gold", 0)

def get_experience_reward(self) -> int:
    """Get the experience reward amount"""
    return self.rewards.get("experience", 0)

def get_item_rewards(self) -> List[Dict[str, Any]]:
    """Get the list of item rewards"""
    return self.rewards.get("items", [])

def get_reputation_rewards(self) -> Dict[str, int]:
    """Get the reputation rewards by faction"""
    return self.rewards.get("reputation", {})
```

## 6. Quest Assignment Logic

Add methods to make quests available and track assignments:

```python
# In the Quest entity class (app/game_state/entities/quest.py)

def make_available_at_location(self, location_id: str, start_time: Optional[float] = None,
                              end_time: Optional[float] = None) -> None:
    """
    Make this quest available at a specific location.
    
    Args:
        location_id: ID of the location (settlement or area)
        start_time: Optional timestamp when quest becomes available
        end_time: Optional timestamp when quest expires
    """
    if location_id.startswith("settlement_"):
        self.settlement = location_id
    else:
        self.area = location_id
    
    # Set availability window if provided
    if start_time:
        self.set_property("available_from", start_time)
    if end_time:
        self.set_property("available_until", end_time)
    
    self._mark_dirty()

def is_available_to_player(self, player_id: str) -> bool:
    """
    Check if this quest is available to a specific player.
    
    Args:
        player_id: The ID of the player
        
    Returns:
        bool: True if the player can take this quest
    """
    # Check quest status
    if self.status != "inactive":
        return False
    
    # Check availability window
    current_time = import_timestamp()
    start_time = self.get_property("available_from")
    end_time = self.get_property("available_until")
    
    if start_time and current_time < start_time:
        return False
    if end_time and current_time > end_time:
        return False
    
    # Check level requirements
    min_level = self.get_property("min_level")
    if min_level:
        player_level = self.get_property(f"player_{player_id}_level")
        if not player_level or player_level < min_level:
            return False
    
    # Check prerequisite quests
    prerequisites = self.prerequisites
    for prereq in prerequisites:
        if not self.get_property(f"player_{player_id}_completed_{prereq}"):
            return False
    
    return True
```

## 7. Quest Progression Tracking

Add methods for tracking and updating quest progress:

```python
# In QuestService class (app/game_state/services/quest_service.py)

async def update_quest_progress_from_event(self, event_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Update all relevant quests based on a game event.
    
    Args:
        event_data: Dictionary with event details
            
    Returns:
        List of quest update results
    """
    # Extract event information
    event_type = event_data.get("type")
    player_id = event_data.get("player_id")
    target_id = event_data.get("target_id")
    location_id = event_data.get("location_id")
    amount = event_data.get("amount", 1)
    
    if not player_id:
        return [{"status": "error", "message": "No player ID provided"}]
    
    # Get active quests for the player
    player_quests = self.quest_manager.get_player_quests(player_id)
    active_quests = [q for q in player_quests if q.status == "active"]
    
    results = []
    
    for quest in active_quests:
        # Check each objective for this quest
        for objective in quest.objectives:
            # Skip completed objectives
            if objective.get("completed", False):
                continue
            
            # Check if this event satisfies the objective
            matches = self._does_event_match_objective(
                event_type, target_id, location_id, objective
            )
            
            if matches:
                # Update the objective progress
                objective_id = objective.get("id")
                result = await self.update_objective_progress(
                    quest.id, objective_id, amount
                )
                results.append(result)
    
    return results

def _does_event_match_objective(self, event_type: str, target_id: str, 
                              location_id: str, objective: Dict[str, Any]) -> bool:
    """Check if an event matches an objective's requirements"""
    # Match based on objective target
    objective_target = objective.get("target")
    if objective_target and objective_target != target_id:
        return False
    
    # Match based on objective location
    objective_location = objective.get("location_id")
    if objective_location and objective_location != location_id:
        return False
    
    # Match based on event type and objective type
    objective_type = objective.get("type", "interact")
    
    if objective_type == "kill" and event_type == "entity_defeated":
        return True
    elif objective_type == "collect" and event_type == "item_acquired":
        return True
    elif objective_type == "visit" and event_type == "location_visited":
        return True
    elif objective_type == "interact" and event_type == "entity_interaction":
        return True
    elif objective_type == "craft" and event_type == "item_crafted":
        return True
    
    return False
```

## 8. Event Triggers

Create a system to trigger quest events:

```python
# app/workers/event_worker.py
from workers.celery_app import app
from database.connection import SessionLocal
from app.game_state.services.quest_service import QuestService
import logging
import asyncio
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

@app.task
def process_game_event(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a game event and update quests accordingly.
    
    Args:
        event_data: Dictionary with event details
            
    Returns:
        Dict with status and affected quests
    """
    event_type = event_data.get("type")
    logger.info(f"Processing game event: {event_type}")
    
    db = SessionLocal()
    try:
        # Create quest service
        quest_service = QuestService(db)
        
        # Update quests based on this event
        results = asyncio.run(quest_service.update_quest_progress_from_event(event_data))
        
        # Find successful updates
        updated_quests = [
            result for result in results 
            if result.get("status") == "success"
        ]
        
        logger.info(f"Updated {len(updated_quests)} quests from event {event_type}")
        
        return {
            "status": "success",
            "event_type": event_type,
            "updated_quests": len(updated_quests),
            "quest_updates": results
        }
    
    except Exception as e:
        logger.exception(f"Error processing game event: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()
```

## Examples of Quest Usage

### Example 1: Creating a Simple Fetch Quest

```python
# Creating a basic fetch quest
quest_data = {
    "name": "Bring Me Herbs",
    "description": "The village healer needs herbs for medicine.",
    "type": "fetch",
    "area_id": "area_forest_1",
    "settlement_id": "settlement_village_1",
    "difficulty": 1,
    "quest_giver_id": "npc_healer_1",
    "rewards": {
        "gold": 50,
        "experience": 100,
        "items": [
            {"item_id": "potion_health_1", "amount": 2}
        ]
    },
    "objectives": [
        {
            "id": "obj_1",
            "description": "Collect healing herbs in the forest",
            "type": "collect",
            "target": "item_herb_healing",
            "required_amount": 5,
            "location_id": "area_forest_1"
        },
        {
            "id": "obj_2",
            "description": "Return the herbs to the village healer",
            "type": "interact",
            "target": "npc_healer_1",
            "required_amount": 1,
            "location_id": "settlement_village_1"
        }
    ]
}

# Create the quest
from app.workers.quest_worker import create_quest
result = create_quest(quest_data)
quest_id = result["quest_id"]

# Assign to a player
from app.workers.quest_worker import assign_quest_to_player
assign_quest_to_player(quest_id, "player_1")

# Update objective progress when player collects herbs
from app.workers.event_worker import process_game_event
process_game_event({
    "type": "item_acquired",
    "player_id": "player_1",
    "target_id": "item_herb_healing",
    "location_id": "area_forest_1",
    "amount": 3
})

# Update again when player collects more herbs
process_game_event({
    "type": "item_acquired",
    "player_id": "player_1",
    "target_id": "item_herb_healing",
    "location_id": "area_forest_1",
    "amount": 2
})

# Complete quest when player returns to healer
process_game_event({
    "type": "entity_interaction",
    "player_id": "player_1",
    "target_id": "npc_healer_1",
    "location_id": "settlement_village_1"
})
```

### Example 2: Creating a Multi-Stage Quest Chain

```python
# First quest in chain
quest_data1 = {
    "name": "Investigate the Ruins",
    "description": "Scouts report strange lights at the old ruins.",
    "type": "exploration",
    "area_id": "area_ruins_1",
    "settlement_id": "settlement_town_1",
    "difficulty": 2,
    "quest_giver_id": "npc_mayor_1",
    "rewards": {
        "gold": 100,
        "experience": 200
    },
    "objectives": [
        {
            "id": "obj_1",
            "description": "Travel to the ruins",
            "type": "visit",
            "target": "area_ruins_1",
            "required_amount": 1
        },
        {
            "id": "obj_2",
            "description": "Find evidence of recent activity",
            "type": "interact",
            "target": "interact_evidence_1",
            "required_amount": 1,
            "location_id": "area_ruins_1"
        }
    ]
}

# Create first quest
result1 = create_quest(quest_data1)
quest_id1 = result1["quest_id"]

# Second quest in chain (will be available after first is complete)
quest_data2 = {
    "name": "Confront the Cultists",
    "description": "Stop the cultists' ritual before it's too late!",
    "type": "combat",
    "area_id": "area_ruins_underground",
    "difficulty": 3,
    "quest_giver_id": "npc_mayor_1",
    "rewards": {
        "gold": 300,
        "experience": 500,
        "items": [
            {"item_id": "weapon_magic_staff", "amount": 1, "quality": "rare"}
        ]
    },
    "objectives": [
        {
            "id": "obj_1",
            "description": "Find the hidden entrance",
            "type": "interact",
            "target": "interact_hidden_entrance",
            "required_amount": 1,
            "location_id": "area_ruins_1"
        },
        {
            "id": "obj_2",
            "description": "Defeat cultist leader",
            "type": "kill",
            "target": "npc_cultist_leader",
            "required_amount": 1,
            "location_id": "area_ruins_underground"
        }
    ],
    "prerequisites": [quest_id1]  # The first quest must be completed
}

# Create second quest (will be inactive until first is completed)
result2 = create_quest(quest_data2)
```

These examples and components provide a complete framework for implementing quests in your game. The system is flexible enough to handle various quest types, objectives, and reward structures while maintaining a clean separation of concerns between different system layers.