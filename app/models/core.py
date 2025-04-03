from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Themes(Base):
    __tablename__ = 'themes'
    theme_id = Column(String, nullable=False, primary_key=True)
    is_active = Column(Boolean, nullable=True)
    created_at = Column(DateTime, nullable=True)
    theme_name = Column(String, nullable=False)
    theme_description = Column(Text, nullable=True)

class Worlds(Base):
    __tablename__ = 'worlds'
    last_updated = Column(DateTime, nullable=True)
    creation_date = Column(DateTime, nullable=True)
    world_id = Column(String, nullable=False, primary_key=True)
    theme_id = Column(String, nullable=True)
    is_premium = Column(Boolean, nullable=True)
    max_players = Column(Integer, nullable=True)
    current_game_day = Column(Integer, nullable=True)
    world_name = Column(String, nullable=False)
    world_seed = Column(String, nullable=True)
    active = Column(Boolean, nullable=True)
    # Season fields
    current_season = Column(String, nullable=True, default="spring")
    day_of_season = Column(Integer, nullable=True, default=1)
    days_per_season = Column(Integer, nullable=True, default=30)
    current_year = Column(Integer, nullable=True, default=1)

class Players(Base):
    __tablename__ = 'players'
    is_premium = Column(Boolean, nullable=True)
    created_at = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)
    player_id = Column(String, nullable=False, primary_key=True)
    password_hash = Column(String, nullable=False)
    username = Column(String, nullable=False)
    email = Column(String, nullable=True)

class Characters(Base):
    __tablename__ = 'characters'
    last_active = Column(DateTime, nullable=True)
    player_id = Column(String, nullable=True)
    world_id = Column(String, nullable=True)
    character_id = Column(String, nullable=False, primary_key=True)
    location_x = Column(Float, nullable=True)
    location_y = Column(Float, nullable=True)
    health = Column(Integer, nullable=True)
    energy = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=True)
    character_name = Column(String, nullable=False)

class ResourceTypes(Base):
    __tablename__ = 'resource_types'
    resource_type_id = Column(String, nullable=False, primary_key=True)
    theme_id = Column(String, nullable=True)
    weight_per_unit = Column(Float, nullable=True)
    is_craftable = Column(Boolean, nullable=True)
    is_stackable = Column(Boolean, nullable=True)
    max_stack_size = Column(Integer, nullable=True)
    base_value = Column(Float, nullable=True)
    resource_code = Column(String, nullable=False)
    resource_name = Column(String, nullable=False)
    resource_category = Column(String, nullable=True)
    description = Column(Text, nullable=True)

class ResourceSiteTypes(Base):
    __tablename__ = 'resource_site_types'
    site_type_id = Column(String, nullable=False, primary_key=True)
    theme_id = Column(String, nullable=True)
    site_code = Column(String, nullable=False)
    site_name = Column(String, nullable=False)
    site_category = Column(String, nullable=True)
    primary_resource_type_id = Column(String, nullable=True)
    secondary_resource_types = Column(String, nullable=True)  # JSON array of resource type IDs
    compatible_area_types = Column(String, nullable=True)  # JSON array of area types
    rarity = Column(Float, nullable=True)  # How rare this site is (0.0-1.0)
    potential_stages = Column(String, nullable=True)  # JSON array of possible development stages
    description = Column(Text, nullable=True)

class ResourceSiteStages(Base):
    __tablename__ = 'resource_site_stages'
    stage_id = Column(String, nullable=False, primary_key=True)
    site_type_id = Column(String, nullable=True)  # Reference to ResourceSiteTypes
    stage_code = Column(String, nullable=False)  # e.g., "discovered", "small_mine", etc.
    stage_name = Column(String, nullable=False)
    stage_description = Column(Text, nullable=True)
    building_requirement = Column(String, nullable=True)  # The building needed for this stage
    required_resources = Column(String, nullable=True)  # JSON object of resources needed to reach this stage
    production_rates = Column(String, nullable=True)  # JSON object of resource_code: amount pairs
    settlement_effects = Column(String, nullable=True)  # JSON object of effects on settlement
    development_cost = Column(Integer, nullable=True)  # Cost to develop to this stage
    next_stage = Column(String, nullable=True)  # Next stage in the progression

class ResourceSites(Base):
    __tablename__ = 'resource_sites'
    site_id = Column(String, nullable=False, primary_key=True)
    settlement_id = Column(String, nullable=True)
    site_type_id = Column(String, nullable=True)  # Reference to ResourceSiteTypes
    current_stage = Column(String, nullable=False)  # e.g., "undiscovered", "discovered", "developing", "operational", "depleted"
    depletion_level = Column(Float, nullable=True, default=0.0)  # 0.0 to 1.0 where 1.0 is fully depleted
    development_level = Column(Float, nullable=True, default=0.0)  # 0.0 to 1.0 where 1.0 is fully developed
    production_multiplier = Column(Float, nullable=True, default=1.0)  # Modifies output based on site quality
    discovery_date = Column(DateTime, nullable=True)
    last_updated = Column(DateTime, nullable=True)
    associated_building_id = Column(String, nullable=True)  # If a building has been constructed on this site

