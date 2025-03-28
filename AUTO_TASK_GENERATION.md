# Automatic Task Generation System

This document outlines the implementation steps required to develop a robust automated task generation system for traders and settlements in the Sworn backend.

## Core Concept

The game world should dynamically create meaningful tasks for players based on in-game events, resource needs, and the current state of traders and settlements. These tasks will:

1. Create emergent gameplay opportunities
2. Provide a steady stream of content without manual design
3. Reinforce the simulation-driven nature of the game world
4. Respond to player actions and inactions
5. Create a more realistic and responsive game economy

## Design Philosophy

The automatic task generation system follows these principles:

1. **Context-Awareness**: Tasks should be generated based on the specific circumstances of traders, settlements, and the world state
2. **Probabilistic Generation**: Use weighted probability systems rather than fixed schedules to create unpredictable but logical task patterns
3. **Dynamic Rewards**: Reward scaling should reflect task difficulty, urgency, and current economic conditions
4. **Minimal Disruption**: The system should integrate with existing code patterns and enhance rather than replace current functionality

## Existing Foundation

We already have:
- A task system with basic structure (TaskService, TaskManager, Task entity)
- Random trader assistance task generation (create_random_trader_tasks)
- Task types that can be assigned to players
- Task tracking and completion mechanisms

## Implementation Plan

### Phase 1: Trader Event-Based Tasks (Low-Hanging Fruit)

1. **Enhance Trader Journey Event System**
   - Update `trader_service.py` to trigger events during area traversal
   - Create event-handling system in `continue_area_travel` method
   - Add probability checks for different event types
   
   **Pointer**: The `trader_service.py` file already has the `continue_area_travel` method (line ~390) that tracks trader movement through areas. This is the ideal place to inject an event check.
   
   **Integration Point**: In the `continue_area_travel` method, look for the section after the trader's journey progress is updated, around line 478:
   ```python
   # Calculate journey progress percentage
   trader_db.journey_progress = int((current_position / (len(path) - 1)) * 100)
   
   # Commit changes to database
   self.db.commit()
   
   # Get area info for logging
   next_area = self.db.query(Areas).filter(Areas.area_id == next_area_id).first()
   ```
   
   This is where you should add event detection before the trader moves to the next area.
   
   **Example**: When a trader enters a dangerous area with low health, it's a perfect opportunity to generate a task:
   ```python
   # In continue_area_travel method, after calculating journey progress
   # First, get area details to check danger level
   next_area = self.db.query(Areas).filter(Areas.area_id == next_area_id).first()
   area_name = next_area.area_name if next_area and hasattr(next_area, 'area_name') else "unknown area"
   
   # Check for potential events - use weighted probability system
   danger_level = getattr(next_area, 'danger_level', 1) or 1
   cart_health = trader_db.cart_health if hasattr(trader_db, 'cart_health') else 100
   
   # Higher danger + lower cart health = higher event chance
   event_chance = (danger_level / 10) + ((100 - cart_health) / 100)
   
   # Cap chance at reasonable levels
   event_chance = min(0.8, max(0.05, event_chance))
   logger.info(f"Trader {trader_name} event chance: {event_chance:.2f} in {area_name} (danger: {danger_level}, cart: {cart_health}%)")
   
   if random.random() < event_chance:
       # Generate an event - most likely a cart breakdown if cart health is low
       if cart_health < 50:
           event_type = "broken_cart"
           severity = max(1, int((50 - cart_health) / 10))  # 1-5 severity
           
           logger.info(f"Trader {trader_name} experiences cart breakdown in {area_name} (severity: {severity})")
           
           # Create a task for this event
           await self._create_event_based_task(trader_id, next_area_id, {
               "event_type": event_type,
               "severity": severity,
               "area_name": area_name,
               "trader_name": trader_name
           })
           
           # Halt trader's journey until task is resolved
           trader_db.can_move = False
           trader_db.path_position = current_position  # Stay at current position
           self.db.commit()
           
           return {
               "status": "success",
               "action": "event_halted",
               "event_type": event_type,
               "area": area_name
           }
   ```
   
   **Compatibility**: This approach doesn't disrupt existing functionality - it simply adds an extra check that may occasionally halt trader progress when events occur, creating organic gameplay opportunities.

2. **Implement Trader Event to Task Pipeline**
   - Define clear events (cart damage, animal illness, bandit attacks)
   - Create helper functions to transform events into tasks
   - Integrate with existing `create_trader_assistance_task` function
   
   **Pointer**: The `create_trader_assistance_task` function already exists in `trader_worker.py` (around line 230) and defines several issue types like "bandit_attack" and "broken_cart". Use these existing types as your event categories.
   
   **Integration Point**: First, examine the existing function to understand its parameters:
   
   ```python
   # In trader_worker.py, look at the existing function
   def create_trader_assistance_task(trader_id, area_id, world_id, issue_type):
       """Create a task for assisting a trader who's encountered an issue."""
       logger.info(f"Creating assistance task for trader {trader_id} in area {area_id}")
       
       db = SessionLocal()
       try:
           # Get necessary details
           trader = db.query(Traders).filter(Traders.trader_id == trader_id).first()
           area = db.query(Areas).filter(Areas.area_id == area_id).first()
           # ... rest of function ...
   ```
   
   **Implementation**: Create a new helper method in `trader_service.py` that maps events to tasks:
   
   ```python
   async def _create_event_based_task(self, trader_id: str, area_id: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
       """Create a player task based on a trader travel event."""
       try:
           # Import the task creation function
           from app.workers.trader_worker import create_trader_assistance_task
           
           # Get necessary info
           trader_db = self.db.query(Traders).filter(Traders.trader_id == trader_id).first()
           if not trader_db or not trader_db.world_id:
               logger.error(f"Cannot create task: Trader {trader_id} not found or missing world_id")
               return {"status": "error", "message": "Trader or world not found"}
           
           world_id = trader_db.world_id
           event_type = event_data["event_type"]
           severity = event_data.get("severity", 1)
           trader_name = event_data.get("trader_name", trader_db.npc_name or f"Trader {trader_id[:8]}")
           area_name = event_data.get("area_name", "unknown area")
           
           # Log task creation attempt
           logger.info(f"Creating {event_type} task for {trader_name} in {area_name} (severity: {severity})")
           
           # Modify reward based on severity (existing function doesn't support custom rewards directly)
           # We'll need to enhance this in a future update, but for now we'll use the base function
           
           # Create the task using the existing function
           result = create_trader_assistance_task(
               trader_id=trader_id,
               area_id=area_id,
               world_id=world_id,
               issue_type=event_type
           )
           
           # Log the result
           if result.get("status") == "success":
               logger.info(f"Successfully created {event_type} task {result.get('task_id')} for {trader_name}")
               
               # Mark the trader as waiting for assistance
               trader_db.can_move = False
               trader_db.active_task_id = result.get("task_id")
               self.db.commit()
               
               # Also update entity model for consistency
               trader_entity = await self.trader_manager.load_trader(trader_id)
               if trader_entity:
                   trader_entity.set_property("can_move", False)
                   trader_entity.set_property("active_task_id", result.get("task_id"))
                   await self.trader_manager.save_trader(trader_entity)
           else:
               logger.error(f"Failed to create task: {result.get('message')}")
           
           return result
           
       except Exception as e:
           logger.exception(f"Error creating event-based task: {e}")
           return {"status": "error", "message": str(e)}
   ```
   
   **Event Type Mapping**: Use the existing issue types defined in `trader_worker.py`:
   
   ```python
   # Existing issue types from create_random_trader_tasks in trader_worker.py
   issue_types = [
       "bandit_attack",  # Combat encounter - occurs in dangerous areas
       "broken_cart",    # Repair skill needed - more likely with low cart health
       "sick_animals",   # Medicine skill needed - more common in extreme weather
       "lost_cargo",     # Search/tracking task - can happen on rough terrain
       "food_shortage"   # Resource gathering - more common on long journeys
   ]
   ```
   
   **Enhancement Plan**: In the future, you should enhance the `create_trader_assistance_task` function to accept severity and custom rewards, but this implementation provides immediate value while respecting the existing code structure.

3. **Add Contextual Awareness**
   - Make event likelihood depend on area danger level
   - Consider trader's equipment, guards, and resources
   - Account for seasonal effects (more breakdowns in winter, etc.)
   
   **Pointer**: The `trader_service.py` already tracks area danger levels and trader properties. Use these to make events more realistic.
   
   **Integration Point**: Expand the `_check_for_travel_events` method we started earlier to include comprehensive context factors:
   
   ```python
   async def _check_for_travel_events(self, trader_id: str, area_id: str) -> Dict[str, Any]:
       """Check if any travel events occur for a trader in an area, with comprehensive context awareness."""
       try:
           # Get all necessary data for context-aware decisions
           trader_db = self.db.query(Traders).filter(Traders.trader_id == trader_id).first()
           area = self.db.query(Areas).filter(Areas.area_id == area_id).first()
           
           if not trader_db or not area:
               logger.warning(f"Missing data for event check: trader={trader_id}, area={area_id}")
               return {"event_triggered": False}
           
           # Get trader context factors
           trader_name = trader_db.npc_name or f"Trader {trader_id[:8]}"
           cart_health = getattr(trader_db, 'cart_health', 100) or 100
           hired_guards = getattr(trader_db, 'hired_guards', 0) or 0
           journey_days = 0
           if hasattr(trader_db, 'journey_started') and trader_db.journey_started:
               from datetime import datetime
               journey_days = (datetime.now() - trader_db.journey_started).days
           
           # Get area context factors
           area_name = getattr(area, 'area_name', "Unknown Area")
           danger_level = getattr(area, 'danger_level', 1) or 1
           area_type = getattr(area, 'area_type', "wilderness")
           terrain_difficulty = getattr(area, 'terrain_difficulty', 1) or 1
           
           # Get world context (season, weather)
           world = None
           current_season = "summer"  # Default
           current_weather = "clear"  # Default
           
           if hasattr(trader_db, 'world_id') and trader_db.world_id:
               world = self.db.query(Worlds).filter(Worlds.world_id == trader_db.world_id).first()
               if world:
                   current_season = getattr(world, 'current_season', "summer")
                   current_weather = getattr(world, 'current_weather', "clear")
           
           logger.info(f"Context check for trader {trader_name} in {area_name}:")
           logger.info(f"  Trader: cart={cart_health}%, guards={hired_guards}, journey_days={journey_days}")
           logger.info(f"  Area: danger={danger_level}, type={area_type}, terrain={terrain_difficulty}")
           logger.info(f"  World: season={current_season}, weather={current_weather}")
           
           # Base chance modified by multiple factors
           base_chance = 0.1  # 10% base chance of an event
           
           # === AREA MODIFIERS ===
           # Danger level increases chance
           area_factor = danger_level * 0.05  # +5% per danger level
           
           # Terrain difficulty affects certain event types
           terrain_factor = terrain_difficulty * 0.03  # +3% per terrain difficulty level
           
           # === TRADER MODIFIERS ===
           # Cart health - lower health increases chance of breakdown
           cart_factor = 0
           if cart_health < 80:
               cart_factor = (80 - cart_health) * 0.005  # Up to +40% at 0% health
           
           # Guard protection reduces chance of certain events
           guard_protection = min(hired_guards * 0.1, 0.5)  # Max 50% reduction
           
           # Journey length - longer journeys increase certain risks
           journey_factor = min(journey_days * 0.02, 0.2)  # Up to +20% for 10+ day journeys
           
           # === WORLD MODIFIERS ===
           # Season affects event chance and types
           season_modifier = 1.0  # Multiplier
           if current_season == "winter":
               season_modifier = 1.5  # 50% more events in winter
           elif current_season == "autumn":
               season_modifier = 1.2  # 20% more events in autumn
           
           # Weather affects event chance and types
           weather_modifier = 1.0  # Multiplier
           if current_weather in ["rain", "storm", "snow"]:
               weather_modifier = 1.4  # 40% more events in bad weather
           elif current_weather == "fog":
               weather_modifier = 1.2  # 20% more events in fog
           
           # === COMBINE FACTORS ===
           # Calculate final chance
           final_chance = (base_chance + area_factor + terrain_factor + cart_factor + journey_factor)
           final_chance = final_chance * season_modifier * weather_modifier
           
           # Cap at reasonable range
           final_chance = min(0.8, max(0.05, final_chance))
           
           logger.info(f"Final event chance: {final_chance:.2f} (base={base_chance}, area={area_factor}, terrain={terrain_factor}, " +
                       f"cart={cart_factor}, journey={journey_factor}, season={season_modifier}x, weather={weather_modifier}x)")
           
           # Roll for event
           if random.random() < final_chance:
               logger.info(f"Event triggered for trader {trader_name} in {area_name}")
               
               # Now decide event type based on context factors
               # We'll build a pool of potential events with weights
               event_pool = []
               
               # Cart-related events more likely with low cart health
               if cart_health < 70:
                   weight = (70 - cart_health) / 10  # 0.1 to 7 weight
                   event_pool.append(("broken_cart", weight))
               
               # Bandit attacks affected by guards and danger level
               if danger_level >= 2:
                   # Base weight from danger level
                   weight = danger_level - 1  # 1 to 5 weight
                   
                   # Reduce by guard protection
                   if hired_guards > 0:
                       # Guards provide protection
                       weight *= max(0.2, 1.0 - guard_protection)
                   
                   # Weather reduces bandit activity
                   if current_weather in ["storm", "snow"]:
                       weight *= 0.5  # Half as likely in bad weather
                   
                   event_pool.append(("bandit_attack", weight))
               
               # Animal sickness more common in certain conditions
               if hasattr(trader_db, 'has_pack_animals') and trader_db.has_pack_animals:
                   weight = 1.0  # Base weight
                   
                   # Season affects animal health
                   if current_season == "winter":
                       weight *= 2.0  # Twice as likely in winter
                   elif current_season == "spring":
                       weight *= 1.5  # 50% more likely in spring (mud, etc.)
                   
                   # Weather affects animals
                   if current_weather in ["rain", "storm", "snow"]:
                       weight *= 1.5  # More likely in bad weather
                   
                   event_pool.append(("sick_animals", weight))
               
               # Lost cargo can happen on difficult terrain
               if terrain_difficulty >= 2:
                   weight = terrain_difficulty * 0.5  # 1.0 to 2.5 weight
                   
                   # Weather makes cargo problems worse
                   if current_weather in ["rain", "storm", "fog"]:
                       weight *= 1.5  # More likely in bad visibility
                   
                   event_pool.append(("lost_cargo", weight))
               
               # Food shortage on long journeys
               if journey_days >= 3:
                   weight = journey_days * 0.2  # 0.6 to 2.0+ weight
                   event_pool.append(("food_shortage", weight))
               
               # Ensure we have at least one event type
               if not event_pool:
                   # Fallback to generic cart issue
                   event_pool.append(("broken_cart", 1.0))
               
               # Log the event pool for debugging
               logger.info(f"Event pool: {event_pool}")
               
               # Select event based on weights
               total_weight = sum(weight for _, weight in event_pool)
               selection = random.uniform(0, total_weight)
               
               # Find the selected event
               current_weight = 0
               selected_event = event_pool[0][0]  # Default fallback
               for event, weight in event_pool:
                   current_weight += weight
                   if selection <= current_weight:
                       selected_event = event
                       break
               
               # Determine severity (1-5 scale)
               # Base on context factors relevant to the event type
               severity = 1  # Default mild severity
               
               if selected_event == "broken_cart":
                   # Severity based on cart health
                   severity = max(1, min(5, int(6 - (cart_health / 20))))
               elif selected_event == "bandit_attack":
                   # Severity based on danger level and guard count
                   severity = max(1, min(5, danger_level + 1 - (hired_guards // 2)))
               elif selected_event == "sick_animals":
                   # Severity based on weather and season
                   severity = 2  # Base severity
                   if current_weather in ["storm", "snow"]:
                       severity += 1
                   if current_season == "winter":
                       severity += 1
               elif selected_event == "lost_cargo":
                   # Severity based on terrain and weather
                   severity = max(1, min(5, terrain_difficulty + 
                                         (1 if current_weather in ["fog", "rain", "storm"] else 0)))
               elif selected_event == "food_shortage":
                   # Severity based on journey length
                   severity = max(1, min(5, journey_days // 2))
               
               logger.info(f"Selected event: {selected_event} (severity: {severity})")
               
               return {
                   "event_triggered": True,
                   "event_type": selected_event,
                   "severity": severity,
                   "area_name": area_name,
                   "trader_name": trader_name
               }
           
           return {"event_triggered": False}
           
       except Exception as e:
           logger.exception(f"Error checking for travel events: {e}")
           return {"event_triggered": False}
   ```
   
   **Key Context Factors**:
   
   1. **Trader Factors**:
      - Cart health: Lower health increases breakdown chance
      - Guards: More guards reduce bandit attack chance
      - Journey length: Longer journeys increase food shortage chance
      
   2. **Area Factors**:
      - Danger level: Higher danger increases bandit attack chance
      - Terrain difficulty: Difficult terrain increases cargo loss
      - Area type: Different areas have different event profiles
   
   3. **World Factors**:
      - Season: Winter increases animal sickness, mechanical problems
      - Weather: Rain, snow, fog affect different event types
      
   **Event Type Selection**: 
   - Uses weighted random selection instead of fixed thresholds
   - Includes multiple candidate events to avoid predictability
   - Severity scales logically with contributing factors

