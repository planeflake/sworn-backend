#!/usr/bin/env python
import json
import uuid
import random
import math
from datetime import datetime

from database.connection import SessionLocal
from models.core import Settlements, Areas, TravelRoutes

# Default fantasy theme ID
FANTASY_THEME_ID = "f47ac10b-58cc-4372-a567-0e02b2c3d479"

def generate_areas_between_settlements():
    """Generate areas between existing settlements and create travel routes"""
    db = SessionLocal()
    
    try:
        # Get all settlements
        settlements = db.query(Settlements).all()
        if len(settlements) < 2:
            print("Need at least 2 settlements to generate areas between them")
            return
            
        # Check if there are already areas and routes defined
        existing_areas = db.query(Areas).all()
        existing_routes = db.query(TravelRoutes).all()
        
        if existing_areas:
            print(f"Found {len(existing_areas)} existing areas")
        
        if existing_routes:
            print(f"Found {len(existing_routes)} existing routes")
            
        # Get all possible settlement pairs
        settlement_pairs = []
        for i, start in enumerate(settlements):
            for end in settlements[i+1:]:
                # Check if these settlements are in the same world
                if start.world_id != end.world_id:
                    continue
                    
                # Create a pair
                settlement_pairs.append((start, end))
        
        print(f"Found {len(settlement_pairs)} potential routes between settlements")
        
        # Process each pair to create areas and routes
        for start, end in settlement_pairs:
            # Skip if a route already exists between these settlements
            existing_route = db.query(TravelRoutes).filter(
                ((TravelRoutes.start_settlement_id == str(start.settlement_id)) & 
                 (TravelRoutes.end_settlement_id == str(end.settlement_id))) |
                ((TravelRoutes.start_settlement_id == str(end.settlement_id)) & 
                 (TravelRoutes.end_settlement_id == str(start.settlement_id)))
            ).first()
            
            if existing_route:
                print(f"Route already exists between {start.settlement_name} and {end.settlement_name}")
                continue
                
            print(f"Generating route between {start.settlement_name} and {end.settlement_name}")
            
            # Calculate distance and number of areas to create
            dist_x = start.location_x - end.location_x
            dist_y = start.location_y - end.location_y
            distance = math.sqrt(dist_x**2 + dist_y**2)
            
            # Determine number of areas based on distance
            # For example, one area per 20 distance units
            num_areas = max(1, min(5, int(distance / 20)))
            
            # Determine area types based on start and end settlement area types
            start_area_type = start.area_type
            end_area_type = end.area_type
            
            # Create a progression of area types from start to end
            area_types = []
            if start_area_type == end_area_type:
                # If same type, all areas are that type
                area_types = [start_area_type] * num_areas
            else:
                # Create a gradient of area types
                area_types = [start_area_type]
                
                # If we have more than 2 areas, add transitional areas
                if num_areas > 2:
                    # Determine transitional biomes
                    transitional_biomes = get_transitional_biomes(start_area_type, end_area_type)
                    
                    # Add transitional areas
                    for i in range(num_areas - 2):
                        if transitional_biomes and i < len(transitional_biomes):
                            area_types.append(transitional_biomes[i])
                        else:
                            # If no specific transition, alternate between start and end
                            area_types.append(start_area_type if i % 2 == 0 else end_area_type)
                
                # Add the destination area type
                area_types.append(end_area_type)
            
            # Generate areas along the path
            area_ids = []
            for i in range(num_areas):
                # Calculate position along the path
                progress = (i + 1) / (num_areas + 1)  # Position between 0 and 1
                x = start.location_x + dist_x * progress
                y = start.location_y + dist_y * progress
                
                # Add some randomness to position to avoid straight lines
                x += random.uniform(-5, 5)
                y += random.uniform(-5, 5)
                
                # Determine area type
                area_type = area_types[i]
                
                # Set danger level (higher in the middle of the journey)
                danger_level = random.randint(1, 8)
                if i == 0 or i == num_areas - 1:
                    # Lower danger near settlements
                    danger_level = max(1, danger_level - 3)
                
                # Generate a good area name
                area_name = generate_area_name(area_type)
                
                # Create area
                area_id = str(uuid.uuid4())
                area = Areas(
                    area_id=area_id,
                    world_id=start.world_id,
                    theme_id=FANTASY_THEME_ID,
                    area_name=area_name,
                    area_type=area_type,
                    location_x=x,
                    location_y=y,
                    radius=15.0,  # Default radius
                    danger_level=danger_level,
                    resource_richness=random.uniform(0.3, 0.8),
                    created_at=datetime.now(),
                    last_updated=datetime.now(),
                    description=generate_area_description(area_type, danger_level),
                    connected_settlements=json.dumps([str(start.settlement_id), str(end.settlement_id)]),
                    connected_areas=json.dumps([])  # Will update after creating all areas
                )
                
                db.add(area)
                db.flush()  # Ensure the area is in the database before proceeding
                area_ids.append(area_id)
                print(f"Created area: {area_name} ({area_type})")
            
            # Create travel route
            route_id = str(uuid.uuid4())
            # Get danger level from areas if they exist, otherwise use a default
            area_danger_levels = [area.danger_level for area in db.query(Areas).filter(Areas.area_id.in_(area_ids)).all()]
            max_danger = max(area_danger_levels) if area_danger_levels else 5  # Default danger level if no areas
            
            route = TravelRoutes(
                route_id=route_id,
                world_id=start.world_id,
                start_settlement_id=str(start.settlement_id),
                end_settlement_id=str(end.settlement_id),
                path=json.dumps(area_ids),
                total_distance=distance,
                danger_level=max_danger,
                path_condition=random.choice(["good", "moderate", "poor", "difficult"]),
                travel_time=int(distance * (0.5 + random.random())),  # Semi-random travel time
                created_at=datetime.now(),
                last_updated=datetime.now()
            )
            
            db.add(route)
            print(f"Created route from {start.settlement_name} to {end.settlement_name}")
            
            # Now update connected_areas for each area
            if len(area_ids) > 1:
                for i, area_id in enumerate(area_ids):
                    area = db.query(Areas).filter(Areas.area_id == area_id).first()
                    
                    if not area:
                        print(f"Warning: Could not find area with ID {area_id}")
                        continue
                        
                    connected = []
                    
                    # Connect to previous area if it exists
                    if i > 0:
                        connected.append(area_ids[i-1])
                        
                    # Connect to next area if it exists
                    if i < len(area_ids) - 1:
                        connected.append(area_ids[i+1])
                        
                    area.connected_areas = json.dumps(connected)
        
        db.commit()
        print("Areas and routes generated successfully")
    except Exception as e:
        db.rollback()
        print(f"Error generating areas: {str(e)}")
    finally:
        db.close()

