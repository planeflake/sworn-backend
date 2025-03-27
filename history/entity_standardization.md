# Entity Standardization

## Overview

This document outlines the standardization applied to all entity classes in the game state architecture. The goal is to ensure consistent patterns for property access, state tracking, and serialization across all entity types.

## Key Standardization Features

1. **Property Storage**
   - All entity state is stored in a `properties` dictionary
   - Direct instance attributes are used only for essential fields (entity_id, properties, _dirty)

2. **Accessor Methods**
   - `set_property(key, value)` - Sets a property and marks entity as dirty
   - `get_property(key, default)` - Gets a property or returns default value

3. **Relationship Management**
   - `set_relation(entity_id, relation_type, value)` - Sets a relationship to another entity
   - `get_relation(entity_id, relation_type, default)` - Gets a relationship value

4. **State Tracking**
   - `is_dirty()` - Returns whether entity has unsaved changes
   - `mark_clean()` - Marks entity as having no unsaved changes

5. **Serialization**
   - `to_dict()` - Converts entity to dictionary for storage 
   - `from_dict(data)` - Creates entity from dictionary data

## Standardized Entity Structure

```python
class Entity:
    def __init__(self, entity_id: str):
        self.entity_id = entity_id
        self.properties = {}  # Dictionary to store all properties
        self._dirty = False
        
        # Initialize properties with default values
        self.set_property("name", None)
        self.set_property("description", None)
        # ... more default properties

    def set_property(self, key: str, value: Any):
        self.properties[key] = value
        self._dirty = True
    
    def get_property(self, key: str, default: Any = None) -> Any:
        return self.properties.get(key, default)
    
    # ... other standard methods
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "properties": self.properties
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Entity':
        entity = cls(entity_id=data["entity_id"])
        entity.properties = data.get("properties", {})
        return entity
```

## Benefits of Standardization

1. **Uniform State Tracking**
   - All property changes are automatically tracked via the `_dirty` flag
   - Consistent pattern for determining when an entity needs to be saved

2. **Simplified Serialization**
   - Serialization only needs to handle the `properties` dictionary
   - Reduces risk of missing properties during serialization

3. **Consistent Access Patterns**
   - All code accessing entity properties follows the same pattern
   - Reduces bugs from inconsistent property access

4. **Centralized Validation**
   - Property setters can implement validation in one place
   - Easier to add global validation or transformation rules

5. **Type Safety**
   - All property accesses use default values for proper type safety
   - Prevents errors from accessing undefined properties

## Implementation Details

The standardization was applied to the following entity classes:

1. `Wildlife` (animal.py)
2. `Item` (item.py)
3. `Building` (building.py)
4. `Settlement` (settlement.py)

A canonical template file (entity_template.py) was created to serve as the reference implementation for all future entity classes.

## Usage Guidelines

1. **Property Access**
   - Always use `entity.get_property("property_name")` instead of `entity.property_name`
   - Always use `entity.set_property("property_name", value)` instead of `entity.property_name = value`

2. **Entity Creation**
   - Initialize with minimal required attributes (typically just ID)
   - Use set_property to establish all default values

3. **Custom Getters/Setters**
   - Create custom getter/setter methods for properties needing special handling
   - These methods should use get_property/set_property internally

4. **Entity-Specific Methods**
   - Entity-specific behavior should be implemented as methods
   - Methods should use get_property/set_property for state access

5. **Relation Management**
   - Use set_relation/get_relation for managing relationships between entities