### Phase 2: Settlement Resource-Based Tasks

1. **Create Settlement Resource Monitoring**
   - Add resource tracking to the settlement entity
   - Implement thresholds for critical resource levels
   - Track resource consumption rates
   
   **Pointer**: Look at the existing settlement processing in `settlement_service.py` and check the database schema to determine how resources are stored.
   
   **Database Integration**: First, examine if you need to add new tables to track resources:
   
   ```python
   # If there isn't already a settlement resource table, create a migration to add one
   # Example migration file (use alembic to generate):
   
   """
   from alembic import op
   import sqlalchemy as sa
   from sqlalchemy.dialects.postgresql import UUID
   
   def upgrade():
       # Create table for settlement resources
       op.create_table(
           'settlement_resources',
           sa.Column('id', UUID, primary_key=True),
           sa.Column('settlement_id', UUID, sa.ForeignKey('settlements.settlement_id'), nullable=False),
           sa.Column('resource_type', sa.String(50), nullable=False),
           sa.Column('quantity', sa.Integer, nullable=False, default=0),
           sa.Column('last_updated', sa.DateTime, nullable=False, server_default=sa.func.now()),
           sa.Column('minimum_threshold', sa.Integer, nullable=False, default=0),
           sa.Column('consumption_rate', sa.Float, nullable=False, default=0.0),
           sa.UniqueConstraint('settlement_id', 'resource_type', name='uq_settlement_resource')
       )
   """
   ```
   
   **Model Integration**: If you need to create a new model class:
   
   ```python
   # In app/models/resource.py
   
   from app.models.core import Base
   from sqlalchemy import Column, String, Integer, Float, ForeignKey, DateTime, func
   from sqlalchemy.dialects.postgresql import UUID
   import uuid
   
   class SettlementResource(Base):
       __tablename__ = "settlement_resources"
       
       id = Column(UUID, primary_key=True, default=uuid.uuid4)
       settlement_id = Column(UUID, ForeignKey("settlements.settlement_id"), nullable=False)
       resource_type = Column(String(50), nullable=False)
       quantity = Column(Integer, nullable=False, default=0)
       last_updated = Column(DateTime, nullable=False, server_default=func.now())
       minimum_threshold = Column(Integer, nullable=False, default=0)
       consumption_rate = Column(Float, nullable=False, default=0.0)
       
       def to_dict(self):
           return {
               "resource_type": self.resource_type,
               "quantity": self.quantity,
               "minimum_threshold": self.minimum_threshold,
               "consumption_rate": self.consumption_rate,
               "last_updated": self.last_updated.isoformat() if self.last_updated else None
           }
   ```
   
   **Integration Point**: In the settlement worker or service, add a method to process resource consumption:
   
   ```python
   # In settlement_service.py
   def _update_resource_levels(self, settlement_id: str) -> Dict[str, Any]:
       """Update resource levels based on consumption and production."""
       try:
           # Get the settlement
           settlement = self.db.query(Settlements).filter(
               Settlements.settlement_id == settlement_id
           ).first()
           
           if not settlement:
               logger.error(f"Settlement {settlement_id} not found")
               return {"status": "error", "message": "Settlement not found"}
           
           settlement_name = settlement.settlement_name
           
           # Get population to calculate consumption rates
           population = getattr(settlement, 'population', 0) or 0
           
           # Get current resources
           from app.models.resource import SettlementResource
           resources = self.db.query(SettlementResource).filter(
               SettlementResource.settlement_id == settlement_id
           ).all()
           
           # If no resources found, initialize default resources
           if not resources:
               logger.info(f"Initializing default resources for settlement {settlement_name}")
               default_resources = [
                   {"type": "food", "quantity": population * 10, "threshold": population * 3, "rate": population * 0.2},
                   {"type": "wood", "quantity": population * 5, "threshold": population * 2, "rate": population * 0.1},
                   {"type": "stone", "quantity": population * 3, "threshold": population, "rate": population * 0.05},
                   {"type": "iron", "quantity": population * 1, "threshold": population // 2, "rate": population * 0.02},
                   {"type": "cloth", "quantity": population * 2, "threshold": population, "rate": population * 0.05}
               ]
               
               for res in default_resources:
                   self.db.add(SettlementResource(
                       settlement_id=settlement_id,
                       resource_type=res["type"],
                       quantity=res["quantity"],
                       minimum_threshold=res["threshold"],
                       consumption_rate=res["rate"]
                   ))
               
               self.db.commit()
               
               # Reload resources
               resources = self.db.query(SettlementResource).filter(
                   SettlementResource.settlement_id == settlement_id
               ).all()
           
           # Critical resources tracking
           critical_resources = []
           
           # Process each resource - consumption based on time since last update
           for resource in resources:
               # Calculate time since last update
               from datetime import datetime
               now = datetime.utcnow()
               time_diff = now - resource.last_updated
               days_passed = time_diff.total_seconds() / 86400  # Convert to days
               
               # Only process if at least 0.1 days have passed (about 2.4 hours)
               if days_passed >= 0.1:
                   # Calculate consumption
                   consumed = int(resource.consumption_rate * days_passed)
                   
                   # Update quantity
                   old_quantity = resource.quantity
                   resource.quantity = max(0, old_quantity - consumed)
                   resource.last_updated = now
                   
                   logger.info(f"Settlement {settlement_name}: {resource.resource_type} {old_quantity}->{resource.quantity} " + 
                               f"(-{consumed} over {days_passed:.1f} days)")
                   
                   # Check if resource is below critical threshold
                   if resource.quantity < resource.minimum_threshold:
                       critical_level = resource.quantity / max(1, resource.minimum_threshold)
                       critical_resources.append({
                           "resource_type": resource.resource_type,
                           "quantity": resource.quantity,
                           "threshold": resource.minimum_threshold,
                           "level_percentage": critical_level * 100,
                           "days_remaining": resource.quantity / max(0.1, resource.consumption_rate) if resource.consumption_rate > 0 else 999
                       })
           
           # Commit changes
           self.db.commit()
           
           if critical_resources:
               # Sort by days remaining (most urgent first)
               critical_resources.sort(key=lambda r: r["days_remaining"])
               
               logger.warning(f"Settlement {settlement_name} has {len(critical_resources)} critical resources:")
               for res in critical_resources:
                   logger.warning(f"  {res['resource_type']}: {res['quantity']}/{res['threshold']} " +
                                f"({res['level_percentage']:.1f}%, {res['days_remaining']:.1f} days left)")
               
               return {
                   "status": "critical",
                   "critical_resources": critical_resources,
                   "most_urgent": critical_resources[0]["resource_type"],
                   "settlement_name": settlement_name
               }
           
           return {
               "status": "ok",
               "message": f"Resources updated for settlement {settlement_name}"
           }
               
       except Exception as e:
           logger.exception(f"Error updating resource levels: {e}")
           return {"status": "error", "message": str(e)}
   ```
   
   **Schedule Integration**: Add this to the settlement worker's periodic tasks:
   
   ```python
   @app.task
   def update_all_settlement_resources(world_id: Optional[str] = None):
       """Update resource levels for all settlements."""
       logger.info(f"Updating resources for all settlements" + (f" in world {world_id}" if world_id else ""))
       
       db = SessionLocal()
       try:
           # Get all settlements
           query = db.query(Settlements)
           if world_id:
               query = query.filter(Settlements.world_id == world_id)
               
           settlements = query.all()
           logger.info(f"Processing resources for {len(settlements)} settlements")
           
           # Create service
           settlement_service = SettlementService(db)
           
           # Process each settlement
           critical_settlements = []
           for settlement in settlements:
               result = settlement_service._update_resource_levels(settlement.settlement_id)
               if result.get("status") == "critical":
                   critical_settlements.append({
                       "settlement_id": settlement.settlement_id,
                       "settlement_name": settlement.settlement_name,
                       "urgent_resource": result["most_urgent"]
                   })
           
           # Return a summary
           return {
               "status": "success",
               "settlements_processed": len(settlements),
               "critical_settlements": len(critical_settlements),
               "critical_list": critical_settlements
           }
           
       except Exception as e:
           logger.exception(f"Error updating settlement resources: {e}")
           return {"status": "error", "message": str(e)}
       finally:
           db.close()
   ```
   
   **Production Integration**: Add resource production from buildings:
   
   ```python
   # In settlement_service.py
   def _process_building_production(self, settlement_id: str):
       """Process resource production from settlement buildings."""
       try:
           # Get settlement
           settlement = self.db.query(Settlements).filter(
               Settlements.settlement_id == settlement_id
           ).first()
           
           if not settlement:
               return {"status": "error", "message": "Settlement not found"}
           
           # Get buildings
           buildings = self.db.query(Buildings).filter(
               Buildings.settlement_id == settlement_id,
               Buildings.is_completed == True,
               Buildings.is_damaged == False
           ).all()
           
           if not buildings:
               return {"status": "no_buildings", "message": "No productive buildings"}
           
           # Process each building's production
           production_summary = {}
           
           for building in buildings:
               # Skip damaged or incomplete buildings
               building_type = building.building_type
               
               # Get production rates from building type
               production_rates = self._get_building_production_rates(building_type)
               
               if not production_rates:
                   continue
               
               # Calculate time since last production
               from datetime import datetime
               now = datetime.utcnow()
               last_production = building.last_production or building.completed_date or now
               time_diff = now - last_production
               days_passed = time_diff.total_seconds() / 86400  # Convert to days
               
               # Only process if at least 0.1 days have passed
               if days_passed >= 0.1:
                   # Update each resource produced by this building
                   for resource_type, daily_rate in production_rates.items():
                       produced = int(daily_rate * days_passed)
                       if produced > 0:
                           # Add to settlement resources
                           self._add_settlement_resource(settlement_id, resource_type, produced)
                           
                           # Track for summary
                           if resource_type not in production_summary:
                               production_summary[resource_type] = 0
                           production_summary[resource_type] += produced
                   
                   # Update last production time
                   building.last_production = now
           
           # Commit changes
           self.db.commit()
           
           # Log production
           if production_summary:
               logger.info(f"Settlement {settlement.settlement_name} produced: " + 
                          ", ".join([f"{amount} {res}" for res, amount in production_summary.items()]))
           
           return {
               "status": "success",
               "production": production_summary
           }
               
       except Exception as e:
           logger.exception(f"Error processing building production: {e}")
           return {"status": "error", "message": str(e)}
   
   def _add_settlement_resource(self, settlement_id: str, resource_type: str, amount: int):
       """Add resources to a settlement's inventory."""
       from app.models.resource import SettlementResource
       
       # Find the resource record
       resource = self.db.query(SettlementResource).filter(
           SettlementResource.settlement_id == settlement_id,
           SettlementResource.resource_type == resource_type
       ).first()
       
       if resource:
           # Update existing resource
           resource.quantity += amount
       else:
           # Create new resource record
           self.db.add(SettlementResource(
               settlement_id=settlement_id,
               resource_type=resource_type,
               quantity=amount,
               minimum_threshold=10  # Default threshold
           ))
       
       # No need to commit here - calling function will handle commits
   
   def _get_building_production_rates(self, building_type: str) -> Dict[str, float]:
       """Get resource production rates for a building type."""
       # Define production rates for each building type
       production_mapping = {
           "farm": {"food": 10.0},
           "lumbermill": {"wood": 5.0},
           "mine": {"stone": 3.0, "iron": 1.0},
           "hunting_lodge": {"food": 5.0, "leather": 2.0},
           "weaver": {"cloth": 3.0},
           "blacksmith": {"tools": 1.0},
           "bakery": {"bread": 8.0, "food": 5.0},
           "brewery": {"ale": 4.0},
           "fishery": {"food": 7.0}
       }
       
       return production_mapping.get(building_type, {})
   ```

