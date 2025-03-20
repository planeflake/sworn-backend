#!/usr/bin/env python
import json
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

from database.connection import SessionLocal
from models.core import ResourceSiteTypes, ResourceTypes, Settlements

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

# Function to create a UUID from a string for consistency
def get_uuid_from_string(text):
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, text))

def seed_resource_site_types():
    """Seed resource site types in the database"""
    db = SessionLocal()
    
    # First, ensure we have resource types in the database
    resource_types = {
        "iron": {
            "resource_type_id": get_uuid_from_string("iron"),
            "resource_code": "iron",
            "resource_name": "Iron",
            "resource_category": "metal",
            "weight_per_unit": 5.0,
            "is_craftable": False,
            "is_stackable": True,
            "max_stack_size": 50,
            "base_value": 8.0,
            "description": "Metal used for tools and weapons"
        },
        "gold": {
            "resource_type_id": get_uuid_from_string("gold"),
            "resource_code": "gold",
            "resource_name": "Gold",
            "resource_category": "metal",
            "weight_per_unit": 5.0,
            "is_craftable": False,
            "is_stackable": True,
            "max_stack_size": 20,
            "base_value": 30.0,
            "description": "Precious metal for trade and luxury items"
        },
        "stone": {
            "resource_type_id": get_uuid_from_string("stone"),
            "resource_code": "stone",
            "resource_name": "Stone",
            "resource_category": "building",
            "weight_per_unit": 8.0,
            "is_craftable": False,
            "is_stackable": True,
            "max_stack_size": 50,
            "base_value": 3.0,
            "description": "Basic building material"
        },
        "wood": {
            "resource_type_id": get_uuid_from_string("wood"),
            "resource_code": "wood",
            "resource_name": "Wood",
            "resource_category": "building",
            "weight_per_unit": 3.0,
            "is_craftable": False,
            "is_stackable": True,
            "max_stack_size": 50,
            "base_value": 4.0,
            "description": "Basic building and crafting material"
        },
        "herbs": {
            "resource_type_id": get_uuid_from_string("herbs"),
            "resource_code": "herbs",
            "resource_name": "Herbs",
            "resource_category": "flora",
            "weight_per_unit": 0.5,
            "is_craftable": False,
            "is_stackable": True,
            "max_stack_size": 40,
            "base_value": 6.0,
            "description": "Medicinal and culinary herbs"
        },
        "fish": {
            "resource_type_id": get_uuid_from_string("fish"),
            "resource_code": "fish",
            "resource_name": "Fish",
            "resource_category": "food",
            "weight_per_unit": 1.0,
            "is_craftable": False,
            "is_stackable": True,
            "max_stack_size": 30,
            "base_value": 5.0,
            "description": "Nutritious food from water sources"
        },
        "food": {
            "resource_type_id": get_uuid_from_string("food"),
            "resource_code": "food",
            "resource_name": "Food",
            "resource_category": "food",
            "weight_per_unit": 1.0,
            "is_craftable": False,
            "is_stackable": True,
            "max_stack_size": 40,
            "base_value": 4.0,
            "description": "General food supplies"
        }
    }
    
    # Check if resource types already exist and insert if not
    for code, resource_data in resource_types.items():
        existing = db.query(ResourceTypes).filter(
            ResourceTypes.resource_type_id == resource_data["resource_type_id"]
        ).first()
        
        if not existing:
            db.add(ResourceTypes(**resource_data))
            print(f"Added resource type: {resource_data['resource_name']}")
    
    # Define resource site types
    resource_site_types = [
        # Mining Sites
        {
            "site_type_id": get_uuid_from_string("iron_vein"),
            "site_code": "iron_vein",
            "site_name": "Iron Vein",
            "site_category": "mining",
            "primary_resource_type_id": get_uuid_from_string("iron"),
            "secondary_resource_types": json.dumps(["stone"]),
            "compatible_area_types": json.dumps(["mountains", "hills"]),
            "rarity": 0.7,
            "potential_stages": json.dumps([
                "undiscovered", 
                "discovered", 
                "small_mine", 
                "established_mine", 
                "large_mine", 
                "depleted"
            ]),
            "description": "Iron deposits that can be mined for metal production."
        },
        {
            "site_type_id": get_uuid_from_string("gold_vein"),
            "site_code": "gold_vein",
            "site_name": "Gold Vein",
            "site_category": "mining",
            "primary_resource_type_id": get_uuid_from_string("gold"),
            "secondary_resource_types": json.dumps(["stone"]),
            "compatible_area_types": json.dumps(["mountains"]),
            "rarity": 0.3,
            "potential_stages": json.dumps([
                "undiscovered", 
                "discovered", 
                "gold_mine", 
                "productive_gold_mine", 
                "depleted"
            ]),
            "description": "Precious gold deposits valuable for trade and crafting."
        },
        
        # Stone Resources
        {
            "site_type_id": get_uuid_from_string("stone_quarry"),
            "site_code": "stone_quarry",
            "site_name": "Stone Quarry",
            "site_category": "mining",
            "primary_resource_type_id": get_uuid_from_string("stone"),
            "secondary_resource_types": json.dumps([]),
            "compatible_area_types": json.dumps(["mountains", "hills"]),
            "rarity": 0.8,
            "potential_stages": json.dumps([
                "undiscovered", 
                "discovered", 
                "small_quarry", 
                "quarry", 
                "depleted"
            ]),
            "description": "Quality stone deposits ideal for construction."
        },
        
        # Forest Resources
        {
            "site_type_id": get_uuid_from_string("forest_grove"),
            "site_code": "forest_grove",
            "site_name": "Forest Grove",
            "site_category": "forestry",
            "primary_resource_type_id": get_uuid_from_string("wood"),
            "secondary_resource_types": json.dumps(["herbs"]),
            "compatible_area_types": json.dumps(["forest"]),
            "rarity": 0.9,
            "potential_stages": json.dumps([
                "undiscovered", 
                "discovered", 
                "small_lumber_camp", 
                "lumber_camp", 
                "forestry_complex", 
                "managed_forest"
            ]),
            "description": "A rich forest area with various valuable resources."
        },
        
        # Herb Resources
        {
            "site_type_id": get_uuid_from_string("herb_grove"),
            "site_code": "herb_grove",
            "site_name": "Herb Grove",
            "site_category": "gathering",
            "primary_resource_type_id": get_uuid_from_string("herbs"),
            "secondary_resource_types": json.dumps(["food"]),
            "compatible_area_types": json.dumps(["forest", "swamp"]),
            "rarity": 0.5,
            "potential_stages": json.dumps([
                "undiscovered", 
                "discovered", 
                "herb_garden", 
                "herbalist_sanctuary"
            ]),
            "description": "An area rich in medicinal herbs and edible plants."
        },
        
        # Farming Resources
        {
            "site_type_id": get_uuid_from_string("fertile_soil"),
            "site_code": "fertile_soil",
            "site_name": "Fertile Soil",
            "site_category": "farming",
            "primary_resource_type_id": get_uuid_from_string("food"),
            "secondary_resource_types": json.dumps(["herbs"]),
            "compatible_area_types": json.dumps(["plains", "river"]),
            "rarity": 0.7,
            "potential_stages": json.dumps([
                "undiscovered", 
                "discovered", 
                "small_farm", 
                "established_farm", 
                "plantation"
            ]),
            "description": "Exceptionally fertile land ideal for growing crops."
        },
        
        # Fishing Resources
        {
            "site_type_id": get_uuid_from_string("fishing_grounds"),
            "site_code": "fishing_grounds",
            "site_name": "Fishing Grounds",
            "site_category": "fishing",
            "primary_resource_type_id": get_uuid_from_string("fish"),
            "secondary_resource_types": json.dumps(["food"]),
            "compatible_area_types": json.dumps(["coastal", "river"]),
            "rarity": 0.7,
            "potential_stages": json.dumps([
                "undiscovered", 
                "discovered", 
                "fishing_spot", 
                "fishing_dock", 
                "fishing_harbor"
            ]),
            "description": "Waters teeming with fish ready to be harvested."
        }
    ]

    try:
        # Check if each site type already exists
        for site_type in resource_site_types:
            existing = db.query(ResourceSiteTypes).filter(
                ResourceSiteTypes.site_type_id == site_type["site_type_id"]
            ).first()
            
            # Add the theme ID to make it a fantasy theme resource
            site_type["theme_id"] = FANTASY_THEME_ID
            
            if not existing:
                db.add(ResourceSiteTypes(**site_type))
                print(f"Added site type: {site_type['site_name']}")
            else:
                # Update the theme ID if needed
                if existing.theme_id != FANTASY_THEME_ID:
                    existing.theme_id = FANTASY_THEME_ID
                    print(f"Updated theme ID for site type: {site_type['site_name']}")
                else:
                    print(f"Site type {site_type['site_name']} already exists")
        
        db.commit()
        print("Resource site types seeded successfully")
    except Exception as e:
        db.rollback()
        print(f"Error seeding resource site types: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_resource_site_types()