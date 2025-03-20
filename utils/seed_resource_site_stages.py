#!/usr/bin/env python
import json
import uuid
from datetime import datetime

from database.connection import SessionLocal
from models.core import ResourceSiteTypes, ResourceSiteStages

# Function to create a UUID from a string for consistency
# Function to map our resource names to existing resource IDs
resource_id_map = {
    "iron": "6e7e41a9-c3f6-4723-b510-50bd9f537b8a",  # Iron Ore
    "gold": "aa09429d-4df0-4834-a503-b2653e5a52bd",  # Gold
    "stone": "ba009e21-4bbd-4998-ad15-e7cb32a19636",  # Stone
    "wood": "c4aa2349-409f-4107-ac8a-71331e5f9e92",   # Logs
    "herbs": "51c21030-d6f4-42c4-b63f-343d11a818f5",  # Herbs
    "fish": "ad4b90c1-2e0d-4c1e-9beb-84cfc18f8f5b",   # Fish
    "food": "7bf0d22e-cdef-4ecc-aff6-33ae9c47f21e",   # Meat
    "water": "fc5a66f8-4faa-43ad-a20f-9e386afab6b1",  # Water
}

# Default fantasy theme ID
FANTASY_THEME_ID = "f47ac10b-58cc-4372-a567-0e02b2c3d479"

def get_uuid_from_string(text):
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, text))