2. **Develop Resource Need Task Generation**
   - Create `create_settlement_resource_task` function
   - Generate tasks when resources fall below thresholds
   - Scale rewards based on urgency and quantity
   
   **Pointer**: Model this after the trader task creation, but focus on resource delivery rather than resolving incidents.
   
   **Integration Point**: Create a dedicated method for task generation in the settlement service:
   
   ```python
   # In settlement_service.py
   async def create_settlement_resource_task(self, settlement_id: str, resource_type: str = None) -> Dict[str, Any]:
       """
       Create a resource gathering task for a settlement.
       If resource_type is provided, creates a task for that specific resource.
       Otherwise, checks for critical resources and creates a task for the most urgent one.
       """
       try:
           # Get the settlement
           settlement = self.db.query(Settlements).filter(
               Settlements.settlement_id == settlement_id
           ).first()
           
           if not settlement:
               logger.error(f"Settlement {settlement_id} not found")
               return {"status": "error", "message": "Settlement not found"}
           
           settlement_name = settlement.settlement_name
           
           # If resource type not specified, check for critical resources
           if not resource_type:
               resource_status = self._update_resource_levels(settlement_id)
               
               if resource_status.get("status") != "critical":
                   logger.info(f"No critical resources found for {settlement_name}")
                   return {"status": "not_needed", "message": "No critical resources found"}
               
               # Get the most urgent resource from the update result
               resource_type = resource_status.get("most_urgent")
               critical_resources = resource_status.get("critical_resources", [])
               critical_resource = next((r for r in critical_resources if r["resource_type"] == resource_type), None)
               
               if not critical_resource:
                   logger.warning(f"Failed to find details for critical resource {resource_type}")
                   return {"status": "error", "message": "Resource details not found"}
               
               # Use details from the critical resource
               amount_needed = critical_resource.get("threshold", 0) - critical_resource.get("quantity", 0)
               urgency = 6 - min(5, int(critical_resource.get("days_remaining", 0)))  # Convert days remaining to urgency
           else:
               # Get the specific resource
               from app.models.resource import SettlementResource
               resource = self.db.query(SettlementResource).filter(
                   SettlementResource.settlement_id == settlement_id,
                   SettlementResource.resource_type == resource_type
               ).first()
               
               if not resource:
                   logger.warning(f"Resource {resource_type} not found for settlement {settlement_name}")
                   return {"status": "error", "message": f"Resource {resource_type} not found"}
               
               # Calculate need
               amount_needed = max(0, resource.minimum_threshold - resource.quantity)
               
               # Determine urgency based on level compared to threshold
               if resource.quantity == 0:
                   urgency = 6  # Critical - completely depleted
               elif resource.quantity < resource.minimum_threshold * 0.25:
                   urgency = 5  # Very urgent - below 25% of threshold
               elif resource.quantity < resource.minimum_threshold * 0.5:
                   urgency = 4  # Urgent - below 50% of threshold
               elif resource.quantity < resource.minimum_threshold * 0.75:
                   urgency = 3  # Moderate - below 75% of threshold
               elif resource.quantity < resource.minimum_threshold:
                   urgency = 2  # Low - below threshold but above 75%
               else:
                   urgency = 1  # Not urgent - at or above threshold
           
           # No need to create a task if no resources needed
           if amount_needed <= 0:
               logger.info(f"No {resource_type} needed for {settlement_name}")
               return {"status": "not_needed", "message": f"No {resource_type} needed"}
           
           # Format task title and description based on urgency
           if urgency >= 5:
               title = f"URGENT: {settlement_name} needs {resource_type}"
               description = f"Critical shortage of {resource_type} in {settlement_name}! The settlement requires {amount_needed} units immediately."
           elif urgency >= 3:
               title = f"{settlement_name} requires {resource_type}"
               description = f"{settlement_name} is running low on {resource_type}. Please deliver {amount_needed} units to avoid shortages."
           else:
               title = f"Gather {resource_type} for {settlement_name}"
               description = f"{settlement_name} could use more {resource_type}. Delivering {amount_needed} units would help the settlement thrive."
           
           # Calculate rewards based on amount and urgency
           # Base values adjusted by urgency
           base_gold_per_unit = 2  # Gold per unit of resource
           base_reputation = urgency  # 1-6 reputation based on urgency
           
           # Scale gold reward by urgency and amount
           gold_reward = int(amount_needed * base_gold_per_unit * (1 + (urgency * 0.2)))
           
           # Cap and floor to reasonable values
           gold_reward = min(1000, max(50, gold_reward))
           
           # Get world ID for task creation
           world_id = settlement.world_id
           
           # Get task service
           from app.game_state.services.task_service import TaskService
           task_service = TaskService(self.db)
           
           # Create the task
           logger.info(f"Creating task for {amount_needed} {resource_type} in {settlement_name} (urgency: {urgency})")
           
           # Special rewards for very urgent tasks
           item_rewards = []
           if urgency >= 5:
               # Add special item rewards for critical tasks
               item_rewards.append({
                   "item_type": "settlement_token",
                   "quantity": 1,
                   "name": f"{settlement_name} Gratitude Token",
                   "description": "A token of appreciation from a settlement you saved from crisis"
               })
           
           # Determine resource requirements for completion
           requirements = {
               "resources": {
                   resource_type: amount_needed
               }
           }
           
           # Create task with TaskService
           result = await task_service.create_task(
               task_type="SETTLEMENT_RESOURCES",
               title=title,
               description=description,
               world_id=str(world_id),
               location_id=settlement_id,
               target_id=settlement_id,
               requirements=requirements,
               rewards={
                   "gold": gold_reward,
                   "reputation": base_reputation,
                   "items": item_rewards
               }
           )
           
           # Log the result
           if result.get("status") == "success":
               logger.info(f"Created resource task {result.get('task_id')} for {settlement_name}")
               
               # Update the database to track the active resource task
               from app.models.resource import SettlementResource
               resource = self.db.query(SettlementResource).filter(
                   SettlementResource.settlement_id == settlement_id,
                   SettlementResource.resource_type == resource_type
               ).first()
               
               if resource:
                   # Track that a task has been created for this resource
                   # This prevents multiple tasks for the same resource type
                   resource.active_task_id = result.get("task_id")
                   self.db.commit()
           else:
               logger.error(f"Failed to create resource task: {result.get('message')}")
           
           return result
       
       except Exception as e:
           logger.exception(f"Error creating settlement resource task: {e}")
           return {"status": "error", "message": str(e)}
   ```
   
   **Implementation Advice**:
   
   1. **Task Requirements Structure**: The task requirements should specify exactly what resources are needed:
   
   ```python
   requirements = {
       "resources": {
           "wood": 100,  # Need 100 wood
           "stone": 50   # and 50 stone
       }
   }
   ```
   
   2. **Tracking Active Tasks**: Add an `active_task_id` field to the `SettlementResource` model to prevent duplicate tasks:
   
   ```python
   # Add to your SettlementResource model class
   active_task_id = Column(UUID, nullable=True)
   ```
   
   3. **Task Completion Handler**: Create a handler for when players complete resource tasks:
   
   ```python
   # In settlement_service.py
   async def complete_resource_task(self, task_id: str, character_id: str) -> Dict[str, Any]:
       """Process resource task completion."""
       try:
           # Get the task
           from app.game_state.services.task_service import TaskService
           task_service = TaskService(self.db)
           task = await task_service.get_task(task_id)
           
           if not task:
               return {"status": "error", "message": "Task not found"}
           
           # Check if task is a resource task
           if task.get("task_type") != "SETTLEMENT_RESOURCES":
               return {"status": "error", "message": "Not a resource task"}
           
           # Get the settlement
           settlement_id = task.get("target_id")
           if not settlement_id:
               return {"status": "error", "message": "No settlement associated with task"}
           
           # Get the resources required
           requirements = task.get("requirements", {})
           resources_required = requirements.get("resources", {})
           
           if not resources_required:
               return {"status": "error", "message": "No resources required for this task"}
           
           # Process each resource
           for resource_type, amount in resources_required.items():
               # Add the resources to the settlement
               self._add_settlement_resource(settlement_id, resource_type, amount)
               
               # Clear the active task ID from the resource record
               from app.models.resource import SettlementResource
               resource = self.db.query(SettlementResource).filter(
                   SettlementResource.settlement_id == settlement_id,
                   SettlementResource.resource_type == resource_type
               ).first()
               
               if resource:
                   resource.active_task_id = None
           
           # Commit changes
           self.db.commit()
           
           # Complete the task
           completion_result = await task_service.complete_task(task_id, character_id)
           
           return completion_result
           
       except Exception as e:
           logger.exception(f"Error completing resource task: {e}")
           return {"status": "error", "message": str(e)}
   ```
   
   **Usage Example**: To generate resource tasks for all settlements in a world:
   
   ```python
   # In settlement_worker.py
   @app.task
   def generate_settlement_resource_tasks(world_id: Optional[str] = None, max_tasks: int = 5):
       """
       Generate resource tasks for settlements that need resources.
       
       Args:
           world_id: Optional world ID to limit scope
           max_tasks: Maximum number of tasks to create
           
       Returns:
           Dict with task generation summary
       """
       logger.info(f"Generating settlement resource tasks" + (f" for world {world_id}" if world_id else ""))
       
       db = SessionLocal()
       try:
           # Get settlement service
           settlement_service = SettlementService(db)
           
           # Find settlements with critical resources
           # First update all resources
           update_result = update_all_settlement_resources(world_id)
           
           if update_result.get("status") != "success":
               logger.error(f"Failed to update resources: {update_result.get('message')}")
               return update_result
           
           # Get settlements with critical resources
           critical_list = update_result.get("critical_list", [])
           logger.info(f"Found {len(critical_list)} settlements with critical resources")
           
           if not critical_list:
               return {
                   "status": "success",
                   "tasks_created": 0,
                   "message": "No settlements have critical resource needs"
               }
           
           # Prioritize settlements (could add more logic here for town importance, etc.)
           import random
           random.shuffle(critical_list)  # Simple randomization for now
           
           # Create tasks up to the maximum
           tasks_created = []
           tasks_count = 0
           
           for settlement in critical_list[:max_tasks]:  # Limit to max_tasks
               settlement_id = settlement["settlement_id"]
               resource_type = settlement["urgent_resource"]
               
               # Check if there's already an active task for this resource
               from app.models.resource import SettlementResource
               resource = db.query(SettlementResource).filter(
                   SettlementResource.settlement_id == settlement_id,
                   SettlementResource.resource_type == resource_type
               ).first()
               
               if resource and resource.active_task_id:
                   logger.info(f"Settlement {settlement['settlement_name']} already has an active task for {resource_type}")
                   continue
               
               # Create a task for this settlement and resource
               result = asyncio.run(settlement_service.create_settlement_resource_task(
                   settlement_id, resource_type
               ))
               
               if result.get("status") == "success":
                   tasks_count += 1
                   tasks_created.append({
                       "settlement_id": settlement_id,
                       "settlement_name": settlement["settlement_name"],
                       "resource_type": resource_type,
                       "task_id": result.get("task_id")
                   })
               else:
                   logger.warning(f"Failed to create task for {settlement['settlement_name']}: {result.get('message')}")
           
           return {
               "status": "success",
               "tasks_created": tasks_count,
               "tasks": tasks_created,
               "message": f"Created {tasks_count} resource tasks out of {len(critical_list)} critical settlements"
           }
           
       except Exception as e:
           logger.exception(f"Error generating settlement resource tasks: {e}")
           return {"status": "error", "message": str(e)}
       finally:
           db.close()
   ```

