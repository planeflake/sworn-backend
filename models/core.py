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

class SettlementResources(Base):
    __tablename__ = 'settlement_resources'
    settlement_resource_id = Column(String, nullable=False, primary_key=True)
    settlement_id = Column(String, nullable=True)
    resource_type_id = Column(String, nullable=True)
    quantity = Column(Integer, nullable=True)
    last_updated = Column(DateTime, nullable=True)

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

class CharacterSkills(Base):
    __tablename__ = 'character_skills'
    character_skill_id = Column(String, nullable=False, primary_key=True)
    character_id = Column(String, nullable=True)
    skill_type_id = Column(String, nullable=True)
    current_level = Column(Integer, nullable=True)
    current_xp = Column(Integer, nullable=True)
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


#class HideId(Base):
#    __tablename__ = 'hide_id'
#    resource_type_id = Column(String, nullable=True)

#class LeatherId(Base):
#    __tablename__ = 'leather_id'
#    resource_type_id = Column(String, nullable=True)