def get_transitional_biomes(start_biome, end_biome):
    """Determine appropriate transitional biomes between two biomes"""
    transitions = {
        # From forest to X
        ("forest", "mountains"): ["hills"],
        ("forest", "plains"): ["hills", "plains"],
        ("forest", "desert"): ["hills", "plains"],
        ("forest", "swamp"): ["wetlands"],
        ("forest", "coastal"): ["hills", "coastal"],
        
        # From mountains to X
        ("mountains", "forest"): ["hills", "forest"],
        ("mountains", "plains"): ["hills", "plains"],
        ("mountains", "desert"): ["hills", "desert"],
        ("mountains", "swamp"): ["hills", "wetlands"],
        ("mountains", "coastal"): ["hills", "coastal"],
        
        # From plains to X
        ("plains", "forest"): ["hills", "forest"],
        ("plains", "mountains"): ["hills", "mountains"],
        ("plains", "desert"): ["badlands"],
        ("plains", "swamp"): ["wetlands"],
        ("plains", "coastal"): ["coastal"],
        
        # From desert to X
        ("desert", "forest"): ["plains", "forest"],
        ("desert", "mountains"): ["badlands", "mountains"],
        ("desert", "plains"): ["badlands"],
        ("desert", "swamp"): ["plains", "wetlands"],
        ("desert", "coastal"): ["coastal"],
        
        # From swamp to X
        ("swamp", "forest"): ["wetlands", "forest"],
        ("swamp", "mountains"): ["wetlands", "hills"],
        ("swamp", "plains"): ["wetlands"],
        ("swamp", "desert"): ["wetlands", "plains"],
        ("swamp", "coastal"): ["wetlands", "coastal"],
        
        # From coastal to X
        ("coastal", "forest"): ["coastal", "forest"],
        ("coastal", "mountains"): ["coastal", "hills"],
        ("coastal", "plains"): ["coastal", "plains"],
        ("coastal", "desert"): ["coastal", "badlands"],
        ("coastal", "swamp"): ["coastal", "wetlands"]
    }
    
    # Check if we have a defined transition
    key = (start_biome, end_biome)
    if key in transitions:
        return transitions[key]
    
    # Check reverse order
    key = (end_biome, start_biome)
    if key in transitions:
        # Return in reverse order
        return list(reversed(transitions[key]))
    
    # Default to midpoint transition
    return ["hills"]  # Generic transition