3. **Link to Settlement Production Systems**
   - Connect to the production lifecycle in settlements
   - Allow buildings to generate specific resource needs
   - Create tasks for upgrading/repairing buildings
   
   **Pointer**: First, check if there's a `_process_buildings` method already in the settlement service. If not, you'll need to create one.
   
   **Integration Point**: Add or extend the building processing method to create repair tasks:
   
   ```python
   # In settlement_service.py
   def _process_buildings(self, settlement_id: str) -> Dict[str, Any]:
       """Process all buildings in a settlement, including production and damage."""
       try:
           # Get settlement data
           settlement = self.db.query(Settlements).filter(
               Settlements.settlement_id == settlement_id
           ).first()
           
           if not settlement:
               return {"status": "error", "message": "Settlement not found"}
           
           settlement_name = settlement.settlement_name
           
           # Get all buildings in the settlement
           buildings = self.db.query(Buildings).filter(
               Buildings.settlement_id == settlement_id
           ).all()
           
           if not buildings:
               return {"status": "success", "message": "No buildings to process"}
           
           # Process production for working buildings
           production_result = self._process_building_production(settlement_id)
           
           # Track damaged buildings that might need repair
           damaged_buildings = []
           
           # Check buildings for damage and deterioration
           for building in buildings:
               # Skip under-construction buildings
               if not building.is_completed:
                   continue
                   
               # Check for random damage chance
               if not building.is_damaged:
                   # Calculate deterioration
                   from datetime import datetime
                   now = datetime.utcnow()
                   age_days = (now - building.completed_date).days if building.completed_date else 0
                   
                   # Older buildings have higher damage chance
                   base_damage_chance = 0.001  # 0.1% daily chance for new buildings
                   age_factor = min(5, age_days / 100)  # Max 5x for very old buildings
                   
                   # Final damage chance per day
                   daily_damage_chance = base_damage_chance * (1 + age_factor)
                   
                   # Roll for damage
                   import random
                   if random.random() < daily_damage_chance:
                       # Building became damaged!
                       building.is_damaged = True
                       building.damage_date = now
                       building.damage_level = random.randint(1, 3)  # 1=minor, 2=moderate, 3=severe
                       
                       logger.warning(f"Building {building.building_id} ({building.building_type}) in {settlement_name} became damaged (level {building.damage_level})")
                       
                       damaged_buildings.append({
                           "building_id": building.building_id,
                           "building_type": building.building_type,
                           "damage_level": building.damage_level,
                           "damage_date": now
                       })
               else:
                   # Already damaged, check if there's an active repair task
                   if not building.repair_task_id:
                       damaged_buildings.append({
                           "building_id": building.building_id,
                           "building_type": building.building_type,
                           "damage_level": building.damage_level,
                           "damage_date": building.damage_date
                       })
           
           # Commit all building changes
           self.db.commit()
           
           # Create repair tasks for damaged buildings that don't have tasks
           repair_tasks_created = 0
           
           for damaged in damaged_buildings:
               # Create a repair task for this building
               repair_result = asyncio.run(self._create_building_repair_task(
                   settlement_id=settlement_id,
                   building_id=damaged["building_id"],
                   building_type=damaged["building_type"],
                   damage_level=damaged["damage_level"]
               ))
               
               if repair_result.get("status") == "success":
                   repair_tasks_created += 1
                   
                   # Update the building to track the repair task
                   building = self.db.query(Buildings).filter(
                       Buildings.building_id == damaged["building_id"]
                   ).first()
                   
                   if building:
                       building.repair_task_id = repair_result.get("task_id")
                       self.db.commit()
           
           return {
               "status": "success",
               "buildings_processed": len(buildings),
               "damaged_buildings": len(damaged_buildings),
               "repair_tasks_created": repair_tasks_created,
               "production": production_result.get("production", {})
           }
           
       except Exception as e:
           logger.exception(f"Error processing buildings for settlement {settlement_id}: {e}")
           return {"status": "error", "message": str(e)}
   ```
   
   **Building Repair Task Creation**: Implement a dedicated method for repair tasks:
   
   ```python
   # In settlement_service.py
   async def _create_building_repair_task(self, settlement_id: str, building_id: str, 
                                         building_type: str, damage_level: int) -> Dict[str, Any]:
       """Create a task for repairing a damaged building."""
       try:
           # Get the settlement for reference
           settlement = self.db.query(Settlements).filter(
               Settlements.settlement_id == settlement_id
           ).first()
           
           if not settlement:
               return {"status": "error", "message": "Settlement not found"}
           
           settlement_name = settlement.settlement_name
           
           # Define resource requirements based on building type and damage level
           # Base requirements for each building type
           base_requirements = {
               "house": {"wood": 10, "stone": 5},
               "farm": {"wood": 15, "stone": 5},
               "mine": {"wood": 20, "stone": 10, "iron": 5},
               "blacksmith": {"wood": 15, "stone": 10, "iron": 10},
               "market": {"wood": 25, "stone": 15},
               "tavern": {"wood": 20, "stone": 10},
               "barracks": {"wood": 30, "stone": 20, "iron": 10},
               "temple": {"wood": 20, "stone": 30, "cloth": 5},
               "townhall": {"wood": 40, "stone": 30, "iron": 10},
               "storehouse": {"wood": 30, "stone": 10},
               "wall": {"stone": 30, "iron": 5}
           }
           
           # Default if building type not recognized
           building_requirements = base_requirements.get(building_type, {"wood": 15, "stone": 10})
           
           # Scale by damage level
           damage_multiplier = {
               1: 0.3,  # Minor damage - 30% of full materials
               2: 0.6,  # Moderate damage - 60% of full materials
               3: 1.0   # Severe damage - 100% of full materials
           }.get(damage_level, 0.5)  # Default to 50% if damage level unknown
           
           # Calculate final requirements
           repair_requirements = {}
           for resource, amount in building_requirements.items():
               repair_requirements[resource] = max(1, int(amount * damage_multiplier))
           
           # Create descriptive text based on damage level
           if damage_level == 1:
               severity = "minor"
               urgency = "needs some attention"
           elif damage_level == 2:
               severity = "significant"
               urgency = "requires repairs soon"
           else:
               severity = "severe"
               urgency = "needs immediate repairs"
           
           # Scale rewards based on damage level and building importance
           # Base reward values
           base_gold = 100
           base_reputation = 2
           
           # Building importance factors - more important buildings give better rewards
           importance_factor = {
               "house": 0.8,
               "farm": 1.0,
               "mine": 1.2,
               "blacksmith": 1.3,
               "market": 1.2,
               "tavern": 1.0,
               "barracks": 1.4,
               "temple": 1.3,
               "townhall": 1.5,
               "storehouse": 1.1,
               "wall": 1.4
           }.get(building_type, 1.0)
           
           # Calculate rewards
           gold_reward = int(base_gold * damage_level * importance_factor)
           reputation_reward = base_reputation + (damage_level - 1)
           
           # Add special rewards for important buildings
           item_rewards = []
           if importance_factor >= 1.3 and damage_level >= 3:
               item_rewards.append({
                   "item_type": "building_blueprint",
                   "quantity": 1,
                   "name": f"{building_type.capitalize()} Blueprint",
                   "description": f"A valuable blueprint for constructing a {building_type}"
               })
           
           # Create the task
           from app.game_state.services.task_service import TaskService
           task_service = TaskService(self.db)
           
           logger.info(f"Creating repair task for {building_type} in {settlement_name} (damage level: {damage_level})")
           
           # Format task information
           title = f"Repair {building_type} in {settlement_name}"
           description = f"The {building_type} in {settlement_name} has suffered {severity} damage and {urgency}. Bring the required materials to restore it to working order."
           
           # Create the task
           result = await task_service.create_task(
               task_type="REPAIR_BUILDING",
               title=title,
               description=description,
               world_id=str(settlement.world_id),
               location_id=settlement_id,
               target_id=building_id,
               requirements={"resources": repair_requirements},
               rewards={
                   "gold": gold_reward,
                   "reputation": reputation_reward,
                   "items": item_rewards if item_rewards else None
               }
           )
           
           # Track and log the result
           if result.get("status") == "success":
               logger.info(f"Created repair task {result.get('task_id')} for {building_type} in {settlement_name}")
           else:
               logger.error(f"Failed to create repair task: {result.get('message')}")
           
           return result
           
       except Exception as e:
           logger.exception(f"Error creating building repair task: {e}")
           return {"status": "error", "message": str(e)}
   ```
   
   **Building Repair Task Completion**: Add a handler for when players complete repair tasks:
   
   ```python
   # In settlement_service.py
   async def complete_building_repair_task(self, task_id: str, character_id: str) -> Dict[str, Any]:
       """Process building repair task completion."""
       try:
           # Get the task
           from app.game_state.services.task_service import TaskService
           task_service = TaskService(self.db)
           task = await task_service.get_task(task_id)
           
           if not task:
               return {"status": "error", "message": "Task not found"}
           
           # Check if it's a repair task
           if task.get("task_type") != "REPAIR_BUILDING":
               return {"status": "error", "message": "Not a repair task"}
           
           # Get the building
           building_id = task.get("target_id")
           if not building_id:
               return {"status": "error", "message": "No building associated with task"}
           
           # Update the building status
           building = self.db.query(Buildings).filter(
               Buildings.building_id == building_id
           ).first()
           
           if not building:
               return {"status": "error", "message": "Building not found"}
           
           # Mark as repaired
           building.is_damaged = False
           building.damage_level = 0
           building.repair_task_id = None
           building.last_repair_date = datetime.utcnow()
           
           # Commit the changes
           self.db.commit()
           
           # Complete the task
           completion_result = await task_service.complete_task(task_id, character_id)
           
           # Log the repair
           logger.info(f"Building {building.building_type} in settlement {building.settlement_id} repaired by {character_id}")
           
           return completion_result
           
       except Exception as e:
           logger.exception(f"Error completing building repair task: {e}")
           return {"status": "error", "message": str(e)}
   ```
   
   **Building Database Schema**: If the Buildings table doesn't exist or doesn't have damage fields, you'll need to create a migration:
   
   ```python
   # Example migration to add damage tracking fields
   """
   from alembic import op
   import sqlalchemy as sa
   from sqlalchemy.dialects.postgresql import UUID
   
   def upgrade():
       # Add damage tracking fields to buildings table
       op.add_column('buildings', sa.Column('is_damaged', sa.Boolean(), nullable=False, server_default='false'))
       op.add_column('buildings', sa.Column('damage_level', sa.Integer(), nullable=False, server_default='0'))
       op.add_column('buildings', sa.Column('damage_date', sa.DateTime(), nullable=True))
       op.add_column('buildings', sa.Column('last_repair_date', sa.DateTime(), nullable=True))
       op.add_column('buildings', sa.Column('repair_task_id', UUID(), nullable=True))
   """
   ```

### Phase 3: Integrated Task Ecosystem

