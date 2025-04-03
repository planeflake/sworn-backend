# Trader Activity Logging System

This document describes the trader activity logging system, which tracks trader movements, trades, and other activities in a PostgreSQL database.

## Overview

The trader activity logging system records detailed information about trader actions in the game world. This includes:

- Movements between settlements and areas
- Trade activities
- Task completions
- Location changes
- Encounters

The logs are stored in the `entity_action_log` table and can be queried via API endpoints.

## Database Schema

The entity action log table has the following schema:

```sql
CREATE TABLE entity_action_log (
    log_id UUID PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    
    -- Entity information
    entity_id UUID NOT NULL,
    entity_type VARCHAR(50) NOT NULL, -- 'trader', 'player', 'npc', etc.
    entity_name VARCHAR(255),
    
    -- Action details
    action_type VARCHAR(50) NOT NULL, -- 'movement', 'trade', 'task', etc.
    action_subtype VARCHAR(50), -- More specific action like 'depart', 'arrive', 'buy', 'sell', etc.
    
    -- Locations
    from_location_id UUID,
    from_location_type VARCHAR(50), -- 'settlement', 'area', etc.
    from_location_name VARCHAR(255),
    
    to_location_id UUID,
    to_location_type VARCHAR(50),
    to_location_name VARCHAR(255),
    
    -- Related entities
    related_entity_id UUID, -- Another entity involved in the action
    related_entity_type VARCHAR(50),
    related_entity_name VARCHAR(255),
    
    -- Additional data
    details JSONB, -- Flexible field for additional context
    
    -- Tracking fields
    world_id UUID NOT NULL,
    game_day INTEGER,
    game_time VARCHAR(50)
);
```

## Logging Service

The `LoggingService` class in `app/game_state/services/logging_service.py` provides methods for logging and retrieving entity actions:

- `log_action()` - General method for logging any entity action
- `log_trader_movement()` - Specialized method for logging trader movement
- `log_trader_trade()` - Specialized method for logging trader trade activities
- `get_trader_action_history()` - Retrieve a trader's action history
- `get_trader_movement_history()` - Retrieve a trader's movement history

## Integration with Trader Worker

The trader worker has been updated to log activities at key points:

1. **Starting a Journey**
   - When a trader leaves a settlement to begin a journey

2. **Area Movement**
   - When a trader moves from one area to another during a journey

3. **Journey Completion**
   - When a trader arrives at their destination settlement

## API Endpoints

The following API endpoints are available for retrieving trader action logs:

1. **GET /traders/{trader_id}/movement_history**
   - Returns a history of trader movements
   - Supports limiting the number of results

2. **GET /traders/{trader_id}/action_history**
   - Returns all actions for a trader
   - Supports filtering by action type and limiting the number of results

## Sample Log Structure

Here's an example of a trader movement log:

```json
{
  "timestamp": "2025-03-29T15:30:45.123456",
  "trader_id": "550e8400-e29b-41d4-a716-446655440000",
  "trader_name": "Orrin Silverhand",
  "action_type": "movement",
  "action_subtype": "journey_started",
  "from_location": {
    "id": "a3e8f7b2-c29d-45e8-b712-345678901234",
    "type": "settlement",
    "name": "Riverdale"
  },
  "to_location": {
    "id": "b4d9f8c3-d30e-46f9-c823-456789012345",
    "type": "settlement",
    "name": "Highmont"
  },
  "details": {
    "action": "journey_started",
    "path_length": 5,
    "first_area": "c5e0f9d4-e41f-57g0-d934-567890123456"
  },
  "game_day": 42
}
```

## Querying Action Logs

You can use the API endpoints to analyze trader behavior patterns, track trader movements, or visualize trade routes. 

For example, to see a trader's recent movements:

```http
GET /traders/550e8400-e29b-41d4-a716-446655440000/movement_history?limit=10
```

To view all trade actions:

```http
GET /traders/550e8400-e29b-41d4-a716-446655440000/action_history?action_type=trade&limit=20
```

## Future Enhancements

Planned enhancements to the logging system include:

1. Advanced analytics and visualization of trader routes
2. Tracking of profit/loss across trade activities
3. Journey duration statistics
4. Integration with game events and weather systems
5. Heatmaps of trader activity by region