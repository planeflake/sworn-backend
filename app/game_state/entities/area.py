# Fix import path
from app.models.animals import Animal

"""
Areas

"""

class Area:
    """
    Represents a game area (e.g. a forest, a mountain range, etc.)
    """
    def __init__(self, name, description, area_type, area_id):
        self.area_name = name  # Changed to match DB schema
        self.area_id = area_id
        self.description = description
        self.area_type = area_type
        self._is_dirty = False

    def set_name(self, name):
        self.area_name = name  # Changed to match DB schema
        self._is_dirty = True

    def set_description(self, description):
        self.description = description
        self._is_dirty = True

    def set_area_type(self, area_type):
        self.area_type = area_type
        self._is_dirty = True

    def set_controlling_faction(self, faction_id):
        self.controlling_faction = faction_id
        self._is_dirty = True

    def set_dominant_species(self, animal_id):
        self.dominant_species = animal_id or None
        self._is_dirty = True

    def set_weather(self, weather_id):
        self.weather = weather_id
        self._is_dirty = True

    def get_property(self, property_name, default=None):
        return getattr(self, property_name, default)
    
    def set_property(self, property_name, value):
        setattr(self, property_name, value)
        self._is_dirty = True

    def add_area_quest(self, quest_id):
        self.quests.append(quest_id)
        self._is_dirty = True

    def complete_area_quest(self, quest_id):
        if quest_id in self.quests:
            self.quests.remove(quest_id)
            self._is_dirty = True

    def is_dirty(self):
        return self._is_dirty
        
    def mark_clean(self):
        """Mark this entity as having no unsaved changes."""
        self._is_dirty = False
    
    def to_dict(self):
        return {
            "area_name": self.area_name,  # Changed to match DB schema
            "description": self.description,
            "area_type": self.area_type,
            "controlling_faction": self.controlling_faction,
            "dominant_species": self.dominant_species,
            "weather": self.weather,
            "quests": self.quests
        }
    
    @classmethod
    def from_dict(cls, data):
        area = cls(
            name=data.get("area_name"),  # Changed to match DB schema
            description=data.get("description"),
            area_type=data.get("area_type"),
            area_id=data.get("area_id")
        )
        area.controlling_faction = data.get("controlling_faction")
        area.dominant_species = data.get("dominant_species")
        area.weather = data.get("weather")
        area.quests = data.get("quests")
        return area