1. **Create Task Relationships**
   - Allow generated tasks to depend on other tasks
   - Implement task chains and sequences
   - Create escalating scenarios based on player actions/inaction
   
   **Pointer**: First, examine the Task model to see if it has a parent_task_id field. If not, you'll need to add it via migration.
   
   **Database Schema Update**:
   ```python
   # Migration to add parent_task_id field
   """
   from alembic import op
   import sqlalchemy as sa
   from sqlalchemy.dialects.postgresql import UUID
   
   def upgrade():
       # Add parent_task_id to tasks table for chaining
       op.add_column('tasks', sa.Column('parent_task_id', UUID(), nullable=True))
       op.add_column('tasks', sa.Column('is_part_of_chain', sa.Boolean(), nullable=False, server_default='false'))
       op.add_column('tasks', sa.Column('chain_position', sa.Integer(), nullable=False, server_default='0'))
       op.add_column('tasks', sa.Column('max_chain_length', sa.Integer(), nullable=False, server_default='1'))
   """
   ```
   
   **Model Update**: Update the Task model to include chain-related fields:
   
   ```python
   # In app/models/tasks.py
   
   # Add to the existing Task model class
   parent_task_id = Column(UUID, nullable=True)
   is_part_of_chain = Column(Boolean, nullable=False, default=False)
   chain_position = Column(Integer, nullable=False, default=0)
   max_chain_length = Column(Integer, nullable=False, default=1)
   ```
   
   **Integration Point**: Enhance the TaskService to support task chains:
   
   ```python
   # In app/game_state/services/task_service.py
   
   async def create_chained_task(self, parent_task_id: str, task_type: str, title: str, 
                                 description: str, world_id: str, location_id: str, 
                                 requirements: Dict[str, Any] = None, 
                                 rewards: Dict[str, Any] = None, 
                                 chain_position: int = 0, max_chain_length: int = 1) -> Dict[str, Any]:
       """
       Create a task that is part of a chain, linked to a parent task.
       The task will only become active when its parent is completed.
       
       Args:
           parent_task_id: The ID of the parent task
           task_type: The type of task
           title: Task title
           description: Task description
           world_id: The world ID
           location_id: The location ID
           requirements: Task completion requirements
           rewards: Task rewards
           chain_position: Position in the chain (0 = first, 1 = second, etc.)
           max_chain_length: Total length of the chain
           
       Returns:
           Dict with task creation result
       """
       try:
           # Verify parent task exists
           parent_task = await self.get_task(parent_task_id)
           if not parent_task:
               logger.error(f"Parent task {parent_task_id} not found")
               return {"status": "error", "message": "Parent task not found"}
           
           # Create the task with chain properties
           task_id = str(uuid.uuid4())
           
           from app.models.tasks import Task
           task = Task(
               task_id=task_id,
               task_type=task_type,
               title=title,
               description=description,
               world_id=world_id,
               location_id=location_id,
               requirements=json.dumps(requirements or {}),
               rewards=json.dumps(rewards or {}),
               status="pending",  # Start as pending, not active
               parent_task_id=parent_task_id,
               is_part_of_chain=True,
               chain_position=chain_position,
               max_chain_length=max_chain_length
           )
           
           self.db.add(task)
           self.db.commit()
           
           logger.info(f"Created chained task {task_id} (chain position {chain_position}/{max_chain_length}), parent: {parent_task_id}")
           
           return {
               "status": "success",
               "task_id": task_id,
               "message": f"Created chained task in position {chain_position} of {max_chain_length}"
           }
           
       except Exception as e:
           logger.exception(f"Error creating chained task: {e}")
           return {"status": "error", "message": str(e)}
   ```
   
   **Task Chain Activation**: Add functionality to activate the next task in a chain:
   
   ```python
   # In app/game_state/services/task_service.py
   
   async def complete_task(self, task_id: str, character_id: str) -> Dict[str, Any]:
       """Complete a task and process rewards."""
       try:
           # Original task completion logic...
           
           # After successfully completing the task, check for child tasks
           task = self.db.query(Task).filter(Task.task_id == task_id).first()
           
           if task.is_part_of_chain:
               # Check if there are any pending tasks in the chain
               next_task = self.db.query(Task).filter(
                   Task.parent_task_id == task_id,
                   Task.status == "pending"
               ).first()
               
               if next_task:
                   # Activate the next task
                   next_task.status = "active"
                   self.db.commit()
                   
                   logger.info(f"Activated next task {next_task.task_id} in chain after completing {task_id}")
           
           # Rest of original task completion logic...
       
       except Exception as e:
           logger.exception(f"Error completing task: {e}")
           return {"status": "error", "message": str(e)}
   ```
   
   **Example Task Chain Creation**: This example creates a multi-step bandit threat storyline:
   
   ```python
   # In settlement_service.py
   async def create_bandit_threat_chain(self, settlement_id: str) -> Dict[str, Any]:
       """Create a chain of tasks to address a growing bandit threat near a settlement."""
       try:
           # Get the settlement
           settlement = self.db.query(Settlements).filter(
               Settlements.settlement_id == settlement_id
           ).first()
           
           if not settlement:
               return {"status": "error", "message": "Settlement not found"}
           
           settlement_name = settlement.settlement_name
           world_id = str(settlement.world_id)
           
           # Task service
           from app.game_state.services.task_service import TaskService
           task_service = TaskService(self.db)
           
           # Get nearby areas for the tasks to take place
           # Ideally, use progressively more distant areas for each step
           from app.models.core import Areas
           nearby_areas = self.db.query(Areas).limit(3).all()  # In a real implementation, get truly nearby areas
           
           if not nearby_areas or len(nearby_areas) < 3:
               return {"status": "error", "message": "Not enough nearby areas for chain"}
           
           # Step 1: Investigation - Active immediately
           scout_area = nearby_areas[0]
           investigation_result = await task_service.create_task(
               task_type="INVESTIGATE_AREA",
               title=f"Investigate disturbances near {settlement_name}",
               description=f"Residents of {settlement_name} have reported strange noises and missing supplies. Scout the nearby {scout_area.area_name} to investigate these reports.",
               world_id=world_id,
               location_id=scout_area.area_id,
               requirements={},  # Simple exploration, no special requirements
               rewards={
                   "gold": 50,
                   "reputation": 1
               }
           )
           
           if investigation_result.get("status") != "success":
               return investigation_result
           
           investigation_task_id = investigation_result.get("task_id")
           
           # Step 2: Smaller Bandit Encounter - Pending until investigation complete
           encounter_area = nearby_areas[1]
           encounter_result = await task_service.create_chained_task(
               parent_task_id=investigation_task_id,
               task_type="COMBAT",
               title=f"Confront bandit scouts near {settlement_name}",
               description=f"Your investigation has revealed a small group of bandit scouts in {encounter_area.area_name}. Defeat them before they can report back to their main group.",
               world_id=world_id,
               location_id=encounter_area.area_id,
               requirements={
                   "combat": {
                       "enemy_type": "bandit_scout",
                       "count": 3
                   }
               },
               rewards={
                   "gold": 120,
                   "reputation": 2,
                   "items": [{
                       "item_type": "weapon",
                       "name": "Bandit's Blade",
                       "quantity": 1
                   }]
               },
               chain_position=1,
               max_chain_length=3
           )
           
           if encounter_result.get("status") != "success":
               return encounter_result
               
           encounter_task_id = encounter_result.get("task_id")
           
           # Step 3: Final Bandit Camp Raid - Pending until previous step complete
           camp_area = nearby_areas[2]
           camp_result = await task_service.create_chained_task(
               parent_task_id=encounter_task_id,
               task_type="RAID",
               title=f"Clear bandit camp threatening {settlement_name}",
               description=f"After defeating the scouts, you've discovered the location of the main bandit camp in {camp_area.area_name}. Eliminate this threat to ensure the safety of {settlement_name}.",
               world_id=world_id,
               location_id=camp_area.area_id,
               requirements={
                   "combat": {
                       "enemy_type": "bandit_leader",
                       "count": 1
                   },
                   "combat_additional": {
                       "enemy_type": "bandit",
                       "count": 5
                   }
               },
               rewards={
                   "gold": 300,
                   "reputation": 5,
                   "items": [{
                       "item_type": "armor",
                       "name": "Bandit Captain's Armor",
                       "quantity": 1
                   },
                   {
                       "item_type": "treasure_map",
                       "name": "Bandit's Treasure Map",
                       "quantity": 1
                   }]
               },
               chain_position=2,
               max_chain_length=3
           )
           
           # Return the created chain details
           return {
               "status": "success",
               "chain_start_task_id": investigation_task_id,
               "task_ids": [
                   investigation_task_id,
                   encounter_result.get("task_id"),
                   camp_result.get("task_id")
               ],
               "message": f"Created 3-step bandit threat chain for {settlement_name}"
           }
           
       except Exception as e:
           logger.exception(f"Error creating bandit threat chain: {e}")
           return {"status": "error", "message": str(e)}
   ```

2. **Add Task Variety Enhancement**
   - Implement rotating task pools
   - Ensure diversity in generated tasks
   - Add rarity tiers and special events
   
   **Pointer**: Add a task generation history system to prevent repetitive tasks in the same areas.
   
   **Integration Point**: Create a TaskGenerationHistory model and table:
   
   ```python
   # In models/tasks.py
   class TaskGenerationHistory(Base):
       """Tracks task types generated in specific locations to maintain variety."""
       __tablename__ = "task_generation_history"
       
       id = Column(UUID, primary_key=True, default=uuid.uuid4)
       location_id = Column(UUID, ForeignKey("areas.area_id"), nullable=False)
       task_type = Column(String(50), nullable=False)
       generated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
       rarity_tier = Column(Integer, nullable=False, default=1)  # 1=common, 2=uncommon, 3=rare, 4=legendary
       
       def __repr__(self):
           return f"<TaskGenerationHistory location_id={self.location_id} task_type={self.task_type}>"
   ```
   
   **Task Selection Helper**: Add a method to select varied tasks:
   
   ```python
   # In area_service.py or task_service.py
   def _select_varied_task_type(self, area_id: str, available_tasks: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
       """
       Select a task type that hasn't been used recently in this area.
       Considers task rarity for selection.
       
       Args:
           area_id: Area ID to check history for
           available_tasks: Dictionary of {task_type: task_config} with available task types
           
       Returns:
           Tuple of (selected_task_type, task_config)
       """
       try:
           from app.models.tasks import TaskGenerationHistory
           from datetime import datetime, timedelta
           from collections import Counter
           import random
           
           # Get tasks generated in this area in the last 7 days
           recent_tasks = self.db.query(TaskGenerationHistory).filter(
               TaskGenerationHistory.location_id == area_id,
               TaskGenerationHistory.generated_at > (datetime.utcnow() - timedelta(days=7))
           ).all()
           
           # Count task types used recently
           recent_task_types = [task.task_type for task in recent_tasks]
           task_type_counts = Counter(recent_task_types)
           
           # Get all task types and their configurations
           task_types = list(available_tasks.keys())
           
           # If we have no available tasks, return None
           if not task_types:
               logger.warning(f"No available task types for area {area_id}")
               return None, None
           
           # Group tasks by rarity
           common_tasks = []
           uncommon_tasks = []
           rare_tasks = []
           legendary_tasks = []
           
           for task_type, config in available_tasks.items():
               rarity = config.get("rarity", 1)
               
               if rarity == 1:
                   common_tasks.append(task_type)
               elif rarity == 2:
                   uncommon_tasks.append(task_type)
               elif rarity == 3:
                   rare_tasks.append(task_type)
               elif rarity == 4:
                   legendary_tasks.append(task_type)
           
           # Determine if we can give a legendary task (very rare)
           # Only 1% chance and if no legendary task in the last 30 days
           legendary_in_month = self.db.query(TaskGenerationHistory).filter(
               TaskGenerationHistory.location_id == area_id,
               TaskGenerationHistory.rarity_tier == 4,
               TaskGenerationHistory.generated_at > (datetime.utcnow() - timedelta(days=30))
           ).count() > 0
           
           can_give_legendary = random.random() < 0.01 and not legendary_in_month and legendary_tasks
           
           # Determine if we can give a rare task
           # 10% chance and if no rare task in the last 14 days
           rare_in_two_weeks = self.db.query(TaskGenerationHistory).filter(
               TaskGenerationHistory.location_id == area_id,
               TaskGenerationHistory.rarity_tier == 3,
               TaskGenerationHistory.generated_at > (datetime.utcnow() - timedelta(days=14))
           ).count() > 0
           
           can_give_rare = random.random() < 0.1 and not rare_in_two_weeks and rare_tasks
           
           # Determine if we can give an uncommon task
           # 30% chance and if no uncommon task in the last 3 days
           uncommon_in_three_days = self.db.query(TaskGenerationHistory).filter(
               TaskGenerationHistory.location_id == area_id,
               TaskGenerationHistory.rarity_tier == 2,
               TaskGenerationHistory.generated_at > (datetime.utcnow() - timedelta(days=3))
           ).count() > 0
           
           can_give_uncommon = random.random() < 0.3 and not uncommon_in_three_days and uncommon_tasks
           
           # Select task type based on rarity and availability
           if can_give_legendary:
               # Select a legendary task
               selected_task_type = random.choice(legendary_tasks)
               logger.info(f"Selected LEGENDARY task {selected_task_type} for area {area_id}")
           elif can_give_rare:
               # Select a rare task
               selected_task_type = random.choice(rare_tasks)
               logger.info(f"Selected RARE task {selected_task_type} for area {area_id}")
           elif can_give_uncommon:
               # Select an uncommon task
               selected_task_type = random.choice(uncommon_tasks)
               logger.info(f"Selected UNCOMMON task {selected_task_type} for area {area_id}")
           else:
               # Select a common task - but avoid recently used ones
               unused_common_tasks = [t for t in common_tasks if t not in recent_task_types]
               
               if unused_common_tasks:
                   # Choose a type we haven't used recently
                   selected_task_type = random.choice(unused_common_tasks)
               else:
                   # If all types have been used, use the least common
                   common_task_counts = {t: task_type_counts.get(t, 0) for t in common_tasks}
                   selected_task_type = min(common_task_counts.items(), key=lambda x: x[1])[0]
               
               logger.info(f"Selected COMMON task {selected_task_type} for area {area_id}")
           
           # Record the task generation
           task_config = available_tasks[selected_task_type]
           rarity = task_config.get("rarity", 1)
           
           self.db.add(TaskGenerationHistory(
               location_id=area_id,
               task_type=selected_task_type,
               rarity_tier=rarity
           ))
           self.db.commit()
           
           return selected_task_type, task_config
           
       except Exception as e:
           logger.exception(f"Error selecting varied task type: {e}")
           # Fallback to simple random selection
           if available_tasks:
               selected_task_type = random.choice(list(available_tasks.keys()))
               return selected_task_type, available_tasks[selected_task_type]
           return None, None
   ```
   
   **Task Pool Configuration**: Define task pools with rarity tiers:
   
   ```python
   # Define a pool of task templates that can be used in different areas
   AREA_TASK_POOL = {
       "bandit_attack": {
           "title": "Clear Bandit Camp near {area_name}",
           "description": "A group of bandits has established a camp in {area_name} and is terrorizing travelers. Eliminate the threat.",
           "requirements": {
               "combat": {
                   "enemy_type": "bandit",
                   "count": 5
               }
           },
           "rewards": {
               "gold": 100,
               "reputation": 2
           },
           "rarity": 1  # Common
       },
       "lost_artifact": {
           "title": "Recover Lost Artifact from {area_name}",
           "description": "A valuable artifact was lost in {area_name}. Find and return it to earn a reward.",
           "requirements": {
               "find_item": {
                   "item_type": "artifact"
               }
           },
           "rewards": {
               "gold": 200,
               "reputation": 3
           },
           "rarity": 2  # Uncommon
       },
       "legendary_beast": {
           "title": "Hunt the Legendary Beast of {area_name}",
           "description": "A legendary beast has been spotted in {area_name}. Hunt it down for fame and fortune.",
           "requirements": {
               "combat": {
                   "enemy_type": "legendary_beast",
                   "count": 1
               }
           },
           "rewards": {
               "gold": 500,
               "reputation": 8,
               "items": [
                   {
                       "item_type": "trophy",
                       "name": "Legendary Beast Trophy",
                       "quantity": 1
                   }
               ]
           },
           "rarity": 4  # Legendary
       }
   }
   ```
   
   **Usage Example**: Generate a varied task for an area:
   
   ```python
   # In area_service.py or a specific task generator
   async def generate_area_task(self, area_id: str) -> Dict[str, Any]:
       """Generate a varied task for an area based on rarity tiers."""
       try:
           # Get the area
           area = self.db.query(Areas).filter(Areas.area_id == area_id).first()
           if not area:
               return {"status": "error", "message": "Area not found"}
           
           area_name = area.area_name
           
           # Select a varied task type
           task_type, task_config = self._select_varied_task_type(area_id, AREA_TASK_POOL)
           
           if not task_type or not task_config:
               return {"status": "error", "message": "No suitable task type found"}
           
           # Format task details
           title = task_config["title"].format(area_name=area_name)
           description = task_config["description"].format(area_name=area_name)
           
           # Customize requirements based on area type
           requirements = task_config["requirements"].copy()
           
           # Customize rewards
           rewards = task_config["rewards"].copy()
           
           # Apply rarity bonuses
           rarity = task_config.get("rarity", 1)
           if rarity >= 2:
               rewards["gold"] = int(rewards["gold"] * 1.2)  # 20% bonus for uncommon+
           if rarity >= 3:
               rewards["reputation"] += 2  # +2 rep for rare+
           
           # Create the task
           from app.game_state.services.task_service import TaskService
           task_service = TaskService(self.db)
           
           world_id = area.world_id
           
           result = await task_service.create_task(
               task_type=task_type,
               title=title,
               description=description,
               world_id=world_id,
               location_id=area_id,
               requirements=requirements,
               rewards=rewards
           )
           
           return result
           
       except Exception as e:
           logger.exception(f"Error generating area task: {e}")
           return {"status": "error", "message": str(e)}
   ```

