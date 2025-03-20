#!/usr/bin/env python
import json
import uuid
from datetime import datetime
import random

from database.connection import SessionLocal
from models.core import Settlements, ResourceSites, ResourceSiteTypes, Worlds

# Default fantasy theme ID
FANTASY_THEME_ID = "f47ac10b-58cc-4372-a567-0e02b2c3d479"

def get_uuid_from_string(text):
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, text))

def add_resource_sites():
    """Add resource sites to existing settlements based on their biome types"""
    db = SessionLocal()
    try:
        # Get all settlements
        settlements = db.query(Settlements).all()
        if not settlements:
            print("No settlements found in database")
            return
        
        # Get all resource site types for the fantasy theme
        site_types = db.query(ResourceSiteTypes).filter(
            ResourceSiteTypes.theme_id == FANTASY_THEME_ID
        ).all()
        if not site_types:
            print("No resource site types found for the fantasy theme. Run seed_resource_sites.py first.")
            return
        
        # Map site types by compatible area type
        area_to_sites = {}
        for site_type in site_types:
            if not site_type.compatible_area_types:
                continue
                
            try:
                compatible_areas = json.loads(site_type.compatible_area_types)
                for area in compatible_areas:
                    if area not in area_to_sites:
                        area_to_sites[area] = []
                    area_to_sites[area].append(site_type)
            except (json.JSONDecodeError, TypeError):
                print(f"Error parsing compatible areas for {site_type.site_name}")
        
        # Process each settlement
        for settlement in settlements:
            print(f"\nProcessing settlement: {settlement.settlement_name} (area type: {settlement.area_type})")
            
            # Check if settlement already has resource sites
            existing_sites = db.query(ResourceSites).filter(
                ResourceSites.settlement_id == str(settlement.settlement_id)
            ).all()
            
            if existing_sites:
                print(f"Settlement already has {len(existing_sites)} resource sites")
                continue
            
            # Get compatible site types for this settlement's area type
            compatible_sites = area_to_sites.get(settlement.area_type, [])
            if not compatible_sites:
                print(f"No compatible resource site types found for area type: {settlement.area_type}")
                continue
            
            # Add 3-4 resource sites per settlement with varying stages and quality
            num_sites = random.randint(3, 4)
            for i in range(num_sites):
                # Pick a random compatible site type
                site_type = random.choice(compatible_sites)
                
                # Decide if it's undiscovered, discovered, or developed
                # Higher chance of being discovered or developed for gameplay interest
                stage_odds = random.random()
                if stage_odds < 0.25:
                    stage = "undiscovered"
                    discovery_date = None
                elif stage_odds < 0.75:
                    stage = "discovered"
                    discovery_date = datetime.now()
                else:
                    # For developed sites, use the first developed stage from potential_stages
                    potential_stages = json.loads(site_type.potential_stages) if site_type.potential_stages else []
                    developed_stages = [s for s in potential_stages if s not in ["undiscovered", "discovered", "depleted"]]
                    if developed_stages:
                        stage = developed_stages[0]  # Pick the first developed stage
                    else:
                        stage = "discovered"
                    discovery_date = datetime.now()
                
                # Random quality multiplier (0.8 to 1.2)
                quality = round(random.uniform(0.8, 1.2), 2)
                
                # Create the site
                new_site = ResourceSites(
                    site_id=str(uuid.uuid4()),
                    settlement_id=str(settlement.settlement_id),
                    site_type_id=str(site_type.site_type_id),
                    current_stage=stage,
                    depletion_level=0.0,
                    development_level=0.3 if stage not in ["undiscovered", "discovered"] else 0.0,
                    production_multiplier=quality,
                    discovery_date=discovery_date,
                    last_updated=datetime.now(),
                    associated_building_id=None
                )
                
                db.add(new_site)
                print(f"Added {site_type.site_name} ({stage}) with quality {quality} to {settlement.settlement_name}")
            
        db.commit()
        print("\nResource sites added successfully to settlements")
    except Exception as e:
        db.rollback()
        print(f"Error adding resource sites: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    add_resource_sites()