class ResourceCraftingRecipes(Base):
    __tablename__ = 'resource_crafting_recipes'
    recipe_id = Column(String, nullable=False, primary_key=True)
    theme_id = Column(String, nullable=True)
    result_resource_id = Column(String, nullable=True)
    result_quantity = Column(Integer, nullable=True)
    skill_requirement = Column(String, nullable=True)
    building_requirement = Column(String, nullable=True)
    ingredients = Column(String, nullable=True)

class CharacterInventory(Base):
    __tablename__ = 'character_inventory'
    inventory_id = Column(String, nullable=False, primary_key=True)
    character_id = Column(String, nullable=True)
    resource_type_id = Column(String, nullable=True)
    quantity = Column(Integer, nullable=True)
    last_updated = Column(DateTime, nullable=True)

class BuildingTypes(Base):
    __tablename__ = 'building_types'
    area_type_bonuses = Column(String, nullable=True)
    theme_id = Column(String, nullable=True)
    personnel_requirements = Column(String, nullable=True)
    effects = Column(String, nullable=True)
    upgrade_path = Column(String, nullable=True)
    building_type_id = Column(String, nullable=False, primary_key=True)
    construction_time = Column(Integer, nullable=True)
    resource_requirements = Column(String, nullable=True)
    building_code = Column(String, nullable=False)
    building_name = Column(String, nullable=False)
    building_category = Column(String, nullable=True)
    description = Column(Text, nullable=True)

    @classmethod
    def to_dict(cls, building):
        return {
            'building_type_id': getattr(building, 'building_type_id', None),
            'construction_time': getattr(building, 'construction_time', None),
            'resource_requirements': getattr(building, 'resource_requirements', None),
            'building_code': getattr(building, 'building_code', None),
            'building_name': getattr(building, 'building_name', None),
            'building_category': getattr(building, 'building_category', None),
            'description': getattr(building, 'description', None)
        }

class Settlements(Base):
    __tablename__ = 'settlements'
    last_updated = Column(DateTime, nullable=True)
    world_id = Column(String, nullable=True)
    connections = Column(String, nullable=True)
    settlement_id = Column(String, nullable=False, primary_key=True)
    location_x = Column(Float, nullable=True)
    location_y = Column(Float, nullable=True)
    population = Column(Integer, nullable=True)
    foundation_date = Column(DateTime, nullable=True)
    owner_character_id = Column(String, nullable=True)
    threats = Column(String, nullable=True)
    settlement_name = Column(String, nullable=False)
    area_type = Column(String, nullable=False)
    size = Column(String, nullable=True)  # Note: This field is not in the DB yet
    prosperity = Column(Integer, nullable=True)  # Added for settlement economy tracking
    biome = Column(String, nullable=True)  # Added for environment type

class SettlementBuildings(Base):
    __tablename__ = 'settlement_buildings'
    last_updated = Column(DateTime, nullable=True)
    settlement_id = Column(String, nullable=True)
    building_type_id = Column(String, nullable=True)
    settlement_building_id = Column(String, nullable=False, primary_key=True)
    construction_progress = Column(Float, nullable=True)
    health = Column(Integer, nullable=True)
    staff_assigned = Column(String, nullable=True)
    is_operational = Column(Boolean, nullable=True)
    constructed_at = Column(DateTime, nullable=True)
    construction_status = Column(String, nullable=True)

    @classmethod
    def to_dict(cls, building):
        return {
            'settlement_building_id': getattr(building, 'settlement_building_id', None),
            'construction_progress': getattr(building, 'construction_progress', None),
            'health': getattr(building, 'health', None),
            'staff_assigned': getattr(building, 'staff_assigned', None),
            'is_operational': getattr(building, 'is_operational', None),
            'constructed_at': getattr(building, 'constructed_at', None),
            'construction_status': getattr(building, 'construction_status', None)
        }

class SettlementResources(Base):
    __tablename__ = 'settlement_resources'
    settlement_resource_id = Column(String, nullable=False, primary_key=True)
    settlement_id = Column(String, nullable=True)
    resource_type_id = Column(String, nullable=True)
    quantity = Column(Integer, nullable=True)
    last_updated = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=True)

class NpcTypes(Base):
    __tablename__ = 'npc_types'
    theme_id = Column(String, nullable=True)
    base_stats = Column(String, nullable=True)
    skill_levels = Column(String, nullable=True)
    npc_type_id = Column(String, nullable=False, primary_key=True)
    description = Column(Text, nullable=True)
    npc_code = Column(String, nullable=False)
    npc_name = Column(String, nullable=False)
    role = Column(String, nullable=True)