3. **Balance Task Economy**
   - Create algorithms to balance task generation rate
   - Adjust rewards dynamically based on player economy
   - Implement difficulty scaling based on player progression
   
   **Pointer**: Add a WorldEconomy model to track economic indicators for balancing.
   
   **Database Integration**:
   
   ```python
   # In models/world.py
   class WorldEconomy(Base):
       """Tracks economic metrics for a world to balance task rewards."""
       __tablename__ = "world_economy"
       
       id = Column(UUID, primary_key=True, default=uuid.uuid4)
       world_id = Column(UUID, ForeignKey("worlds.world_id"), nullable=False)
       gold_rewarded_24h = Column(Integer, nullable=False, default=0)
       gold_rewarded_7d = Column(Integer, nullable=False, default=0)
       task_completion_rate_24h = Column(Float, nullable=False, default=0.0)  # Tasks completed / tasks generated
       avg_player_gold = Column(Integer, nullable=False, default=0)
       last_updated = Column(DateTime, nullable=False, default=datetime.utcnow)
       inflation_multiplier = Column(Float, nullable=False, default=1.0)  # For dynamic price/reward adjustment
       
       def __repr__(self):
           return f"<WorldEconomy world_id={self.world_id} inflation={self.inflation_multiplier}>"
   ```
   
   **Economy Update Scheduler**:
   
   ```python
   # In world_worker.py
   @app.task
   def update_world_economy(world_id: str):
       """Update economic indicators for a world to guide task balancing."""
       logger.info(f"Updating economy metrics for world {world_id}")
       
       db = SessionLocal()
       try:
           from app.models.world import WorldEconomy
           from app.models.tasks import Task
           from app.models.core import Players
           from datetime import datetime, timedelta
           from sqlalchemy import func
           
           # Get or create economy record
           economy = db.query(WorldEconomy).filter(WorldEconomy.world_id == world_id).first()
           if not economy:
               economy = WorldEconomy(world_id=world_id)
               db.add(economy)
               db.commit()
           
           # Update gold rewarded in last 24 hours
           day_ago = datetime.utcnow() - timedelta(days=1)
           gold_24h = db.query(func.sum(Task.gold_reward)).filter(
               Task.world_id == world_id,
               Task.status == "completed",
               Task.completed_at > day_ago
           ).scalar() or 0
           
           # Update gold rewarded in last 7 days
           week_ago = datetime.utcnow() - timedelta(days=7)
           gold_7d = db.query(func.sum(Task.gold_reward)).filter(
               Task.world_id == world_id,
               Task.status == "completed",
               Task.completed_at > week_ago
           ).scalar() or 0
           
           # Calculate task completion rate
           tasks_created = db.query(func.count(Task.task_id)).filter(
               Task.world_id == world_id,
               Task.created_at > day_ago
           ).scalar() or 0
           
           tasks_completed = db.query(func.count(Task.task_id)).filter(
               Task.world_id == world_id,
               Task.status == "completed",
               Task.completed_at > day_ago
           ).scalar() or 0
           
           completion_rate = tasks_completed / max(1, tasks_created)
           
           # Get average player gold
           avg_gold = db.query(func.avg(Players.gold)).filter(
               Players.world_id == world_id
           ).scalar() or 0
           
           # Update economy record
           economy.gold_rewarded_24h = gold_24h
           economy.gold_rewarded_7d = gold_7d
           economy.task_completion_rate_24h = completion_rate
           economy.avg_player_gold = int(avg_gold)
           economy.last_updated = datetime.utcnow()
           
           # Calculate inflation multiplier
           # Targets: 1000 gold per day per active player, 50% completion rate
           # Higher completion rates with high rewards = lower multiplier (deflation)
           # Lower completion rates with low rewards = higher multiplier (inflation)
           active_players = db.query(func.count(Players.player_id)).filter(
               Players.world_id == world_id,
               Players.last_activity > day_ago
           ).scalar() or 1
           
           target_gold = 1000 * active_players
           target_completion = 0.5
           
           # If we're giving too much gold and tasks are being completed too frequently,
           # decrease the multiplier to reduce rewards
           if gold_24h > target_gold * 1.2 and completion_rate > target_completion:
               economy.inflation_multiplier = max(0.5, economy.inflation_multiplier * 0.95)  # 5% reduction
           
           # If we're giving too little gold and tasks aren't being completed,
           # increase the multiplier to boost rewards
           elif gold_24h < target_gold * 0.8 and completion_rate < target_completion:
               economy.inflation_multiplier = min(2.0, economy.inflation_multiplier * 1.05)  # 5% increase
           
           # Commit the changes
           db.commit()
           
           logger.info(f"Updated economy for world {world_id}: " +
                      f"gold_24h={gold_24h}, completion_rate={completion_rate:.2f}, " +
                      f"inflation={economy.inflation_multiplier:.2f}")
           
           return {
               "status": "success",
               "world_id": world_id,
               "gold_24h": gold_24h,
               "completion_rate": completion_rate,
               "inflation_multiplier": economy.inflation_multiplier
           }
           
       except Exception as e:
           logger.exception(f"Error updating world economy: {e}")
           return {"status": "error", "message": str(e)}
       finally:
           db.close()
   ```
   
   **Dynamic Reward Calculation**:
   
   ```python
   # Add to task_service.py
   def _calculate_balanced_rewards(self, base_rewards: Dict[str, Any], world_id: str, 
                                  task_type: str, requirements: Dict[str, Any]) -> Dict[str, Any]:
       """
       Calculate balanced rewards for a task, adjusting based on world economy.
       
       Args:
           base_rewards: Dictionary of base rewards (gold, reputation, items)
           world_id: World ID for economic context
           task_type: Type of task for difficulty adjustment
           requirements: Task requirements for complexity calculation
           
       Returns:
           Dict with adjusted rewards
       """
       try:
           from app.models.world import WorldEconomy
           
           # Copy the base rewards
           rewards = base_rewards.copy()
           
           # Get economy data for this world
           economy = self.db.query(WorldEconomy).filter(WorldEconomy.world_id == world_id).first()
           
           if not economy:
               # No economy data yet, use base rewards
               return rewards
           
           # Get base gold reward
           gold_reward = rewards.get("gold", 0)
           
           # Apply inflation multiplier
           gold_reward = int(gold_reward * economy.inflation_multiplier)
           
           # Apply task type adjustments
           task_difficulty_multipliers = {
               "BANDIT_ATTACK": 1.0,
               "COLLECT_RESOURCES": 0.8,
               "LEGENDARY_HUNT": 1.5,
               "ESCORT": 1.2,
               "SETTLEMENT_RESOURCES": 0.9,
               "REPAIR_BUILDING": 1.1
           }
           
           difficulty_multiplier = task_difficulty_multipliers.get(task_type, 1.0)
           gold_reward = int(gold_reward * difficulty_multiplier)
           
           # Apply complexity adjustment based on requirements
           complexity = 1.0
           
           # Combat requirements increase complexity
           if "combat" in requirements:
               enemy_count = requirements["combat"].get("count", 1)
               enemy_type = requirements["combat"].get("enemy_type", "generic")
               
               # More enemies = more complex
               complexity += 0.1 * min(enemy_count, 10)
               
               # Tougher enemies = more complex
               enemy_difficulty = {
                   "bandit": 1.0,
                   "bandit_leader": 1.5,
                   "wolf": 0.8,
                   "bear": 1.2,
                   "legendary_beast": 2.0
               }.get(enemy_type, 1.0)
               
               complexity *= enemy_difficulty
           
           # Delivery distance affects complexity
           if "delivery" in requirements:
               distance = requirements["delivery"].get("distance", 0)
               complexity += distance * 0.01
           
           # Apply complexity multiplier
           gold_reward = int(gold_reward * complexity)
           
           # Apply completion rate adjustments
           # If tasks are being ignored, make them more lucrative
           if economy.task_completion_rate_24h < 0.3:
               gold_reward = int(gold_reward * 1.3)
           
           # Player progression adjustment - if players have lots of gold, 
           # rewards should scale to remain meaningful
           avg_gold = economy.avg_player_gold
           if avg_gold > 10000:
               # Ensure rewards stay relevant for rich players
               gold_reward = max(gold_reward, int(avg_gold * 0.05))
           
           # Apply the calculated gold reward
           rewards["gold"] = gold_reward
           
           # Adjust reputation rewards slightly based on task difficulty
           if "reputation" in rewards:
               rep_reward = rewards["reputation"]
               rewards["reputation"] = max(1, int(rep_reward * difficulty_multiplier))
           
           return rewards
           
       except Exception as e:
           logger.exception(f"Error calculating balanced rewards: {e}")
           # Fallback to base rewards
           return base_rewards
   ```
   
   **Integration Example**: Use the balanced rewards function when creating tasks:
   
   ```python
   # In task_service.py, modify create_task method
   async def create_task(self, task_type: str, title: str, description: str, world_id: str, 
                        location_id: str, target_id: str = None, 
                        requirements: Dict[str, Any] = None, 
                        rewards: Dict[str, Any] = None) -> Dict[str, Any]:
       """Create a new task with economically balanced rewards."""
       try:
           # Create task ID
           task_id = str(uuid.uuid4())
           
           # Balance the rewards
           balanced_rewards = self._calculate_balanced_rewards(
               rewards or {},
               world_id,
               task_type,
               requirements or {}
           )
           
           # Continue with original task creation logic
           # But use balanced_rewards instead of the original rewards
           # ...
       
       except Exception as e:
           logger.exception(f"Error creating task: {e}")
           return {"status": "error", "message": str(e)}
   ```