def seed_resource_site_stages():
    """Seed resource site stages with production data in the database"""
    db = SessionLocal()
    
    # Define resource site stages with production rates
    site_stages = [
        # Iron Vein Stages
        {
            "stage_id": get_uuid_from_string("iron_vein_undiscovered"),
            "site_type_id": get_uuid_from_string("iron_vein"),
            "stage_code": "undiscovered",
            "stage_name": "Undiscovered Iron Vein",
            "stage_description": "Iron deposits hidden beneath the surface, waiting to be discovered.",
            "building_requirement": None,
            "required_resources": None,
            "production_rates": json.dumps({}),  # No production when undiscovered
            "settlement_effects": None,
            "development_cost": 0,
            "next_stage": "discovered"
        },
        {
            "stage_id": get_uuid_from_string("iron_vein_discovered"),
            "site_type_id": get_uuid_from_string("iron_vein"),
            "stage_code": "discovered",
            "stage_name": "Discovered Iron Vein",
            "stage_description": "Iron deposits have been found but no mining operations have begun.",
            "building_requirement": None,
            "required_resources": None,
            "production_rates": json.dumps({"iron": 1, "stone": 1}),  # Minimal production
            "settlement_effects": None,
            "development_cost": 50,
            "next_stage": "small_mine"
        },
        {
            "stage_id": get_uuid_from_string("iron_vein_small_mine"),
            "site_type_id": get_uuid_from_string("iron_vein"),
            "stage_code": "small_mine",
            "stage_name": "Small Iron Mine",
            "stage_description": "A rudimentary mine extracting modest amounts of iron ore.",
            "building_requirement": "basic_mine",
            "required_resources": json.dumps({"wood": 20, "stone": 10, "tools": 5}),
            "production_rates": json.dumps({"iron": 5, "stone": 2}),
            "settlement_effects": None,
            "development_cost": 100,
            "next_stage": "established_mine"
        },
        {
            "stage_id": get_uuid_from_string("iron_vein_established_mine"),
            "site_type_id": get_uuid_from_string("iron_vein"),
            "stage_code": "established_mine",
            "stage_name": "Established Iron Mine",
            "stage_description": "A well-developed mine with efficient iron extraction.",
            "building_requirement": "mine",
            "required_resources": json.dumps({"wood": 30, "stone": 20, "tools": 10, "iron": 5}),
            "production_rates": json.dumps({"iron": 12, "stone": 3}),
            "settlement_effects": None,
            "development_cost": 200,
            "next_stage": "large_mine"
        },
        {
            "stage_id": get_uuid_from_string("iron_vein_large_mine"),
            "site_type_id": get_uuid_from_string("iron_vein"),
            "stage_code": "large_mine",
            "stage_name": "Large Iron Mine",
            "stage_description": "An expansive mining operation with significant iron output.",
            "building_requirement": "advanced_mine",
            "required_resources": json.dumps({"wood": 50, "stone": 40, "tools": 20, "iron": 15}),
            "production_rates": json.dumps({"iron": 25, "stone": 5}),
            "settlement_effects": None,
            "development_cost": 400,
            "next_stage": "depleted"
        },
        {
            "stage_id": get_uuid_from_string("iron_vein_depleted"),
            "site_type_id": get_uuid_from_string("iron_vein"),
            "stage_code": "depleted",
            "stage_name": "Depleted Iron Mine",
            "stage_description": "The iron vein has been exhausted, yielding minimal resources.",
            "building_requirement": None,
            "required_resources": None,
            "production_rates": json.dumps({"iron": 1, "stone": 1}),
            "settlement_effects": None,
            "development_cost": 0,
            "next_stage": None
        },
        
        # Stone Quarry Stages
        {
            "stage_id": get_uuid_from_string("stone_quarry_undiscovered"),
            "site_type_id": get_uuid_from_string("stone_quarry"),
            "stage_code": "undiscovered",
            "stage_name": "Undiscovered Stone Deposit",
            "stage_description": "An area rich in quality stone for quarrying.",
            "building_requirement": None,
            "required_resources": None,
            "production_rates": json.dumps({}),
            "settlement_effects": None,
            "development_cost": 0,
            "next_stage": "discovered"
        },
        {
            "stage_id": get_uuid_from_string("stone_quarry_discovered"),
            "site_type_id": get_uuid_from_string("stone_quarry"),
            "stage_code": "discovered",
            "stage_name": "Discovered Stone Deposit",
            "stage_description": "Quality stone has been located but quarrying has not begun.",
            "building_requirement": None,
            "required_resources": None,
            "production_rates": json.dumps({"stone": 2}),
            "settlement_effects": None,
            "development_cost": 30,
            "next_stage": "small_quarry"
        },
        {
            "stage_id": get_uuid_from_string("stone_quarry_small_quarry"),
            "site_type_id": get_uuid_from_string("stone_quarry"),
            "stage_code": "small_quarry",
            "stage_name": "Small Quarry",
            "stage_description": "A basic quarry extracting stone for construction.",
            "building_requirement": "basic_quarry",
            "required_resources": json.dumps({"wood": 15, "tools": 3}),
            "production_rates": json.dumps({"stone": 10}),
            "settlement_effects": None,
            "development_cost": 80,
            "next_stage": "quarry"
        },
        {
            "stage_id": get_uuid_from_string("stone_quarry_quarry"),
            "site_type_id": get_uuid_from_string("stone_quarry"),
            "stage_code": "quarry",
            "stage_name": "Established Quarry",
            "stage_description": "A productive quarry providing substantial stone resources.",
            "building_requirement": "quarry",
            "required_resources": json.dumps({"wood": 25, "tools": 8, "stone": 10}),
            "production_rates": json.dumps({"stone": 25}),
            "settlement_effects": None,
            "development_cost": 150,
            "next_stage": "depleted"
        },
        {
            "stage_id": get_uuid_from_string("stone_quarry_depleted"),
            "site_type_id": get_uuid_from_string("stone_quarry"),
            "stage_code": "depleted",
            "stage_name": "Depleted Quarry",
            "stage_description": "The best stone has been harvested, leaving lower quality material.",
            "building_requirement": None,
            "required_resources": None,
            "production_rates": json.dumps({"stone": 5}),
            "settlement_effects": None,
            "development_cost": 0,
            "next_stage": None
        },
        
        # Forest Grove Stages
        {
            "stage_id": get_uuid_from_string("forest_grove_undiscovered"),
            "site_type_id": get_uuid_from_string("forest_grove"),
            "stage_code": "undiscovered",
            "stage_name": "Undiscovered Forest Grove",
            "stage_description": "A pristine wooded area filled with resources.",
            "building_requirement": None,
            "required_resources": None,
            "production_rates": json.dumps({}),
            "settlement_effects": None,
            "development_cost": 0,
            "next_stage": "discovered"
        },
        {
            "stage_id": get_uuid_from_string("forest_grove_discovered"),
            "site_type_id": get_uuid_from_string("forest_grove"),
            "stage_code": "discovered",
            "stage_name": "Discovered Forest Grove",
            "stage_description": "A valuable forest area identified but not yet utilized.",
            "building_requirement": None,
            "required_resources": None,
            "production_rates": json.dumps({"wood": 3, "herbs": 1}),
            "settlement_effects": None,
            "development_cost": 20,
            "next_stage": "small_lumber_camp"
        },
        {
            "stage_id": get_uuid_from_string("forest_grove_small_lumber_camp"),
            "site_type_id": get_uuid_from_string("forest_grove"),
            "stage_code": "small_lumber_camp",
            "stage_name": "Small Lumber Camp",
            "stage_description": "A basic operation harvesting wood from the forest.",
            "building_requirement": "basic_lumber_camp",
            "required_resources": json.dumps({"wood": 10, "tools": 2}),
            "production_rates": json.dumps({"wood": 10, "herbs": 2}),
            "settlement_effects": None,
            "development_cost": 60,
            "next_stage": "lumber_camp"
        },
        {
            "stage_id": get_uuid_from_string("forest_grove_lumber_camp"),
            "site_type_id": get_uuid_from_string("forest_grove"),
            "stage_code": "lumber_camp",
            "stage_name": "Lumber Camp",
            "stage_description": "An established lumber operation with sustainable harvesting.",
            "building_requirement": "lumber_camp",
            "required_resources": json.dumps({"wood": 20, "tools": 5, "stone": 10}),
            "production_rates": json.dumps({"wood": 20, "herbs": 3}),
            "settlement_effects": None,
            "development_cost": 120,
            "next_stage": "forestry_complex"
        },
        {
            "stage_id": get_uuid_from_string("forest_grove_forestry_complex"),
            "site_type_id": get_uuid_from_string("forest_grove"),
            "stage_code": "forestry_complex",
            "stage_name": "Forestry Complex",
            "stage_description": "A sophisticated operation balancing lumber production with forest preservation.",
            "building_requirement": "forestry_complex",
            "required_resources": json.dumps({"wood": 40, "tools": 10, "stone": 20}),
            "production_rates": json.dumps({"wood": 30, "herbs": 5, "resin": 3}),
            "settlement_effects": None,
            "development_cost": 250,
            "next_stage": "managed_forest"
        },
        {
            "stage_id": get_uuid_from_string("forest_grove_managed_forest"),
            "site_type_id": get_uuid_from_string("forest_grove"),
            "stage_code": "managed_forest",
            "stage_name": "Managed Forest",
            "stage_description": "A carefully managed forest providing sustainable yields of various resources.",
            "building_requirement": "ranger_station",
            "required_resources": json.dumps({"wood": 50, "tools": 15, "stone": 30, "herbs": 10}),
            "production_rates": json.dumps({"wood": 25, "herbs": 10, "resin": 5}),
            "settlement_effects": json.dumps({"beauty": 5, "air_quality": 3}),
            "development_cost": 400,
            "next_stage": None
        },
        
        # Herb Grove Stages
        {
            "stage_id": get_uuid_from_string("herb_grove_undiscovered"),
            "site_type_id": get_uuid_from_string("herb_grove"),
            "stage_code": "undiscovered",
            "stage_name": "Undiscovered Herb Grove",
            "stage_description": "An area rich in medicinal and culinary herbs.",
            "building_requirement": None,
            "required_resources": None,
            "production_rates": json.dumps({}),
            "settlement_effects": None,
            "development_cost": 0,
            "next_stage": "discovered"
        },
        {
            "stage_id": get_uuid_from_string("herb_grove_discovered"),
            "site_type_id": get_uuid_from_string("herb_grove"),
            "stage_code": "discovered",
            "stage_name": "Discovered Herb Grove",
            "stage_description": "A valuable collection of herbs has been identified but not yet utilized.",
            "building_requirement": None,
            "required_resources": None,
            "production_rates": json.dumps({"herbs": 3, "food": 1}),
            "settlement_effects": None,
            "development_cost": 30,
            "next_stage": "herb_garden"
        },
        {
            "stage_id": get_uuid_from_string("herb_grove_herb_garden"),
            "site_type_id": get_uuid_from_string("herb_grove"),
            "stage_code": "herb_garden",
            "stage_name": "Herb Garden",
            "stage_description": "A cultivated garden enhancing natural herb growth.",
            "building_requirement": "herb_garden",
            "required_resources": json.dumps({"wood": 10, "tools": 2, "water": 5}),
            "production_rates": json.dumps({"herbs": 12, "food": 4}),
            "settlement_effects": None,
            "development_cost": 80,
            "next_stage": "herbalist_sanctuary"
        },
        {
            "stage_id": get_uuid_from_string("herb_grove_herbalist_sanctuary"),
            "site_type_id": get_uuid_from_string("herb_grove"),
            "stage_code": "herbalist_sanctuary",
            "stage_name": "Herbalist Sanctuary",
            "stage_description": "A carefully maintained sanctuary for rare and valuable herbs.",
            "building_requirement": "herbalist_hut",
            "required_resources": json.dumps({"wood": 20, "tools": 5, "water": 10, "herbs": 15}),
            "production_rates": json.dumps({"herbs": 20, "food": 6, "medicine": 2}),
            "settlement_effects": json.dumps({"health_regeneration": 1.1}),
            "development_cost": 150,
            "next_stage": None
        },
        
        # Fertile Soil Stages
        {
            "stage_id": get_uuid_from_string("fertile_soil_undiscovered"),
            "site_type_id": get_uuid_from_string("fertile_soil"),
            "stage_code": "undiscovered",
            "stage_name": "Undiscovered Fertile Land",
            "stage_description": "Exceptionally fertile soil ideal for farming.",
            "building_requirement": None,
            "required_resources": None,
            "production_rates": json.dumps({}),
            "settlement_effects": None,
            "development_cost": 0,
            "next_stage": "discovered"
        },
        {
            "stage_id": get_uuid_from_string("fertile_soil_discovered"),
            "site_type_id": get_uuid_from_string("fertile_soil"),
            "stage_code": "discovered",
            "stage_name": "Discovered Fertile Land",
            "stage_description": "Prime farmland has been identified but not yet cultivated.",
            "building_requirement": None,
            "required_resources": None,
            "production_rates": json.dumps({"food": 3}),
            "settlement_effects": None,
            "development_cost": 20,
            "next_stage": "small_farm"
        },
        {
            "stage_id": get_uuid_from_string("fertile_soil_small_farm"),
            "site_type_id": get_uuid_from_string("fertile_soil"),
            "stage_code": "small_farm",
            "stage_name": "Small Farm",
            "stage_description": "A modest farm producing food for the settlement.",
            "building_requirement": "basic_farm",
            "required_resources": json.dumps({"wood": 10, "tools": 3, "water": 5}),
            "production_rates": json.dumps({"food": 12}),
            "settlement_effects": None,
            "development_cost": 50,
            "next_stage": "established_farm"
        },
        {
            "stage_id": get_uuid_from_string("fertile_soil_established_farm"),
            "site_type_id": get_uuid_from_string("fertile_soil"),
            "stage_code": "established_farm",
            "stage_name": "Established Farm",
            "stage_description": "A productive farm with diverse crops.",
            "building_requirement": "farm",
            "required_resources": json.dumps({"wood": 20, "tools": 5, "water": 10}),
            "production_rates": json.dumps({"food": 20}),
            "settlement_effects": None,
            "development_cost": 100,
            "next_stage": "plantation"
        },
        {
            "stage_id": get_uuid_from_string("fertile_soil_plantation"),
            "site_type_id": get_uuid_from_string("fertile_soil"),
            "stage_code": "plantation",
            "stage_name": "Plantation",
            "stage_description": "An extensive farming operation with maximum productivity.",
            "building_requirement": "plantation",
            "required_resources": json.dumps({"wood": 30, "tools": 10, "water": 20, "stone": 15}),
            "production_rates": json.dumps({"food": 35}),
            "settlement_effects": None,
            "development_cost": 200,
            "next_stage": None
        },
        
        # Fishing Grounds Stages
        {
            "stage_id": get_uuid_from_string("fishing_grounds_undiscovered"),
            "site_type_id": get_uuid_from_string("fishing_grounds"),
            "stage_code": "undiscovered",
            "stage_name": "Undiscovered Fishing Grounds",
            "stage_description": "Waters teeming with fish waiting to be harvested.",
            "building_requirement": None,
            "required_resources": None,
            "production_rates": json.dumps({}),
            "settlement_effects": None,
            "development_cost": 0,
            "next_stage": "discovered"
        },
        {
            "stage_id": get_uuid_from_string("fishing_grounds_discovered"),
            "site_type_id": get_uuid_from_string("fishing_grounds"),
            "stage_code": "discovered",
            "stage_name": "Discovered Fishing Grounds",
            "stage_description": "Rich fishing waters have been found but not yet exploited.",
            "building_requirement": None,
            "required_resources": None,
            "production_rates": json.dumps({"fish": 3, "food": 2}),
            "settlement_effects": None,
            "development_cost": 20,
            "next_stage": "fishing_spot"
        },
        {
            "stage_id": get_uuid_from_string("fishing_grounds_fishing_spot"),
            "site_type_id": get_uuid_from_string("fishing_grounds"),
            "stage_code": "fishing_spot",
            "stage_name": "Fishing Spot",
            "stage_description": "A basic fishing operation providing fresh fish.",
            "building_requirement": "fishing_spot",
            "required_resources": json.dumps({"wood": 5, "tools": 2}),
            "production_rates": json.dumps({"fish": 10, "food": 8}),
            "settlement_effects": None,
            "development_cost": 40,
            "next_stage": "fishing_dock"
        },
        {
            "stage_id": get_uuid_from_string("fishing_grounds_fishing_dock"),
            "site_type_id": get_uuid_from_string("fishing_grounds"),
            "stage_code": "fishing_dock",
            "stage_name": "Fishing Dock",
            "stage_description": "A proper dock for fishing boats, increasing the catch.",
            "building_requirement": "fishing_dock",
            "required_resources": json.dumps({"wood": 15, "tools": 5, "stone": 5}),
            "production_rates": json.dumps({"fish": 20, "food": 15}),
            "settlement_effects": None,
            "development_cost": 80,
            "next_stage": "fishing_harbor"
        },
        {
            "stage_id": get_uuid_from_string("fishing_grounds_fishing_harbor"),
            "site_type_id": get_uuid_from_string("fishing_grounds"),
            "stage_code": "fishing_harbor",
            "stage_name": "Fishing Harbor",
            "stage_description": "A substantial harbor supporting multiple fishing vessels.",
            "building_requirement": "harbor",
            "required_resources": json.dumps({"wood": 30, "tools": 10, "stone": 20}),
            "production_rates": json.dumps({"fish": 35, "food": 25}),
            "settlement_effects": None,
            "development_cost": 150,
            "next_stage": None
        }
    ]

    try:
        # Check if each site stage already exists
        for stage in site_stages:
            existing = db.query(ResourceSiteStages).filter(
                ResourceSiteStages.stage_id == stage["stage_id"]
            ).first()
            
            if not existing:
                db.add(ResourceSiteStages(**stage))
                print(f"Added site stage: {stage['stage_name']}")
            else:
                print(f"Site stage {stage['stage_name']} already exists")
        
        db.commit()
        print("Resource site stages seeded successfully")
    except Exception as e:
        db.rollback()
        print(f"Error seeding resource site stages: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_resource_site_stages()