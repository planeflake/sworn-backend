-- Create a table for logging entity actions including trader movements
CREATE TABLE IF NOT EXISTS entity_action_log (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    
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
    game_time VARCHAR(50),
    
    -- Indexing
    CONSTRAINT entity_action_log_entity_idx UNIQUE (entity_id, timestamp)
);

-- Create indexes for faster querying
CREATE INDEX IF NOT EXISTS entity_action_log_entity_id_idx ON entity_action_log(entity_id);
CREATE INDEX IF NOT EXISTS entity_action_log_entity_type_idx ON entity_action_log(entity_type);
CREATE INDEX IF NOT EXISTS entity_action_log_action_type_idx ON entity_action_log(action_type);
CREATE INDEX IF NOT EXISTS entity_action_log_timestamp_idx ON entity_action_log(timestamp);
CREATE INDEX IF NOT EXISTS entity_action_log_world_id_idx ON entity_action_log(world_id);

-- Comment on table and columns for documentation
COMMENT ON TABLE entity_action_log IS 'Logs actions taken by entities in the game world, including trader movements';
COMMENT ON COLUMN entity_action_log.entity_id IS 'ID of the entity performing the action';
COMMENT ON COLUMN entity_action_log.entity_type IS 'Type of entity (trader, player, etc.)';
COMMENT ON COLUMN entity_action_log.action_type IS 'Primary action category (movement, trade, task, etc.)';
COMMENT ON COLUMN entity_action_log.action_subtype IS 'More specific action detail (depart, arrive, etc.)';
COMMENT ON COLUMN entity_action_log.details IS 'JSON object with additional context-specific details';