## Implementation Schedule and Integration Guide

To successfully implement the automatic task generation system, follow this phased approach:

### Phase 1: Infrastructure and Foundation (Weeks 1-2)
1. **Database Schema Updates**
   - Add required fields to Task model (parent_task_id, chain fields)
   - Create TaskGenerationHistory table
   - Create WorldEconomy table

2. **Core Service Updates**
   - Enhance TaskService with chained task support
   - Add economy tracking to WorldService
   - Update task creation methods for reward balancing
   
### Phase 2: Trader Event System (Weeks 2-3) 
1. **Journey Event System**
   - Update trader_service.py to include event detection
   - Implement _check_for_travel_events method
   - Ensure these events are properly saved in the database

2. **Event to Task Conversion**
   - Add _create_event_based_task method
   - Connect to existing task handling

### Phase 3: Settlement Resource Systems (Weeks 3-4)
1. **Resource Tracking**
   - Add settlement resource models
   - Implement resource consumption and production
   
2. **Resource Task Generation**
   - Create task templates for resources
   - Implement urgency-based reward scaling

### Phase 4: Integration and Tuning (Weeks 4-5)
1. **Scheduling Setup**
   - Add Celery beat tasks for resource checks
   - Configure regular economic updates
   
2. **Performance Testing**
   - Test with multiple simultaneous traders
   - Verify database query optimization
   
3. **Tuning Parameters**
   - Adjust probabilities for ideal task generation rate
   - Fine-tune reward calculations based on player feedback

## Conclusion

The automatic task generation system provides a solid foundation for emergent gameplay in Sworn. By implementing this system, you'll create:

1. **Dynamic Gameplay**: Players will encounter tasks that emerge organically from the game world's state
2. **Economic Balance**: Rewards will scale intelligently with player progression
3. **Content Variety**: Rarity tiers and task chains will keep the experience fresh
4. **Realistic Simulation**: Tasks will be tied to actual in-game needs and events

Most importantly, this system provides a framework that can be extended with:
- Seasonal events
- Faction-based tasks
- Location-specific special encounters 
- Player history customization

By starting with the "low-hanging fruit" - trader journey events - and gradually expanding to resource tasks and chained events, you'll build a robust, flexible system that will continue to drive engaging player experiences for years to come.

## Immediate Next Steps (Low-Hanging Fruit)

### 1. Enhance Trader Journey Events

```python
# In trader_service.py - continue_area_travel method
async def continue_area_travel(self, trader_id: str) -> Dict[str, Any]:
    """Continue a trader's journey through areas."""
    logger.info(f"Continuing area travel for trader {trader_id}")
    
    try:
        # Get the trader's database record
        trader_db = self.db.query(Traders).filter(Traders.trader_id == trader_id).first()
        if not trader_db:
            return {"status": "error", "message": "Trader not found"}
        
        # ... existing journey logic ...
        
        # Add enhanced event handling right before trader moves to next area
        # This is a good place because the trader is in transit
        if current_area_id:
            event_result = await self._check_for_travel_events(trader_id, current_area_id)
            if event_result["event_triggered"]:
                logger.info(f"Trader {trader_id} encountered an event: {event_result['event_type']}")
                
                # Handle the event - potentially creating a task
                if event_result["severity"] >= 3:  # Only create tasks for significant events
                    task_result = await self._create_event_based_task(trader_id, current_area_id, event_result)
                    if task_result.get("status") == "success":
                        # Halt journey if a task was created
                        return {
                            "status": "success", 
                            "action": "event_halted",
                            "event_type": event_result["event_type"],
                            "task_id": task_result.get("task_id")
                        }
        
        # Continue with normal journey if no event or low severity event
        # ... rest of the existing method ...
    
    except Exception as e:
        logger.exception(f"Error continuing area travel: {e}")
        return {"status": "error", "message": str(e)}
```

**Key Features**: 
- Integrates cleanly into the existing travel function
- Only creates tasks for significant events (severity ≥ 3)
- Returns information about the event that caused the halt
- Doesn't disrupt the existing journey logic for non-event cases

### 2. Implement Travel Event Generator

```python
# New method in trader_service.py
async def _check_for_travel_events(self, trader_id: str, area_id: str) -> Dict[str, Any]:
    """Check if any travel events occur for a trader in an area."""
    try:
        trader_db = self.db.query(Traders).filter(Traders.trader_id == trader_id).first()
        area = self.db.query(Areas).filter(Areas.area_id == area_id).first()
        
        if not trader_db or not area:
            return {"event_triggered": False}
        
        # Get trader name for logging
        trader_name = trader_db.npc_name or f"Trader {trader_id[:8]}"
        
        # Base event chance affected by area danger
        danger_level = getattr(area, 'danger_level', 1) or 1
        base_event_chance = 0.05 + (danger_level * 0.03)  # 5% base + 3% per danger level
        
        # Get trader details that affect event chances
        cart_health = getattr(trader_db, 'cart_health', 100) or 100
        hired_guards = getattr(trader_db, 'hired_guards', 0) or 0
        
        # Lower cart health increases breakdown chance
        if cart_health < 50:
            # Significantly higher chance when cart is already damaged
            cart_factor = (50 - cart_health) * 0.01  # Up to +50% chance for 0 health
            base_event_chance += cart_factor
            logger.info(f"Trader {trader_name}'s low cart health ({cart_health}%) increases event chance by {cart_factor*100:.1f}%")
        
        # Guards reduce bandit attack chance
        guard_protection = min(hired_guards * 0.1, 0.5)  # Max 50% reduction from guards
        if hired_guards > 0:
            logger.info(f"Trader {trader_name}'s {hired_guards} guards provide {guard_protection*100:.1f}% protection")
        
        # Weather and season can affect event chances (implement based on your world model)
        # Example: Winter doubles event chance
        world = self.db.query(Worlds).filter(Worlds.world_id == trader_db.world_id).first()
        season_multiplier = 1.0
        if world and hasattr(world, 'current_season') and world.current_season == "winter":
            season_multiplier = 2.0
            logger.info(f"Winter season doubles event chance for trader {trader_name}")
        
        # Apply season multiplier
        final_event_chance = base_event_chance * season_multiplier
        
        # Log the calculated chance for debugging
        logger.info(f"Trader {trader_name} has {final_event_chance*100:.1f}% chance of event in area {area.area_name}")
        
        # Roll for event
        if random.random() < final_event_chance:
            # Determine event type - build a pool of possible events with weights (severity)
            event_pool = []
            
            # Add possible events based on context
            if cart_health < 70:
                # Cart breakdown more likely with lower health
                severity = 2 + int((70 - cart_health) / 10)  # 2-9 severity scale
                event_pool.append(("broken_cart", severity))
                logger.info(f"Added possible broken_cart event with severity {severity}")
            
            # Bandit attack chance reduced by guards but affected by danger level
            bandit_chance = danger_level / 5  # 20% chance at danger level 1
            bandit_chance = max(0.05, bandit_chance - guard_protection)
            if random.random() < bandit_chance:
                severity = 3 + danger_level  # 4-8 severity scale
                event_pool.append(("bandit_attack", severity))
                logger.info(f"Added possible bandit_attack event with severity {severity}")
            
            # Always possible events with lower severity
            event_pool.append(("lost_cargo", 2))
            event_pool.append(("food_shortage", 1))
            
            # Season-specific events
            if world and hasattr(world, 'current_season'):
                current_season = world.current_season
                if current_season == "winter":
                    event_pool.append(("sick_animals", 3))  # Animals more likely to get sick in winter
                elif current_season == "spring":
                    event_pool.append(("flooded_road", 2))  # Spring floods
                elif current_season == "summer":
                    event_pool.append(("heat_exhaustion", 2))  # Summer heat
            
            # Select a random event if any are available, weighted by severity
            if event_pool:
                # Sort the event pool by severity (highest to lowest)
                event_pool.sort(key=lambda x: x[1], reverse=True)
                
                # Select an event - higher chance for higher severity events
                # This makes dangerous events more likely
                weights = [event[1] for event in event_pool]
                total_weight = sum(weights)
                normalized_weights = [w/total_weight for w in weights]
                
                # Use weighted choice
                choice_index = random.choices(
                    range(len(event_pool)), 
                    weights=normalized_weights,
                    k=1
                )[0]
                
                event_type, severity = event_pool[choice_index]
                
                logger.info(f"Trader {trader_name} encountered {event_type} (severity {severity}) in {area.area_name}")
                
                return {
                    "event_triggered": True,
                    "event_type": event_type,
                    "severity": severity,
                    "area_name": area.area_name,
                    "trader_name": trader_name
                }
        
        return {"event_triggered": False}
        
    except Exception as e:
        logger.exception(f"Error checking for travel events: {e}")
        return {"event_triggered": False}
```

**Key Features**:
- Detailed logging to help debug the probability system
- Multiple contextual factors affecting event chance:
  - Area danger level (existing factor in your system)
  - Cart health (promotes equipment maintenance gameplay)
  - Hired guards (makes hiring guards valuable)
  - Season (makes world feel more dynamic)
- Flexible event pool with severity-based weighting
- Proper exception handling to prevent crashes

### 3. Create Task From Event

```python
# New method in trader_service.py
async def _create_event_based_task(self, trader_id: str, area_id: str, event_result: Dict[str, Any]) -> Dict[str, Any]:
    """Create a player task based on a trader travel event."""
    try:
        from app.workers.task_worker import create_trader_assistance_task
        
        # Get necessary info
        trader_db = self.db.query(Traders).filter(Traders.trader_id == trader_id).first()
        if not trader_db or not trader_db.world_id:
            return {"status": "error", "message": "Trader or world not found"}
        
        world_id = trader_db.world_id
        event_type = event_result["event_type"]
        severity = event_result["severity"]
        trader_name = event_result.get("trader_name", trader_db.npc_name or f"Trader {trader_id[:8]}")
        area_name = event_result.get("area_name", "unknown area")
        
        # Log task creation attempt
        logger.info(f"Creating {event_type} task for {trader_name} in {area_name} (severity: {severity})")
        
        # Create task with custom details based on severity
        # Adjust rewards and add special rewards for higher severity events
        additional_rewards = {}
        if severity >= 5:
            # High severity events give better rewards
            additional_rewards = {
                "items": [
                    {"item_type": "rare_trade_good", "quantity": 1},
                    {"item_type": "trader_map", "quantity": 1}
                ]
            }
        
        # Create the task using the existing function
        result = create_trader_assistance_task(
            trader_id=trader_id,
            area_id=area_id,
            world_id=world_id,
            issue_type=event_type,
            additional_rewards=additional_rewards  # You'd need to modify create_trader_assistance_task to accept this
        )
        
        # Log the result
        if result.get("status") == "success":
            logger.info(f"Successfully created {event_type} task {result.get('task_id')} for {trader_name}")
        else:
            logger.error(f"Failed to create task: {result.get('message')}")
        
        # Mark the trader as waiting for assistance if task was created
        if result.get("status") == "success" and result.get("task_id"):
            # Update database record
            trader_db.can_move = False
            trader_db.active_task_id = result.get("task_id")
            self.db.commit()
            
            # Also update entity model for consistency
            trader_entity = await self.trader_manager.load_trader(trader_id)
            if trader_entity:
                trader_entity.set_property("can_move", False)
                trader_entity.set_property("active_task_id", result.get("task_id"))
                # Add event details to entity for storytelling
                trader_entity.set_property("last_event_type", event_type)
                trader_entity.set_property("last_event_area", area_id)
                trader_entity.set_property("last_event_time", datetime.utcnow().isoformat())
                await self.trader_manager.save_trader(trader_entity)
                
            logger.info(f"Trader {trader_name} is now waiting for assistance with task {result.get('task_id')}")
        
        return result
        
    except Exception as e:
        logger.exception(f"Error creating event-based task: {e}")
        return {"status": "error", "message": str(e)}
```

**Key Features**:
- Detailed logging for debugging
- Severity-based rewards (better rewards for more challenging events)
- Trader state management to prevent movement while awaiting help
- Event history tracking in the trader entity
- Proper exception handling

### 4. Settlement Resource Monitoring Function