def generate_area_name(area_type):
    """Generate a descriptive name for an area based on its type"""
    prefixes = {
        "forest": ["Whispering", "Ancient", "Verdant", "Misty", "Shadow", "Emerald", "Tangled", "Twilight"],
        "mountains": ["Rugged", "Towering", "Jagged", "Frost", "Thunder", "Iron", "Stone", "Cloud"],
        "plains": ["Golden", "Windswept", "Rolling", "Amber", "Vast", "Serene", "Sun-kissed", "Wild"],
        "hills": ["Green", "Rolling", "Gentle", "Quiet", "Lonely", "Windy", "Grassy", "Barren"],
        "desert": ["Scorching", "Endless", "Howling", "Crimson", "Bone-dry", "Shifting", "Golden", "Desolate"],
        "swamp": ["Murky", "Withered", "Fog", "Drowned", "Rotting", "Haunted", "Twilight", "Ancient"],
        "coastal": ["Stormy", "Windy", "Salt", "Tide", "Azure", "Foggy", "Rocky", "Wave-beaten"],
        "wetlands": ["Misty", "Reed", "Foggy", "Drowning", "Hollow", "Sunken", "Silent", "Whispering"],
        "badlands": ["Broken", "Scarred", "Red", "Cracked", "Desolate", "Wind-carved", "Sun-scorched", "Barren"]
    }
    
    suffixes = {
        "forest": ["Woods", "Forest", "Grove", "Thicket", "Woodland", "Wilds", "Timberland", "Copse"],
        "mountains": ["Peaks", "Mountains", "Range", "Spires", "Heights", "Crags", "Ridges", "Summit"],
        "plains": ["Plains", "Grasslands", "Fields", "Expanse", "Steppe", "Meadows", "Prairie", "Flatlands"],
        "hills": ["Hills", "Highlands", "Knolls", "Downs", "Rise", "Slopes", "Hillocks", "Ridge"],
        "desert": ["Wastes", "Sands", "Desert", "Dunes", "Barrens", "Badlands", "Flats", "Waste"],
        "swamp": ["Swamp", "Marsh", "Wetlands", "Bog", "Morass", "Quagmire", "Fen", "Mire"],
        "coastal": ["Coast", "Shores", "Beach", "Strand", "Cliffs", "Seaside", "Bay", "Cove"],
        "wetlands": ["Marsh", "Wetlands", "Bog", "Fen", "Mire", "Swamps", "Bayou", "Morass"],
        "badlands": ["Badlands", "Wastes", "Scars", "Ruins", "Gulch", "Ravines", "Flats", "Breaks"]
    }
    
    # Get appropriate lists for this area type
    area_prefixes = prefixes.get(area_type, ["Mysterious", "Unknown", "Strange", "Wild"])
    area_suffixes = suffixes.get(area_type, ["Lands", "Wilderness", "Territory", "Region"])
    
    # Generate name
    prefix = random.choice(area_prefixes)
    suffix = random.choice(area_suffixes)
    
    return f"{prefix} {suffix}"

