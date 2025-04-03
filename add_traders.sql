-- Create new NPCs and traders with trading skills
-- First, get a world_id to use for our traders
DO $$
DECLARE
    world_id_val UUID;
    settlement_id_val UUID;
    npc_id_val UUID;
    trader_id_val UUID;
    npc_type_id_val UUID;
    
BEGIN
    -- Get first world_id from the database
    SELECT world_id INTO world_id_val FROM worlds LIMIT 1;
    
    -- If no world exists, create one for testing
    IF world_id_val IS NULL THEN
        world_id_val := gen_random_uuid();
        INSERT INTO worlds (world_id, world_name, active, created_at, last_updated)
        VALUES (world_id_val, 'Test World', TRUE, NOW(), NOW());
    END IF;
    
    -- Get a settlement for the traders to start in
    SELECT settlement_id INTO settlement_id_val FROM settlements LIMIT 1;
    
    -- If no settlement exists, create one for testing
    IF settlement_id_val IS NULL THEN
        settlement_id_val := gen_random_uuid();
        INSERT INTO settlements (settlement_id, world_id, settlement_name, area_type, location_x, location_y, population, last_updated)
        VALUES (settlement_id_val, world_id_val, 'Trading Post', 'town', 100, 100, 500, NOW());
    END IF;
    
    -- Check if we have a trader-type npc_type
    SELECT npc_type_id INTO npc_type_id_val FROM npc_types WHERE npc_code = 'trader' LIMIT 1;
    
    -- If no trader npc_type exists, create one
    IF npc_type_id_val IS NULL THEN
        npc_type_id_val := gen_random_uuid();
        INSERT INTO npc_types (npc_type_id, npc_code, npc_name, role, description)
        VALUES (npc_type_id_val, 'trader', 'Merchant', 'trading', 'A trader who buys and sells goods.');
    END IF;
    
    -- Create NPC 1: Master Trader
    npc_id_val := gen_random_uuid();
    INSERT INTO npcs (
        npc_id, 
        world_id, 
        npc_type_id,
        settlement_id, 
        npc_name, 
        health, 
        stats, 
        skills, 
        current_location_type, 
        current_location_id, 
        created_at, 
        last_updated
    ) VALUES (
        npc_id_val,
        world_id_val,
        npc_type_id_val,
        settlement_id_val,
        'Orrin Silverhand',
        100,
        '{"strength": 10, "dexterity": 14, "intelligence": 18, "charisma": 20}',
        '{"trading": 95, "negotiation": 90, "appraisal": 85, "leadership": 75}',
        'settlement',
        settlement_id_val,
        NOW(),
        NOW()
    );
    
    -- Create corresponding Trader 1
    trader_id_val := gen_random_uuid();
    INSERT INTO traders (
        trader_id, 
        world_id, 
        npc_id, 
        npc_name, 
        home_settlement_id, 
        current_settlement_id, 
        personality, 
        biome_preferences, 
        cart_capacity, 
        cart_health,
        cart_upgrades,
        gold,
        hired_guards,
        last_updated
    ) VALUES (
        trader_id_val,
        world_id_val,
        npc_id_val,
        'Orrin Silverhand',
        settlement_id_val,
        settlement_id_val,
        '{"shrewd": 0.9, "honest": 0.7, "ambitious": 0.8}',
        '{"coastal": 0.8, "forest": 0.6, "mountain": 0.4}',
        1000,
        100,
        '["reinforced_axles", "weather_protection", "hidden_compartment"]',
        5000,
        3,
        NOW()
    );
    
    -- Create NPC 2: Exotic Goods Specialist
    npc_id_val := gen_random_uuid();
    INSERT INTO npcs (
        npc_id, 
        world_id, 
        npc_type_id,
        settlement_id, 
        npc_name, 
        health, 
        stats, 
        skills, 
        current_location_type, 
        current_location_id, 
        created_at, 
        last_updated
    ) VALUES (
        npc_id_val,
        world_id_val,
        npc_type_id_val,
        settlement_id_val,
        'Lyra Nightshade',
        90,
        '{"strength": 8, "dexterity": 16, "intelligence": 19, "charisma": 18}',
        '{"trading": 85, "appraisal": 92, "alchemy": 75, "persuasion": 80}',
        'settlement',
        settlement_id_val,
        NOW(),
        NOW()
    );
    
    -- Create corresponding Trader 2
    trader_id_val := gen_random_uuid();
    INSERT INTO traders (
        trader_id, 
        world_id, 
        npc_id, 
        npc_name, 
        home_settlement_id, 
        current_settlement_id, 
        personality, 
        biome_preferences, 
        cart_capacity, 
        cart_health,
        cart_upgrades,
        gold,
        hired_guards,
        last_updated
    ) VALUES (
        trader_id_val,
        world_id_val,
        npc_id_val,
        'Lyra Nightshade',
        settlement_id_val,
        settlement_id_val,
        '{"mysterious": 0.9, "knowledgeable": 0.8, "secretive": 0.7}',
        '{"swamp": 0.7, "desert": 0.6, "jungle": 0.9}',
        800,
        95,
        '["specialized_containers", "arcane_wards", "climate_control"]',
        4200,
        2,
        NOW()
    );
    
    -- Create NPC 3: Caravan Master
    npc_id_val := gen_random_uuid();
    INSERT INTO npcs (
        npc_id, 
        world_id, 
        npc_type_id,
        settlement_id, 
        npc_name, 
        health, 
        stats, 
        skills, 
        current_location_type, 
        current_location_id, 
        created_at, 
        last_updated
    ) VALUES (
        npc_id_val,
        world_id_val,
        npc_type_id_val,
        settlement_id_val,
        'Thorne Ironwood',
        120,
        '{"strength": 16, "dexterity": 12, "intelligence": 14, "charisma": 16}',
        '{"trading": 80, "survival": 85, "navigation": 90, "combat": 70}',
        'settlement',
        settlement_id_val,
        NOW(),
        NOW()
    );
    
    -- Create corresponding Trader 3
    trader_id_val := gen_random_uuid();
    INSERT INTO traders (
        trader_id, 
        world_id, 
        npc_id, 
        npc_name, 
        home_settlement_id, 
        current_settlement_id, 
        personality, 
        biome_preferences, 
        cart_capacity, 
        cart_health,
        cart_upgrades,
        gold,
        hired_guards,
        last_updated
    ) VALUES (
        trader_id_val,
        world_id_val,
        npc_id_val,
        'Thorne Ironwood',
        settlement_id_val,
        settlement_id_val,
        '{"brave": 0.8, "practical": 0.9, "protective": 0.7}',
        '{"plains": 0.9, "forest": 0.7, "mountain": 0.8}',
        1200,
        100,
        '["additional_wagon", "guard_post", "animal_housing"]',
        3800,
        5,
        NOW()
    );
    
    -- Create NPC 4: Traveling Peddler
    npc_id_val := gen_random_uuid();
    INSERT INTO npcs (
        npc_id, 
        world_id, 
        npc_type_id,
        settlement_id, 
        npc_name, 
        health, 
        stats, 
        skills, 
        current_location_type, 
        current_location_id, 
        created_at, 
        last_updated
    ) VALUES (
        npc_id_val,
        world_id_val,
        npc_type_id_val,
        settlement_id_val,
        'Milo Quickfoot',
        80,
        '{"strength": 9, "dexterity": 18, "intelligence": 15, "charisma": 17}',
        '{"trading": 75, "stealth": 70, "sleight_of_hand": 80, "bargaining": 90}',
        'settlement',
        settlement_id_val,
        NOW(),
        NOW()
    );
    
    -- Create corresponding Trader 4
    trader_id_val := gen_random_uuid();
    INSERT INTO traders (
        trader_id, 
        world_id, 
        npc_id, 
        npc_name, 
        home_settlement_id, 
        current_settlement_id, 
        personality, 
        biome_preferences, 
        cart_capacity, 
        cart_health,
        cart_upgrades,
        gold,
        hired_guards,
        last_updated
    ) VALUES (
        trader_id_val,
        world_id_val,
        npc_id_val,
        'Milo Quickfoot',
        settlement_id_val,
        settlement_id_val,
        '{"charming": 0.9, "opportunistic": 0.8, "adaptable": 0.9}',
        '{"urban": 0.9, "coastal": 0.7, "plains": 0.6}',
        500,
        85,
        '["lightweight_frame", "quick_release_harness", "concealed_compartments"]',
        2500,
        1,
        NOW()
    );
    
    -- Create NPC 5: Trading Consortium Representative
    npc_id_val := gen_random_uuid();
    INSERT INTO npcs (
        npc_id, 
        world_id, 
        npc_type_id,
        settlement_id, 
        npc_name, 
        health, 
        stats, 
        skills, 
        current_location_type, 
        current_location_id, 
        created_at, 
        last_updated
    ) VALUES (
        npc_id_val,
        world_id_val,
        npc_type_id_val,
        settlement_id_val,
        'Seraphina Goldweaver',
        95,
        '{"strength": 10, "dexterity": 14, "intelligence": 20, "charisma": 19}',
        '{"trading": 95, "diplomacy": 90, "economics": 95, "law": 85}',
        'settlement',
        settlement_id_val,
        NOW(),
        NOW()
    );
    
    -- Create corresponding Trader 5
    trader_id_val := gen_random_uuid();
    INSERT INTO traders (
        trader_id, 
        world_id, 
        npc_id, 
        npc_name, 
        home_settlement_id, 
        current_settlement_id, 
        personality, 
        biome_preferences, 
        cart_capacity, 
        cart_health,
        cart_upgrades,
        gold,
        hired_guards,
        last_updated
    ) VALUES (
        trader_id_val,
        world_id_val,
        npc_id_val,
        'Seraphina Goldweaver',
        settlement_id_val,
        settlement_id_val,
        '{"sophisticated": 0.9, "calculating": 0.8, "diplomatic": 0.9}',
        '{"urban": 0.9, "coastal": 0.8, "mountain": 0.4}',
        1500,
        100,
        '["luxury_fittings", "secure_lockboxes", "diplomatic_insignia"]',
        10000,
        4,
        NOW()
    );
    
END $$;

-- Output success message when script completes
SELECT 'Successfully added 5 new NPCs and traders with trading skills' as result;