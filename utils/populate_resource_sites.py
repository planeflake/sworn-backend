#!/usr/bin/env python
import json
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

from database.connection import SessionLocal
from models.core import ResourceSiteTypes, ResourceSites, Settlements

# Function to create a UUID from a string for consistency
def get_uuid_from_string(text):
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, text))

def create_resource_site_types():
    """Create basic resource site types in the database"""
    db = SessionLocal()
    
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
            "secondary_resource_types": json.dumps(["stone", "silver"]),
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
            "secondary_resource_types": json.dumps(["herbs", "berries"]),
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
            "secondary_resource_types": json.dumps(["berries", "mushrooms"]),
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
            "secondary_resource_types": json.dumps(["wheat", "vegetables"]),
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
            "secondary_resource_types": json.dumps(["salt"]),
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
        # First check if they already exist
        for site_type in resource_site_types:
            existing = db.query(ResourceSiteTypes).filter(
                ResourceSiteTypes.site_type_id == site_type["site_type_id"]
            ).first()
            
            if not existing:
                db.add(ResourceSiteTypes(**site_type))
                print(f"Added site type: {site_type['site_name']}")
        
        db.commit()
        print("Resource site types created successfully")
    except Exception as e:
        db.rollback()
        print(f"Error creating resource site types: {str(e)}")
    finally:
        db.close()

def add_resource_sites_to_settlement(settlement_id):
    """Add sample resource sites to a specific settlement"""
    db = SessionLocal()
    
    # First check if the settlement exists
    settlement = db.query(Settlements).filter(
        Settlements.settlement_id == settlement_id
    ).first()
    
    if not settlement:
        print(f"Settlement with ID {settlement_id} not found")
        db.close()
        return
    
    # Get the area type of the settlement to determine compatible resource sites
    area_type = settlement.area_type
    
    # Find compatible resource site types
    site_types = db.query(ResourceSiteTypes).all()
    compatible_sites = []
    
    for site_type in site_types:
        compatible_areas = json.loads(site_type.compatible_area_types) if site_type.compatible_area_types else []
        if area_type in compatible_areas:
            compatible_sites.append(site_type)
    
    if not compatible_sites:
        print(f"No compatible resource site types found for area type: {area_type}")
        db.close()
        return
    
    # Create some sample resource sites for the settlement
    sample_sites = []
    timestamp = datetime.now()
    
    # Add 2-3 resource sites per settlement
    for i, site_type in enumerate(compatible_sites[:3]):
        site_id = str(uuid.uuid4())
        stages = json.loads(site_type.potential_stages) if site_type.potential_stages else ["undiscovered"]
        # Vary the stages - first one undiscovered, others at different stages
        stage = "undiscovered" if i == 0 else (stages[1] if len(stages) > 1 else stages[0])
        
        site = {
            "site_id": site_id,
            "settlement_id": settlement_id,
            "site_type_id": site_type.site_type_id,
            "current_stage": stage,
            "depletion_level": 0.0,
            "development_level": 0.2 if stage != "undiscovered" else 0.0,
            "production_multiplier": 1.0,
            "discovery_date": None if stage == "undiscovered" else timestamp,
            "last_updated": timestamp,
            "associated_building_id": None  # No building initially
        }
        sample_sites.append(site)
    
    try:
        for site in sample_sites:
            # Add the site
            db.add(ResourceSites(**site))
            site_type = next((st for st in site_types if st.site_type_id == site["site_type_id"]), None)
            print(f"Added {site_type.site_name} in stage '{site['current_stage']}' to settlement {settlement.settlement_name}")
        
        db.commit()
        print(f"Added {len(sample_sites)} resource sites to settlement {settlement.settlement_name}")
    except Exception as e:
        db.rollback()
        print(f"Error adding resource sites: {str(e)}")
    finally:
        db.close()

def main():
    # Create the resource site types first
    create_resource_site_types()
    
    # Get a settlement ID to add resources to
    db = SessionLocal()
    settlements = db.query(Settlements).all()
    db.close()
    
    if not settlements:
        print("No settlements found in the database")
        return
    
    # Add resource sites to each settlement
    for settlement in settlements:
        add_resource_sites_to_settlement(settlement.settlement_id)

if __name__ == "__main__":
    main()