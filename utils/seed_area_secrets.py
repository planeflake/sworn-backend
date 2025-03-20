#!/usr/bin/env python
import json
import uuid
import random
from datetime import datetime

from database.connection import SessionLocal
from models.core import Areas, AreaSecrets

# Default fantasy theme ID
FANTASY_THEME_ID = "f47ac10b-58cc-4372-a567-0e02b2c3d479"

def seed_area_secrets():
    """Add secrets to existing areas"""
    db = SessionLocal()
    
    try:
        # Get all areas
        areas = db.query(Areas).all()
        if not areas:
            print("No areas found in database")
            return
            
        # Check if we already have secrets in the database
        existing_secrets = db.query(AreaSecrets).count()
        if existing_secrets > 0:
            print(f"Found {existing_secrets} existing area secrets")
            
        # Define secret types based on area types
        area_secrets = {
            "forest": [
                {
                    "name": "Ancient Ruins",
                    "type": "history",
                    "description": "Hidden among the trees, you discover the remnants of an ancient civilization.",
                    "difficulty": 6,
                    "rewards": json.dumps({"experience": 100, "item": "ancient_artifact"}),
                    "hints": json.dumps(["Locals speak of strange stones in the deep woods.", 
                                       "Birds seem to avoid a particular part of the forest."])
                },
                {
                    "name": "Hermit's Hut",
                    "type": "npc",
                    "description": "A small, well-hidden hut where a forest hermit lives with valuable knowledge.",
                    "difficulty": 5,
                    "rewards": json.dumps({"map": "treasure_map", "knowledge": "herbal_recipes"}),
                    "hints": json.dumps(["Smoke sometimes rises from deep in the forest.", 
                                       "Animal trails seem to converge at one point."])
                },
                {
                    "name": "Fairy Ring",
                    "type": "magical",
                    "description": "A perfect circle of mushrooms with strange magical properties.",
                    "difficulty": 7,
                    "rewards": json.dumps({"temporary_buff": "forest_affinity", "knowledge": "fae_secrets"}),
                    "hints": json.dumps(["Strange lights have been seen in the forest at night.", 
                                       "Plants grow unusually vibrant in one circular area."])
                }
            ],
            "mountains": [
                {
                    "name": "Hidden Mine",
                    "type": "resource",
                    "description": "A forgotten mine entrance leading to valuable mineral deposits.",
                    "difficulty": 7,
                    "rewards": json.dumps({"resource": "rare_gems", "map": "deep_mine_map"}),
                    "hints": json.dumps(["Old mining tools have been found scattered in the area.", 
                                       "The rocks in one area have unusual colorful streaks."])
                },
                {
                    "name": "Dragon's Lair",
                    "type": "danger",
                    "description": "A cave where a dragon or similar fearsome creature once lived.",
                    "difficulty": 9,
                    "rewards": json.dumps({"treasure": "dragon_hoard", "weapon": "ancient_blade"}),
                    "hints": json.dumps(["Scorch marks can be seen on certain rock faces.", 
                                       "No animals make their home in one particularly large cave."])
                },
                {
                    "name": "Mountain Shrine",
                    "type": "spiritual",
                    "description": "A small shrine built by mountain folk to honor local spirits.",
                    "difficulty": 4,
                    "rewards": json.dumps({"blessing": "mountain_ward", "knowledge": "local_spirits"}),
                    "hints": json.dumps(["Carved symbols appear on rocks along certain paths.", 
                                       "Locals leave small offerings in particular spots."])
                }
            ],
            "plains": [
                {
                    "name": "Ancient Battlefield",
                    "type": "history",
                    "description": "The site of a major battle, now overgrown but still holding relics.",
                    "difficulty": 5,
                    "rewards": json.dumps({"item": "commander_insignia", "knowledge": "battle_tactics"}),
                    "hints": json.dumps(["Metal fragments occasionally surface after heavy rains.", 
                                       "The grass grows differently in a large rectangular pattern."])
                },
                {
                    "name": "Hidden Spring",
                    "type": "resource",
                    "description": "A pure spring with healing properties, hidden in the plains.",
                    "difficulty": 6,
                    "rewards": json.dumps({"item": "healing_water", "knowledge": "water_sources"}),
                    "hints": json.dumps(["Animals seem to gather in one area, even in dry seasons.", 
                                       "Particularly vibrant flowers grow in one small patch."])
                },
                {
                    "name": "Nomad Cache",
                    "type": "treasure",
                    "description": "A hidden storage location used by nomadic traders.",
                    "difficulty": 7,
                    "rewards": json.dumps({"gold": 100, "trade_goods": "exotic_spices"}),
                    "hints": json.dumps(["Unusual stones arranged in a specific pattern.", 
                                       "Abandoned camp equipment half-buried in the ground."])
                }
            ],
            "coastal": [
                {
                    "name": "Smuggler's Cove",
                    "type": "treasure",
                    "description": "A hidden cove once used by smugglers to store contraband.",
                    "difficulty": 6,
                    "rewards": json.dumps({"gold": 150, "item": "captain_compass"}),
                    "hints": json.dumps(["Unusual rope markings on coastal rocks.", 
                                       "Local fishermen avoid a certain cove."])
                },
                {
                    "name": "Shipwreck",
                    "type": "history",
                    "description": "The remains of a merchant vessel that sank near the shore.",
                    "difficulty": 5,
                    "rewards": json.dumps({"item": "waterlogged_map", "salvage": "ship_materials"}),
                    "hints": json.dumps(["Pieces of timber wash ashore after storms.", 
                                       "Unusual currents in one part of the coastline."])
                },
                {
                    "name": "Sea Cave",
                    "type": "magical",
                    "description": "A cave with unusual acoustics and potential magical properties.",
                    "difficulty": 8,
                    "rewards": json.dumps({"item": "echo_stone", "knowledge": "sound_magic"}),
                    "hints": json.dumps(["Strange echoes can be heard at certain times.", 
                                       "The water in one area glows faintly at night."])
                }
            ],
            "swamp": [
                {
                    "name": "Witch's Hut",
                    "type": "npc",
                    "description": "The abandoned dwelling of a witch or alchemist.",
                    "difficulty": 8,
                    "rewards": json.dumps({"item": "potion_recipes", "ingredient": "rare_mushrooms"}),
                    "hints": json.dumps(["Strange lights sometimes flicker in the deepest part of the swamp.", 
                                       "Plants grow in unnatural arrangements in one area."])
                },
                {
                    "name": "Sunken Temple",
                    "type": "history",
                    "description": "A partially submerged temple to an old, forgotten deity.",
                    "difficulty": 9,
                    "rewards": json.dumps({"artifact": "ceremonial_mask", "knowledge": "forgotten_rituals"}),
                    "hints": json.dumps(["Stone blocks can be seen just below the water's surface.", 
                                       "Locals tell tales of voices heard in the mist."])
                }
            ],
            "hills": [
                {
                    "name": "Bandit Hideout",
                    "type": "danger",
                    "description": "An abandoned hideout once used by bandits to store loot.",
                    "difficulty": 4,
                    "rewards": json.dumps({"gold": 75, "item": "bandit_map"}),
                    "hints": json.dumps(["Suspicious markers on trees point in a direction.", 
                                       "A narrow path seems deliberately obscured."])
                },
                {
                    "name": "Forgotten Tomb",
                    "type": "history",
                    "description": "The burial place of a local hero or noble.",
                    "difficulty": 7,
                    "rewards": json.dumps({"artifact": "noble_signet", "knowledge": "local_lineage"}),
                    "hints": json.dumps(["Unusual stones arranged in a pattern on a hillside.", 
                                       "Local folklore mentions a hero buried 'where the sun first touches the hills.'"])
                }
            ]
        }
        
        # Define generic secrets that can appear in any area type
        generic_secrets = [
            {
                "name": "Traveler's Cache",
                "type": "treasure",
                "description": "A small box hidden by a previous traveler, containing useful supplies.",
                "difficulty": 3,
                "rewards": json.dumps({"gold": 20, "supplies": "travel_rations"}),
                "hints": json.dumps(["A carved mark on a nearby landmark.", 
                                   "Disturbed earth that doesn't match the surroundings."])
            },
            {
                "name": "Mysterious Symbol",
                "type": "quest",
                "description": "A strange symbol carved into stone or wood, with unknown meaning.",
                "difficulty": 4,
                "rewards": json.dumps({"knowledge": "mysterious_order", "quest_start": "symbol_meaning"}),
                "hints": json.dumps(["The symbol seems to have been recently maintained.", 
                                   "Similar markings appear at regular intervals in the region."])
            }
        ]
        
        # Add secrets to areas
        secrets_added = 0
        
        for area in areas:
            # Define how many secrets this area might have (1-3)
            # Make it rarer in safer areas, more common in dangerous ones
            max_secrets = min(3, max(1, area.danger_level // 3))
            num_secrets = random.randint(1, max_secrets)
            
            # Check if this area already has secrets
            existing_area_secrets = db.query(AreaSecrets).filter(
                AreaSecrets.area_id == area.area_id
            ).all()
            
            if existing_area_secrets:
                print(f"Area {area.area_name} already has {len(existing_area_secrets)} secrets")
                continue
                
            # Get potential secrets for this area type
            area_type_secrets = area_secrets.get(area.area_type, [])
            
            # Mix in some generic secrets
            potential_secrets = area_type_secrets + generic_secrets
            
            if not potential_secrets:
                continue
                
            # Add random secrets to this area
            for i in range(num_secrets):
                if not potential_secrets:
                    break
                    
                # Select and remove a random secret
                secret_template = random.choice(potential_secrets)
                potential_secrets.remove(secret_template)
                
                # Create the secret
                secret_id = str(uuid.uuid4())
                new_secret = AreaSecrets(
                    secret_id=secret_id,
                    area_id=area.area_id,
                    theme_id=FANTASY_THEME_ID,
                    secret_name=secret_template["name"],
                    secret_type=secret_template["type"],
                    description=secret_template["description"],
                    is_discovered=False,
                    discovered_by=None,
                    discovered_at=None,
                    difficulty=secret_template["difficulty"],
                    requirements=json.dumps({"perception": secret_template["difficulty"]}),
                    rewards=secret_template["rewards"],
                    related_quest_id=None,
                    related_npc_id=None,
                    hints=secret_template["hints"]
                )
                
                db.add(new_secret)
                secrets_added += 1
                print(f"Added secret '{secret_template['name']}' to {area.area_name}")
        
        db.commit()
        print(f"Added {secrets_added} secrets to areas")
    except Exception as e:
        db.rollback()
        print(f"Error seeding area secrets: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_area_secrets()