class Npcs(Base):
    __tablename__ = 'npcs'
    last_updated = Column(DateTime, nullable=True)
    world_id = Column(String, nullable=True)
    npc_type_id = Column(String, nullable=True)
    settlement_id = Column(String, nullable=True)
    npc_id = Column(String, nullable=False, primary_key=True)
    health = Column(Integer, nullable=True)
    stats = Column(String, nullable=True)
    skills = Column(String, nullable=True)
    assigned_building_id = Column(String, nullable=True)
    daily_schedule = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=True)
    npc_name = Column(String, nullable=False)
    # Location tracking fields
    current_location_type = Column(String, nullable=True)  # 'settlement' or 'area'
    current_location_id = Column(String, nullable=True)  # Settlement ID or Area ID
    destination_location_type = Column(String, nullable=True)
    destination_location_id = Column(String, nullable=True)

class Traders(Base):
    __tablename__ = 'traders'
    trader_id = Column(String, nullable=False, primary_key=True)
    world_id = Column(String, nullable=True)
    npc_id = Column(String, nullable=True)
    home_settlement_id = Column(String, nullable=True)
    current_settlement_id = Column(String, nullable=True)
    personality = Column(String, nullable=True)
    biome_preferences = Column(String, nullable=True)
    cart_capacity = Column(Integer, nullable=True)
    cart_health = Column(Integer, nullable=True)
    cart_upgrades = Column(String, nullable=True)
    gold = Column(Integer, nullable=True)
    hired_guards = Column(Integer, nullable=True)
    schedule = Column(String, nullable=True)
    life_goal = Column(String, nullable=True)
    last_updated = Column(DateTime, nullable=True)
    npc_name = Column(String, nullable=True)
    destination_id = Column(String, nullable=True)
    # Journey fields
    current_area_id = Column(String, nullable=True)
    journey_path = Column(String, nullable=True)
    path_position = Column(Integer, nullable=True)
    journey_progress = Column(Integer, nullable=True)
    journey_started = Column(DateTime, nullable=True)
    destination_settlement_name = Column(String, nullable=True)

class TraderInventory(Base):
    __tablename__ = 'trader_inventory'
    trader_inventory_id = Column(String, nullable=False, primary_key=True)
    trader_id = Column(String, nullable=True)
    resource_type_id = Column(String, nullable=True)
    quantity = Column(Integer, nullable=True)
    price_modifier = Column(Float, nullable=True)
    last_updated = Column(DateTime, nullable=True)

class SkillTypes(Base):
    __tablename__ = 'skill_types'
    skill_type_id = Column(String, nullable=False, primary_key=True)
    theme_id = Column(String, nullable=True)
    max_level = Column(Integer, nullable=True)
    progression_formula = Column(String, nullable=True)
    effects_per_level = Column(String, nullable=True)
    parent_skill_id = Column(String, nullable=True)
    skill_code = Column(String, nullable=False)
    skill_name = Column(String, nullable=False)
    skill_category = Column(String, nullable=True)
    description = Column(Text, nullable=True)

class Areas(Base):
    __tablename__ = 'areas'
    area_id = Column(String, nullable=False, primary_key=True)
    world_id = Column(String, nullable=True)
    theme_id = Column(String, nullable=True)
    area_name = Column(String, nullable=False)
    area_type = Column(String, nullable=False)  # forest, mountains, plains, etc.
    location_x = Column(Float, nullable=True)
    location_y = Column(Float, nullable=True)
    radius = Column(Float, nullable=True)
    danger_level = Column(Integer, nullable=True)  # 1-10
    resource_richness = Column(Float, nullable=True)  # 0.0-1.0
    created_at = Column(DateTime, nullable=True)
    last_updated = Column(DateTime, nullable=True)
    description = Column(Text, nullable=True)
    connected_settlements = Column(String, nullable=True)  # JSON array of settlement IDs
    connected_areas = Column(String, nullable=True)  # JSON array of area IDs
    type = Column(String, nullable=True)  # 'wilderness', 'dungeon', 'settlement', etc.
    
class AreaEncounterTypes(Base):
    __tablename__ = 'area_encounter_types'
    encounter_type_id = Column(String, nullable=False, primary_key=True)
    theme_id = Column(String, nullable=True)
    encounter_code = Column(String, nullable=False)
    encounter_name = Column(String, nullable=False)
    encounter_category = Column(String, nullable=True)  # combat, reward, neutral, etc.
    min_danger_level = Column(Integer, nullable=True)  # Minimum area danger level for this encounter
    max_danger_level = Column(Integer, nullable=True)  # Maximum area danger level for this encounter
    compatible_area_types = Column(String, nullable=True)  # JSON array of area types
    rarity = Column(Float, nullable=True)  # 0.0-1.0
    description = Column(Text, nullable=True)
    possible_outcomes = Column(String, nullable=True)  # JSON array of outcome IDs
    applicable_area_types = Column(String, nullable=True)  # JSON array of area types
    