def generate_area_description(area_type, danger_level):
    """Generate a description for an area based on its type and danger level"""
    descriptions = {
        "forest": [
            "A dense forest with towering trees and thick undergrowth.",
            "Sunlight filters through the canopy of this ancient forest.",
            "The forest is alive with the sounds of birds and small animals.",
            "A quiet, mysterious woodland shrouded in mist and shadows."
        ],
        "mountains": [
            "Jagged mountain peaks rise high into the clouds.",
            "Steep, rocky slopes make this mountain range treacherous to traverse.",
            "The mountain air is thin but crisp and invigorating.",
            "Stone and snow dominate this imposing mountain range."
        ],
        "plains": [
            "Rolling grasslands stretch as far as the eye can see.",
            "The plains are covered with tall grasses that sway in the wind.",
            "This open plain offers little shelter from the elements.",
            "A vast expanse of fertile grassland dotted with wildflowers."
        ],
        "hills": [
            "Gentle, rolling hills covered in grass and small shrubs.",
            "The hilly terrain provides good visibility of the surrounding area.",
            "These quiet hills are punctuated by the occasional stand of trees.",
            "The undulating landscape of these hills makes for pleasant travel."
        ],
        "desert": [
            "A harsh, arid desert with shifting sand dunes.",
            "Heat shimmers off the parched ground of this barren desert.",
            "This desert is a seemingly endless expanse of sand and stone.",
            "The desert is brutally hot by day and freezing cold by night."
        ],
        "swamp": [
            "A boggy swamp filled with murky water and twisted trees.",
            "The air in this swamp is thick with humidity and the smell of decay.",
            "Moss-covered trees rise from the dark waters of this swamp.",
            "This fetid swamp is alive with the sounds of insects and amphibians."
        ],
        "coastal": [
            "Rocky cliffs overlook the crashing waves of the coastline.",
            "The coastal air is filled with the scent of salt and seaweed.",
            "Sandy beaches and tide pools mark this beautiful coastal area.",
            "The constant rhythm of waves shapes this ever-changing coastline."
        ],
        "wetlands": [
            "A marshy area where water and land intermingle.",
            "Reeds and cattails grow thick in these shallow waters.",
            "The wetlands teem with diverse wildlife and plant species.",
            "Pools of stagnant water dot this soggy, challenging terrain."
        ],
        "badlands": [
            "Eroded rock formations create a bizarre, alien landscape.",
            "The soil is poor and vegetation is sparse in these harsh badlands.",
            "Deep gullies and dry washes cut through the barren terrain.",
            "The badlands are a maze of canyons and weather-worn rock pillars."
        ]
    }
    
    # Danger level descriptions to append
    danger_desc = [
        "The area seems peaceful and relatively safe.",
        "There are signs of wildlife, but nothing particularly threatening.",
        "Occasional tracks suggest predators may be active in the area.",
        "Several signs warn of potential dangers ahead.",
        "This region has a reputation for being somewhat dangerous.",
        "Locals advise caution when traveling through this hazardous area.",
        "The area is known to be dangerous, with frequent reports of attacks.",
        "This is treacherous territory, avoided by all but the most desperate or well-armed."
    ]
    
    # Get appropriate description for this area type
    area_descriptions = descriptions.get(area_type, ["A wild and untamed region of mysterious origins."])
    
    # Get danger description (0-indexed array, danger_level is 1-8)
    danger_description = danger_desc[min(danger_level - 1, len(danger_desc) - 1)]
    
    # Generate full description
    base_desc = random.choice(area_descriptions)
    
    return f"{base_desc} {danger_description}"

if __name__ == "__main__":
    generate_areas_between_settlements()