```python
# Add to settlement_service.py
def _check_resource_needs(self, settlement_id: str) -> Dict[str, Any]:
    """Check if a settlement needs resources urgently."""
    try:
        # Get settlement data
        settlement_db = self.db.query(Settlements).filter(
            Settlements.settlement_id == settlement_id
        ).first()
        
        if not settlement_db:
            logger.warning(f"Settlement {settlement_id} not found")
            return {"needs_resources": False}
        
        settlement_name = settlement_db.settlement_name
        
        # Get settlement population for calculations
        population = getattr(settlement_db, 'population', 100) or 100
        
        # Define required resources and their thresholds based on settlement size
        # More people need more resources
        population_factor = max(1, population / 100)  # 1.0 for 100 people, 2.0 for 200, etc.
        
        resource_thresholds = {
            "food": int(100 * population_factor),  # Need task if below this amount
            "wood": int(50 * population_factor),
            "stone": int(30 * population_factor),
            "iron": int(20 * population_factor),
            "cloth": int(15 * population_factor)
        }
        
        # Get current resource levels from settlement storage
        # This would need to be implemented based on your storage model
        # For now, we'll use a placeholder implementation
        resource_levels = self._get_settlement_resources(settlement_id)
        
        logger.info(f"Checking resource needs for {settlement_name} (pop: {population})")
        for resource, amount in resource_levels.items():
            threshold = resource_thresholds.get(resource, 0)
            logger.info(f"  {resource}: {amount}/{threshold} ({(amount/threshold*100 if threshold else 0):.1f}%)")
        
        # Check for resources below threshold
        needed_resources = {}
        for resource, threshold in resource_thresholds.items():
            current_level = resource_levels.get(resource, 0)
            if current_level < threshold:
                # Calculate how much is needed to reach comfortable level
                shortfall = threshold - current_level
                needed_resources[resource] = shortfall
                logger.info(f"  {settlement_name} needs {shortfall} more {resource}")
        
        if needed_resources:
            # Determine the most critical resource need (largest percentage shortfall)
            most_needed = max(
                needed_resources.keys(), 
                key=lambda r: needed_resources[r]/resource_thresholds[r]
            )
            shortfall = needed_resources[most_needed]
            
            # Calculate urgency (1-6 scale) - higher when resource is critically low
            current_level = resource_levels.get(most_needed, 0)
            threshold = resource_thresholds[most_needed]
            percentage = current_level / threshold if threshold > 0 else 0
            urgency = 1 + int(5 * (1 - percentage))  # 6 when empty, 1 when nearly full
            
            logger.info(f"{settlement_name} most urgently needs {shortfall} {most_needed} (urgency: {urgency}/6)")
            
            return {
                "needs_resources": True,
                "settlement_name": settlement_name,
                "resource_type": most_needed,
                "amount_needed": shortfall,
                "urgency": urgency,
                "population": population
            }
        
        logger.info(f"{settlement_name} has adequate resources")
        return {"needs_resources": False}
        
    except Exception as e:
        logger.exception(f"Error checking resource needs: {e}")
        return {"needs_resources": False}

# Placeholder method - implement based on your storage model
def _get_settlement_resources(self, settlement_id: str) -> Dict[str, int]:
    """Get current resource levels for a settlement."""
    # In a real implementation, this would query your resource storage system
    # For now, we'll return random values for testing
    
    # Try to get from database if you have a resource table
    try:
        # This is just an example - implement based on your actual schema
        resources = {}
        resource_records = self.db.query(SettlementResources).filter(
            SettlementResources.settlement_id == settlement_id
        ).all()
        
        for record in resource_records:
            resources[record.resource_type] = record.quantity
            
        # If found resources, return them
        if resources:
            return resources
    except Exception as e:
        logger.warning(f"Couldn't query settlement resources: {e}")
    
    # Fallback to random values for testing
    import random
    return {
        "food": random.randint(20, 150),
        "wood": random.randint(10, 100),
        "stone": random.randint(5, 60),
        "iron": random.randint(0, 40),
        "cloth": random.randint(5, 30)
    }
```

**Key Features**:
- Population-based resource thresholds (larger settlements need more)
- Detailed logging to track resource levels
- Urgency calculation for prioritizing tasks
- Fallback to random values for testing
- Proper exception handling

### 5. Create Settlement Resource Task

```python
# Add to settlement_service.py
async def create_settlement_resource_task(self, settlement_id: str) -> Dict[str, Any]:
    """Create a task for gathering resources for a settlement."""
    try:
        # Check resource needs
        needs_result = self._check_resource_needs(settlement_id)
        if not needs_result["needs_resources"]:
            logger.info(f"No resource needs detected for settlement {settlement_id}")
            return {"status": "not_needed", "message": "No resource needs detected"}
        
        # Get settlement data
        settlement_db = self.db.query(Settlements).filter(
            Settlements.settlement_id == settlement_id
        ).first()
        
        if not settlement_db:
            logger.error(f"Settlement {settlement_id} not found")
            return {"status": "error", "message": "Settlement not found"}
        
        settlement_name = needs_result.get("settlement_name", settlement_db.settlement_name)
        resource_type = needs_result["resource_type"]
        amount_needed = needs_result["amount_needed"]
        urgency = needs_result["urgency"]  # 1-6 scale
        
        # Get the world ID
        world_id = settlement_db.world_id
        
        # Generate task details with rich description based on urgency
        descriptions = {
            # Urgency 1-2: Low priority
            1: f"{settlement_name} could use more {resource_type}. The settlement would benefit from a delivery of {amount_needed} units.",
            2: f"{settlement_name} is running a bit low on {resource_type}. Bringing {amount_needed} units would help the settlement's growth.",
            
            # Urgency 3-4: Medium priority
            3: f"{settlement_name} needs {resource_type} to maintain its operations. Deliver {amount_needed} units to keep things running smoothly.",
            4: f"{settlement_name} is facing a shortage of {resource_type}. Delivering {amount_needed} units soon is important for the settlement.",
            
            # Urgency 5-6: High priority
            5: f"{settlement_name} is critically short on {resource_type}! Without a delivery of at least {amount_needed} units, the settlement faces serious problems.",
            6: f"URGENT: {settlement_name} has almost no {resource_type} left! Deliver {amount_needed} units immediately to prevent a crisis!"
        }
        
        # Select appropriate description based on urgency
        description = descriptions.get(urgency, descriptions[3])  # Default to medium if urgency not in range
        
        # Create title based on urgency
        if urgency >= 5:
            title = f"URGENT: {settlement_name} needs {resource_type}"
        else:
            title = f"Deliver {resource_type} to {settlement_name}"
        
        # Calculate rewards based on urgency and amount
        # Higher urgency and larger amounts give better rewards
        base_reward = 10  # Base gold per unit
        urgency_multiplier = 1 + (urgency * 0.2)  # 1.2x for urgency 1, 2.2x for urgency 6
        
        gold_reward = int(amount_needed * base_reward * urgency_multiplier)
        reputation_reward = urgency  # 1-6 reputation points based on urgency
        
        # For very urgent tasks, add item rewards
        item_rewards = []
        if urgency >= 5:
            item_rewards.append({
                "item_type": "settlement_gratitude_token",
                "quantity": 1,
                "description": "A token of appreciation from the settlement"
            })
        
        # Get task service to create the task
        from app.game_state.services.task_service import TaskService
        task_service = TaskService(self.db)
        
        # Create the task
        logger.info(f"Creating resource task for {settlement_name}: {amount_needed} {resource_type} (urgency: {urgency})")
        
        result = await task_service.create_task(
            task_type="SETTLEMENT_RESOURCES",
            title=title,
            description=description,
            world_id=world_id,
            location_id=settlement_id,
            target_id=settlement_id,
            requirements={
                "resources": {
                    resource_type: amount_needed
                }
            },
            rewards={
                "gold": gold_reward,
                "reputation": reputation_reward,
                "items": item_rewards if item_rewards else None
            }
        )
        
        # Log the result
        if result.get("status") == "success":
            logger.info(f"Created resource task {result.get('task_id')} for {settlement_name}")
        else:
            logger.error(f"Failed to create resource task: {result.get('message')}")
        
        return result
        
    except Exception as e:
        logger.exception(f"Error creating settlement resource task: {e}")
        return {"status": "error", "message": str(e)}
```

**Key Features**:
- Richly detailed descriptions that vary based on urgency
- Dynamic titles that highlight urgent tasks
- Reward scaling based on resource amount and urgency
- Special item rewards for critical tasks
- Detailed logging

### 6. Integration with Settlement Worker

Add the following to the settlement_worker.py file:

```python
@app.task
def generate_settlement_tasks(world_id: Optional[str] = None):
    """
    Generate tasks for settlements based on their needs.
    This should be scheduled to run periodically (e.g., daily).
    
    Args:
        world_id: Optional ID of the world to process settlements for
        
    Returns:
        Dict: Summary of task generation results
    """
    logger.info(f"Generating settlement tasks" + (f" for world {world_id}" if world_id else ""))
    
    db = SessionLocal()
    try:
        # Get all settlements in the specified world (or all worlds)
        query = db.query(Settlements)
        if world_id:
            query = query.filter(Settlements.world_id == world_id)
        
        settlements = query.all()
        logger.info(f"Found {len(settlements)} settlements to process")
        
        # Process each settlement
        tasks_created = 0
        settlement_service = SettlementService(db)
        
        for settlement in settlements:
            settlement_id = str(settlement.settlement_id)
            settlement_name = settlement.settlement_name
            
            # Add some randomness to avoid overwhelming players with tasks
            # This creates a natural cycle where settlements need help at different times
            
            # Larger settlements and those with high population have higher chance
            # of generating a task
            population = getattr(settlement, 'population', 100) or 100
            base_chance = 0.2  # 20% base chance
            
            # Population factor: small boost for larger settlements
            pop_factor = min(0.2, population / 500)  # Up to +20% for 500+ population
            
            # Settlement type factor: more complex settlements have more needs
            settlement_type = getattr(settlement, 'settlement_type', 'village')
            type_factors = {
                'village': 0.0,    # No modifier
                'town': 0.1,       # +10% chance
                'city': 0.2,       # +20% chance
                'capital': 0.3     # +30% chance
            }
            type_factor = type_factors.get(settlement_type, 0.0)
            
            # Calculate final chance
            task_chance = base_chance + pop_factor + type_factor
            
            # Log the calculation for debugging
            logger.info(f"Settlement {settlement_name} task chance: {task_chance*100:.1f}% " +
                       f"(base: {base_chance*100}%, pop: +{pop_factor*100:.1f}%, type: +{type_factor*100:.1f}%)")
            
            # Roll for task generation
            if random.random() < task_chance:
                # Create resource task
                result = asyncio.run(settlement_service.create_settlement_resource_task(settlement_id))
                
                if result.get("status") == "success":
                    tasks_created += 1
                    logger.info(f"Created resource task for {settlement_name}")
                elif result.get("status") == "not_needed":
                    logger.info(f"No resource needs for {settlement_name}")
                else:
                    logger.warning(f"Failed to create task for {settlement_name}: {result.get('message')}")
        
        # Return a summary
        return {
            "status": "success",
            "settlements_processed": len(settlements),
            "tasks_created": tasks_created,
            "message": f"Created {tasks_created} settlement tasks from {len(settlements)} settlements"
        }
        
    except Exception as e:
        logger.exception(f"Error generating settlement tasks: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

# Add to celery beat schedule in your task_beat_schedule.py
"""
'generate-settlement-tasks': {
    'task': 'app.workers.settlement_worker.generate_settlement_tasks',
    'schedule': crontab(hour=3, minute=0),  # Run once per day at 3 AM
},
"""
```

**Key Features**:
- Detailed probability calculation based on:
  - Settlement population (larger settlements = more tasks)
  - Settlement type (more complex settlements = more tasks)
- Randomization to avoid task flooding
- Detailed logging for debugging
- Integration with Celery beat scheduling
- Proper exception handling

## Future Enhancements

1. **Weather Effects**: Create weather-triggered events and tasks
   ```python
   # Example integration in trader event system
   if world.current_weather == "storm":
       event_pool.append(("road_washout", 4))  # Severe event during storms
   ```

2. **Faction Influence**: Generate tasks based on faction conflicts and needs
   ```python
   # Example for faction-related tasks
   if settlement.controlling_faction != trader.faction:
       # Chance of harassment if trader is from rival faction
       event_pool.append(("faction_harassment", 3))
   ```

3. **Player History**: Use player's task history to tailor new task generation
   ```python
   # Example for player preference tracking
   completed_tasks = db.query(Tasks).filter(
       Tasks.character_id == character_id,
       Tasks.status == "completed"
   ).all()
   
   # Analyze which types the player completes most
   task_types = [task.task_type for task in completed_tasks]
   preferred_types = Counter(task_types).most_common(3)
   ```

4. **Cascading Events**: Allow unresolved tasks to escalate into larger problems
   ```python
   # Example for task escalation
   stale_tasks = db.query(Tasks).filter(
       Tasks.status == "active",
       Tasks.created_at < (datetime.utcnow() - timedelta(days=7))
   ).all()
   
   for task in stale_tasks:
       if task.task_type == "SETTLEMENT_RESOURCES" and task.resource_type == "food":
           # Food shortage escalates to famine
           create_famine_event(task.settlement_id)
   ```

5. **Seasonal Events**: Create special tasks during specific seasonal transitions
   ```python
   # Example for season transition events
   if world.current_season != world.previous_season:
       if world.current_season == "winter":
           # Generate winter preparation tasks
           for settlement in settlements:
               create_winter_prep_task(settlement.settlement_id)
   ```

## Technical Requirements

- Update database models to track resource levels more precisely
- Create a unified event generation and handling system
- Implement a task priority queue to manage task presentation to players
- Add proper testing for randomized task generation

By following this implementation plan, we can create a rich, dynamic task generation system that provides emergent gameplay while supporting the simulation aspects of the game world.