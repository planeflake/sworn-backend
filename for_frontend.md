# Backend Development Plan for Frontend Support

## Required Backend Components

This document outlines the backend components and adjustments needed to support a mini frontend showing world data, settlement information, and player tasks.

## Implemented Components

✅ **Task Database Models**
- Created SQLAlchemy models for tasks in `app/models/tasks.py`
- Added Pydantic schemas in `app/schemas/tasks.py`

✅ **Task Entity & Manager**
- Implemented Task entity in `app/game_state/entities/task.py`
- Created TaskManager in `app/game_state/managers/task_manager.py`

✅ **Task Service**
- Implemented TaskService in `app/game_state/services/task_service.py`
- Added task creation, completion, and query methods

✅ **Task API Routes**
- Added task router in `app/routers/task.py`
- Registered router in `app/main.py`

✅ **Task Worker**
- Created worker in `app/workers/task_worker.py` 
- Registered in Celery in `app/workers/celery_app.py`

✅ **Trader Integration**
- Updated Trader entity in `app/game_state/entities/trader.py`
- Modified TraderService in `app/game_state/services/trader_service.py`
- Added task-based movement restrictions
- Implemented trader task completion handler

## Components Still Needed

### 1. Database Migrations (Added)
- [x] Create a migration script to add task-related tables (`migrations/versions/create_task_tables.py`)
- [x] Add `can_move` and `active_task_id` columns to the Traders table
- [x] Add `requires_assistance` and `task_id` columns to the AreaEncounters table

### 2. Task Type Seeds (Added)
- [x] Create a script to seed initial TaskTypes in the database (`utils/seed_task_types.py`)
- [x] Define standard task types (resource gathering, trader assistance, etc.)

### 3. Run Migrations and Seeds
- [x] Copy alembic.ini from claude/ to project root
- [x] Run the Alembic migration: `alembic upgrade head`
- [x] Run the task types seed script: `python utils/seed_task_types.py`

### 3. Settlement Task Integration
- [ ] Update Settlement entity and service to support tasks
- [ ] Add methods to create settlement-related tasks
- [ ] Add API endpoints for settlement tasks

### 4. Character Integration
- [ ] Update Character entity to track active and completed tasks
- [ ] Implement task reward distribution to characters

### 5. Testing
- [ ] Create unit tests for the task system
- [ ] Test the trader-task integration
- [ ] Test API endpoints

## API Routes Available for Frontend

### Task Routes
- `GET /tasks/?world_id={world_id}` - List all available tasks in a world
- `GET /tasks/character/{character_id}` - Get tasks assigned to a character
- `GET /tasks/{task_id}` - Get details of a specific task
- `POST /tasks/{task_id}/accept` - Accept a task for a character
- `POST /tasks/{task_id}/complete` - Complete a task and receive rewards
- `GET /tasks/trader/{trader_id}` - Get tasks related to a trader
- `GET /tasks/location/{location_id}?world_id={world_id}` - Get tasks at a location

### Trader Task Routes
- `POST /traders/{trader_id}/complete-task/{task_id}` - Complete a task for a trader

## Frontend Considerations

When building the frontend, you'll need to:

1. **Task List Component**
   - Display available tasks for a world/location
   - Show task details including rewards
   - Provide accept/complete buttons

2. **Trader Integration**
   - Display traders with pending tasks
   - Show task requirements and completion flow
   - Update trader state after task completion

3. **Character Task Tracking**
   - Show active and completed tasks for a character
   - Display task progress and rewards
   - Manage task inventory requirements

4. **World State Display**
   - Show day, season, weather information
   - Display settlement information
   - Link settlements to resource sites

## Next Steps

1. Create the database migrations to support the task system
2. Seed initial task types
3. Implement settlement task integration
4. Add character task reward handling
5. Test the complete task workflow
6. Build the frontend components that use these APIs