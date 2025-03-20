import json
import uuid
import logging as logger

class AnimalGroupEntity:
    """
    Entity representing a group of animals (herd).
    """
    def __init__(self, group_id: str = None):
        self.group_id = group_id or str(uuid.uuid4())
        self.group_name = ""
        self.description = ""
        # Store member animal IDs as a list
        self.member_ids = []
        self._dirty = False

    def set_group_name(self, name: str):
        self.group_name = name
        self._dirty = True
        logger.info(f"Set group name for {self.group_id}: {name}")

    def set_description(self, description: str):
        self.description = description
        self._dirty = True
        logger.info(f"Set description for group {self.group_id}: {description}")

    def add_member(self, animal_id: str):
        if animal_id not in self.member_ids:
            self.member_ids.append(animal_id)
            self._dirty = True
            logger.info(f"Added animal {animal_id} to group {self.group_id}")

    def remove_member(self, animal_id: str):
        if animal_id in self.member_ids:
            self.member_ids.remove(animal_id)
            self._dirty = True
            logger.info(f"Removed animal {animal_id} from group {self.group_id}")

    def clear_members(self):
        self.member_ids = []
        self._dirty = True
        logger.info(f"Cleared all members from group {self.group_id}")

    def is_dirty(self) -> bool:
        """Returns True if there are unsaved changes."""
        return self._dirty

    def mark_clean(self):
        """Marks the entity as clean (no unsaved changes)."""
        self._dirty = False

    def to_dict(self) -> dict:
        """
        Serialize the group data to a dictionary.
        """
        return {
            "group_id": self.group_id,
            "group_name": self.group_name,
            "description": self.description,
            "member_ids": self.member_ids
        }

    @classmethod
    def from_dict(cls, data: dict):
        """
        Create an AnimalGroupEntity from a dictionary.
        """
        group = cls(group_id=data.get("group_id"))
        group.group_name = data.get("group_name", "")
        group.description = data.get("description", "")
        group.member_ids = data.get("member_ids", [])
        return group