class AreaEncounterOutcomes(Base):
    __tablename__ = 'area_encounter_outcomes'
    outcome_id = Column(String, nullable=False, primary_key=True)
    encounter_type_id = Column(String, nullable=True)
    outcome_code = Column(String, nullable=False)
    outcome_name = Column(String, nullable=False)
    outcome_type = Column(String, nullable=True)  # success, failure, neutral
    requirements = Column(String, nullable=True)  # JSON object of requirements (skills, items, etc.)
    rewards = Column(String, nullable=True)  # JSON object of rewards (resources, exp, etc.)
    penalties = Column(String, nullable=True)  # JSON object of penalties (health loss, etc.)
    probability = Column(Float, nullable=True)  # Base probability (0.0-1.0)
    narrative = Column(Text, nullable=True)
    
class AreaEncounters(Base):
    __tablename__ = 'area_encounters'
    encounter_id = Column(String, nullable=False, primary_key=True)
    area_id = Column(String, nullable=True)
    encounter_type_id = Column(String, nullable=True)
    is_active = Column(Boolean, nullable=True, default=True)
    is_completed = Column(Boolean, nullable=True, default=False)
    current_state = Column(String, nullable=True)  # initial, in_progress, resolved
    created_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String, nullable=True)  # Character ID
    resolution_outcome_id = Column(String, nullable=True)  # Reference to outcome
    custom_narrative = Column(Text, nullable=True)
    # References to actual entities in the world
    entity_id = Column(String, nullable=True)  # ID of the entity involved (NPC, trader, etc.)
    entity_type = Column(String, nullable=True)  # Type of entity (trader, npc, bandit, animal, etc.)
    faction_id = Column(String, nullable=True)  # ID of the faction involved (if applicable)
    secret_revealed = Column(Boolean, nullable=True, default=False)  # Whether a secret was revealed
    secret_id = Column(String, nullable=True)  # Reference to a secret discovered

class AreaSecrets(Base):
    __tablename__ = 'area_secrets'
    secret_id = Column(String, nullable=False, primary_key=True)
    area_id = Column(String, nullable=True)
    theme_id = Column(String, nullable=True)
    secret_name = Column(String, nullable=False)
    secret_type = Column(String, nullable=True)  # history, treasure, quest, etc.
    description = Column(Text, nullable=True)
    is_discovered = Column(Boolean, nullable=True, default=False)
    discovered_by = Column(String, nullable=True)  # Character ID that discovered it
    discovered_at = Column(DateTime, nullable=True)
    difficulty = Column(Integer, nullable=True)  # 1-10 how hard to discover
    requirements = Column(String, nullable=True)  # JSON of required skills/conditions to discover
    rewards = Column(String, nullable=True)  # JSON of rewards for discovering
    related_quest_id = Column(String, nullable=True)  # If this secret starts a quest
    related_npc_id = Column(String, nullable=True)  # If this secret involves an NPC
    hints = Column(String, nullable=True)  # JSON array of hints that can be found
    
class TravelRoutes(Base):
    __tablename__ = 'travel_routes'
    route_id = Column(String, nullable=False, primary_key=True)
    world_id = Column(String, nullable=True)
    start_settlement_id = Column(String, nullable=True)
    end_settlement_id = Column(String, nullable=True)
    path = Column(String, nullable=True)  # JSON array of area IDs or waypoints
    total_distance = Column(Float, nullable=True)
    danger_level = Column(Integer, nullable=True)  # 1-10
    path_condition = Column(String, nullable=True)  # good, moderate, poor, etc.
    travel_time = Column(Integer, nullable=True)  # In hours or game time units
    created_at = Column(DateTime, nullable=True)
    last_updated = Column(DateTime, nullable=True)

class WorldEvents(Base):
    __tablename__ = 'world_events'
    created_at = Column(DateTime, nullable=True)
    world_id = Column(String, nullable=True)
    is_active = Column(Boolean, nullable=True)
    resolution_conditions = Column(String, nullable=True)
    event_id = Column(String, nullable=False, primary_key=True)
    location_x = Column(Float, nullable=True)
    location_y = Column(Float, nullable=True)
    radius = Column(Float, nullable=True)
    start_day = Column(Integer, nullable=True)
    duration = Column(Integer, nullable=True)
    effects = Column(String, nullable=True)
    event_type = Column(String, nullable=False)
    event_name = Column(String, nullable=True)
    description = Column(Text, nullable=True)
