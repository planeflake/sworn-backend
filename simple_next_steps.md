# Simple Next Steps for Sworn Backend

## Remaining Tasks

1. **Settlement Entity Standardisation**
   - Standardise property access methods to match other entities:
     ```python
     # In app/game_state/entities/settlement.py
     
     # Current inconsistent approach
     # Using direct property access in some places
     self.name = "Settlement"
     # But using properties dictionary in others
     self.properties["population"] = 100
     
     # Standardised approach
     # Use consistent set_property/get_property methods:
     def set_property(self, key: str, value: Any):
         """Set a property value."""
         self.properties[key] = value
         self._dirty = True
         
     def get_property(self, key: str, default: Any = None) -> Any:
         """Get a property value."""
         return self.properties.get(key, default)
     ```

2. **Manager Standardisation**
   - Standardise method naming across all managers:
     ```python
     # Instead of inconsistent method names:
     get_animals()  # In AnimalManager
     find_entities_by_x()  # In other managers
     
     # Standardise to consistent naming:
     find_animals_by_x()  # For consistency with other managers
     ```

3. **Create item_worker_new.py**
   - Follow the pattern of animal_worker_new.py
   - Implement core functionalities:
     ```python
     @shared_task(name="item_worker.process_items")
     def process_items(world_id: str = None):
         """Process all items in the world."""
         # Implementation here
     
     @shared_task(name="item_worker.decay_items")
     def decay_items():
         """Apply decay to items based on their properties."""
         # Implementation here
     ```

4. **Create settlement_service.py**
   - Highest priority from NEXT_STEPS.md
   - Follow trader_service.py pattern
   - Implement key methods:
     ```python
     def update_settlement(self, settlement_id: str):
         """Update a settlement's state."""
         # Implementation
     
     def process_resources(self, settlement_id: str):
         """Process resource production and consumption."""
         # Implementation
     
     def handle_population_growth(self, settlement_id: str):
         """Handle population growth and housing."""
         # Implementation
     ```

5. **Documentation**
   - Add missing docstrings in these specific locations:
     
     ### Missing Docstrings Completely
     - `/app/game_state/entities/inventory.py`: `__eq__` method
     - `/app/game_state/entities/building.py`: Multiple methods with indentation issues
       - `is_upgradeable`, `upgrade_building`, `repair`, `evict_inhabitant`
       - `collect_taxes`, `assign_faction`, `discover`, `hide`
       - `calculate_defense`, `generate_event`, `generate_repair_costs`
     - `/app/game_state/entities/item.py`: Update `set_is_stolen` docstring to mention the attribute
      
     ### Missing Args/Returns Formatting
     - `/app/game_state/entities/settlement.py`: Fix indentation in `is_under_repair` Returns tag
     - `/app/game_state/entities/equipment.py`: 
       - Add Returns tag with type annotation to `get_equipped_items`
       - Fix parameter documentation in `__init__` to match attribute usage
     - `/app/game_state/managers/equipment_manager.py`: 
       - Add Returns in docstring for `find_equipment_by_property`
     
     ### Class-Level Docstrings
     - `/app/game_state/entities/item.py`: Update Item class docstring to be specific, not template text
     - `/app/game_state/entities/building.py`: Update Building class docstring to be specific

   - Follow consistent triple-quote multi-line format with Args/Returns:
     ```python
     def some_method(self, param1: str, param2: int) -> bool:
         """
         Short description of what this method does.
         
         Args:
             param1 (str): Description of param1
             param2 (int): Description of param2
             
         Returns:
             bool: Description of return value
         """
         # Method implementation
     ```

## Integration Strategy

For each task:

1. **Implement the changes** with proper error handling and tests
2. **Run unit tests** to ensure everything works correctly
3. **Update the history/completed_tasks.md** file with your progress
4. **Check for consistency** with the rest of the codebase

## Testing Strategy

For each new component:

1. **Unit Tests**: Create tests for main functionality
   ```bash
   python -m unittest tests/game_state/entities/test_settlement.py
   ```

2. **Integration Tests**: Test the service with managers
   ```bash
   python -m unittest tests/game_state/services/test_settlement_service.py
   ```

3. **API Testing**: Use an API client to test endpoints
   ```
   GET /settlement/{settlement_id}
   ```
   
## NEXT_STEPS.md Alignment

These tasks align with the following items from NEXT_STEPS.md:

1. **Create Service Layer Classes** - settlement_service.py
2. **Update Celery Workers** - item_worker_new.py
3. **Complete Entity Implementations** - Settlement entity standardisation
4. **Complete Manager Implementations** - Manager standardisation

After completing these tasks, you'll be ready to move on to the more advanced features outlined in NEXT_STEPS.md.