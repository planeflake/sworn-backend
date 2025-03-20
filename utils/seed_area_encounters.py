#!/usr/bin/env python
import json
import uuid
from datetime import datetime

from database.connection import SessionLocal
from models.core import AreaEncounterTypes, AreaEncounterOutcomes

# Default fantasy theme ID
FANTASY_THEME_ID = "f47ac10b-58cc-4372-a567-0e02b2c3d479"

# Function to create a UUID from a string for consistency
def get_uuid_from_string(text):
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, text))

def seed_area_encounter_types():
    """Seed area encounter types for the fantasy theme"""
    db = SessionLocal()
    
    # Define encounter types for the fantasy theme
    encounter_types = [
        # Combat encounters
        {
            "encounter_type_id": get_uuid_from_string("bandit_ambush"),
            "theme_id": FANTASY_THEME_ID,
            "encounter_code": "bandit_ambush",
            "encounter_name": "Bandit Ambush",
            "encounter_category": "combat",
            "min_danger_level": 3,
            "compatible_area_types": json.dumps(["forest", "hills", "mountains", "plains"]),
            "rarity": 0.7,
            "description": "A group of bandits hiding in wait to ambush travelers.",
            "possible_outcomes": json.dumps([
                "bandit_ambush_defeat", 
                "bandit_ambush_flee", 
                "bandit_ambush_negotiate"
            ])
        },
        {
            "encounter_type_id": get_uuid_from_string("wolf_pack"),
            "theme_id": FANTASY_THEME_ID,
            "encounter_code": "wolf_pack",
            "encounter_name": "Wolf Pack",
            "encounter_category": "combat",
            "min_danger_level": 2,
            "compatible_area_types": json.dumps(["forest", "hills", "mountains"]),
            "rarity": 0.6,
            "description": "A hungry pack of wolves stalking travelers.",
            "possible_outcomes": json.dumps([
                "wolf_pack_defeat", 
                "wolf_pack_flee", 
                "wolf_pack_scare"
            ])
        },
        {
            "encounter_type_id": get_uuid_from_string("bear_attack"),
            "theme_id": FANTASY_THEME_ID,
            "encounter_code": "bear_attack",
            "encounter_name": "Bear Attack",
            "encounter_category": "combat",
            "min_danger_level": 4,
            "compatible_area_types": json.dumps(["forest", "mountains"]),
            "rarity": 0.4,
            "description": "A territorial bear defending its territory.",
            "possible_outcomes": json.dumps([
                "bear_attack_defeat", 
                "bear_attack_flee", 
                "bear_attack_hide"
            ])
        },
        
        # Reward encounters
        {
            "encounter_type_id": get_uuid_from_string("abandoned_cart"),
            "theme_id": FANTASY_THEME_ID,
            "encounter_code": "abandoned_cart",
            "encounter_name": "Abandoned Cart",
            "encounter_category": "reward",
            "min_danger_level": 1,
            "compatible_area_types": json.dumps(["forest", "plains", "hills", "mountains", "swamp"]),
            "rarity": 0.5,
            "description": "An abandoned merchant cart with possible supplies.",
            "possible_outcomes": json.dumps([
                "abandoned_cart_supplies", 
                "abandoned_cart_trap", 
                "abandoned_cart_empty"
            ])
        },
        {
            "encounter_type_id": get_uuid_from_string("hidden_cache"),
            "theme_id": FANTASY_THEME_ID,
            "encounter_code": "hidden_cache",
            "encounter_name": "Hidden Cache",
            "encounter_category": "reward",
            "min_danger_level": 1,
            "compatible_area_types": json.dumps(["forest", "mountains", "hills", "ruins"]),
            "rarity": 0.3,
            "description": "A hidden stash of valuable goods.",
            "possible_outcomes": json.dumps([
                "hidden_cache_treasure", 
                "hidden_cache_supplies", 
                "hidden_cache_empty"
            ])
        },
        
        # Helper encounters
        {
            "encounter_type_id": get_uuid_from_string("injured_traveler"),
            "theme_id": FANTASY_THEME_ID,
            "encounter_code": "injured_traveler",
            "encounter_name": "Injured Traveler",
            "encounter_category": "helper",
            "min_danger_level": 1,
            "compatible_area_types": json.dumps(["forest", "plains", "hills", "mountains", "swamp", "coastal"]),
            "rarity": 0.5,
            "description": "A traveler in need of aid after being injured.",
            "possible_outcomes": json.dumps([
                "injured_traveler_help", 
                "injured_traveler_ignore"
            ])
        },
        {
            "encounter_type_id": get_uuid_from_string("lost_merchant"),
            "theme_id": FANTASY_THEME_ID,
            "encounter_code": "lost_merchant",
            "encounter_name": "Lost Merchant",
            "encounter_category": "helper",
            "min_danger_level": 1,
            "compatible_area_types": json.dumps(["forest", "hills", "mountains", "swamp"]),
            "rarity": 0.4,
            "description": "A merchant who has lost their way.",
            "possible_outcomes": json.dumps([
                "lost_merchant_guide", 
                "lost_merchant_directions", 
                "lost_merchant_ignore"
            ])
        },
        
        # Environmental encounters
        {
            "encounter_type_id": get_uuid_from_string("sudden_storm"),
            "theme_id": FANTASY_THEME_ID,
            "encounter_code": "sudden_storm",
            "encounter_name": "Sudden Storm",
            "encounter_category": "environmental",
            "min_danger_level": 2,
            "compatible_area_types": json.dumps(["forest", "plains", "hills", "mountains", "coastal"]),
            "rarity": 0.5,
            "description": "A powerful storm suddenly rolls in, threatening travelers.",
            "possible_outcomes": json.dumps([
                "sudden_storm_shelter", 
                "sudden_storm_continue", 
                "sudden_storm_lost"
            ])
        },
        {
            "encounter_type_id": get_uuid_from_string("rockslide"),
            "theme_id": FANTASY_THEME_ID,
            "encounter_code": "rockslide",
            "encounter_name": "Rockslide",
            "encounter_category": "environmental",
            "min_danger_level": 3,
            "compatible_area_types": json.dumps(["mountains", "hills"]),
            "rarity": 0.4,
            "description": "Loose rocks come tumbling down the mountainside.",
            "possible_outcomes": json.dumps([
                "rockslide_dodge", 
                "rockslide_injured", 
                "rockslide_blocked_path"
            ])
        },
        
        # Neutral encounters
        {
            "encounter_type_id": get_uuid_from_string("traveling_merchant"),
            "theme_id": FANTASY_THEME_ID,
            "encounter_code": "traveling_merchant",
            "encounter_name": "Traveling Merchant",
            "encounter_category": "neutral",
            "min_danger_level": 1,
            "compatible_area_types": json.dumps(["forest", "plains", "hills", "coastal"]),
            "rarity": 0.6,
            "description": "A merchant traveling between settlements with goods to trade.",
            "possible_outcomes": json.dumps([
                "traveling_merchant_trade", 
                "traveling_merchant_info", 
                "traveling_merchant_ignore"
            ])
        },
        {
            "encounter_type_id": get_uuid_from_string("fellow_travelers"),
            "theme_id": FANTASY_THEME_ID,
            "encounter_code": "fellow_travelers",
            "encounter_name": "Fellow Travelers",
            "encounter_category": "neutral",
            "min_danger_level": 1,
            "compatible_area_types": json.dumps(["forest", "plains", "hills", "mountains", "coastal"]),
            "rarity": 0.7,
            "description": "A group of travelers heading in the same direction.",
            "possible_outcomes": json.dumps([
                "fellow_travelers_join", 
                "fellow_travelers_share", 
                "fellow_travelers_pass"
            ])
        },
        
        # Nothing happens (for lower encounter rate)
        {
            "encounter_type_id": get_uuid_from_string("uneventful_travel"),
            "theme_id": FANTASY_THEME_ID,
            "encounter_code": "uneventful_travel",
            "encounter_name": "Uneventful Travel",
            "encounter_category": "neutral",
            "min_danger_level": 0,
            "compatible_area_types": json.dumps(["forest", "plains", "hills", "mountains", "coastal", "swamp", "desert", "ruins"]),
            "rarity": 1.0,  # Always available
            "description": "The journey continues without any notable events.",
            "possible_outcomes": json.dumps(["uneventful_travel_continue"])
        }
    ]

    # Define outcomes for these encounters
    outcomes = [
        # Bandit ambush outcomes
        {
            "outcome_id": get_uuid_from_string("bandit_ambush_defeat"),
            "encounter_type_id": get_uuid_from_string("bandit_ambush"),
            "outcome_code": "defeat",
            "outcome_name": "Defeat Bandits",
            "outcome_type": "success",
            "requirements": json.dumps({"combat_skill": 3, "strength": 2}),
            "rewards": json.dumps({"gold": 20, "experience": 50, "items": ["bandit_weapon"]}),
            "penalties": json.dumps({"health": -10}),
            "probability": 0.4,
            "narrative": "You successfully fight off the bandits, taking minor injuries but claiming their loot."
        },
        {
            "outcome_id": get_uuid_from_string("bandit_ambush_flee"),
            "encounter_type_id": get_uuid_from_string("bandit_ambush"),
            "outcome_code": "flee",
            "outcome_name": "Flee from Bandits",
            "outcome_type": "neutral",
            "requirements": json.dumps({"speed": 3, "agility": 2}),
            "rewards": json.dumps({}),
            "penalties": json.dumps({"time": 1, "stamina": -20}),
            "probability": 0.4,
            "narrative": "You manage to escape the bandits, but lose time and energy in the process."
        },
        {
            "outcome_id": get_uuid_from_string("bandit_ambush_negotiate"),
            "encounter_type_id": get_uuid_from_string("bandit_ambush"),
            "outcome_code": "negotiate",
            "outcome_name": "Negotiate with Bandits",
            "outcome_type": "neutral",
            "requirements": json.dumps({"charisma": 4, "diplomacy": 3}),
            "rewards": json.dumps({"experience": 30}),
            "penalties": json.dumps({"gold": -10}),
            "probability": 0.2,
            "narrative": "You talk your way out of trouble, paying a small 'toll' to pass safely."
        },
        
        # Abandoned cart outcomes
        {
            "outcome_id": get_uuid_from_string("abandoned_cart_supplies"),
            "encounter_type_id": get_uuid_from_string("abandoned_cart"),
            "outcome_code": "supplies",
            "outcome_name": "Find Supplies",
            "outcome_type": "success",
            "requirements": json.dumps({}),
            "rewards": json.dumps({"food": 15, "water": 10, "materials": 5}),
            "penalties": json.dumps({}),
            "probability": 0.6,
            "narrative": "You find useful supplies in the abandoned cart."
        },
        {
            "outcome_id": get_uuid_from_string("abandoned_cart_trap"),
            "encounter_type_id": get_uuid_from_string("abandoned_cart"),
            "outcome_code": "trap",
            "outcome_name": "Spring a Trap",
            "outcome_type": "failure",
            "requirements": json.dumps({}),
            "rewards": json.dumps({}),
            "penalties": json.dumps({"health": -15}),
            "probability": 0.2,
            "narrative": "As you approach the cart, you trigger a hidden trap!"
        },
        {
            "outcome_id": get_uuid_from_string("abandoned_cart_empty"),
            "encounter_type_id": get_uuid_from_string("abandoned_cart"),
            "outcome_code": "empty",
            "outcome_name": "Find Empty Cart",
            "outcome_type": "neutral",
            "requirements": json.dumps({}),
            "rewards": json.dumps({}),
            "penalties": json.dumps({}),
            "probability": 0.2,
            "narrative": "The cart has already been looted and is empty."
        },
        
        # Injured traveler outcomes
        {
            "outcome_id": get_uuid_from_string("injured_traveler_help"),
            "encounter_type_id": get_uuid_from_string("injured_traveler"),
            "outcome_code": "help",
            "outcome_name": "Help Injured Traveler",
            "outcome_type": "success",
            "requirements": json.dumps({"medicine": 2}),
            "rewards": json.dumps({"reputation": 10, "experience": 40, "karmic_balance": 1}),
            "penalties": json.dumps({"medicine_supplies": -1}),
            "probability": 0.7,
            "narrative": "You help the injured traveler, earning their gratitude and valuable information about the area."
        },
        {
            "outcome_id": get_uuid_from_string("injured_traveler_ignore"),
            "encounter_type_id": get_uuid_from_string("injured_traveler"),
            "outcome_code": "ignore",
            "outcome_name": "Ignore Injured Traveler",
            "outcome_type": "neutral",
            "requirements": json.dumps({}),
            "rewards": json.dumps({}),
            "penalties": json.dumps({"karmic_balance": -1}),
            "probability": 0.3,
            "narrative": "You pass by without helping, feeling a twinge of guilt."
        },
        
        # Default uneventful travel outcome
        {
            "outcome_id": get_uuid_from_string("uneventful_travel_continue"),
            "encounter_type_id": get_uuid_from_string("uneventful_travel"),
            "outcome_code": "continue",
            "outcome_name": "Continue Journey",
            "outcome_type": "neutral",
            "requirements": json.dumps({}),
            "rewards": json.dumps({}),
            "penalties": json.dumps({}),
            "probability": 1.0,
            "narrative": "You continue your journey without incident."
        }
    ]

    try:
        # Add encounter types
        for encounter_type in encounter_types:
            existing = db.query(AreaEncounterTypes).filter(
                AreaEncounterTypes.encounter_type_id == encounter_type["encounter_type_id"]
            ).first()
            
            if not existing:
                db.add(AreaEncounterTypes(**encounter_type))
                print(f"Added encounter type: {encounter_type['encounter_name']}")
            else:
                # Update existing entry if needed
                print(f"Encounter type already exists: {encounter_type['encounter_name']}")
        
        # Add outcomes
        for outcome in outcomes:
            existing = db.query(AreaEncounterOutcomes).filter(
                AreaEncounterOutcomes.outcome_id == outcome["outcome_id"]
            ).first()
            
            if not existing:
                db.add(AreaEncounterOutcomes(**outcome))
                print(f"Added encounter outcome: {outcome['outcome_name']}")
            else:
                print(f"Encounter outcome already exists: {outcome['outcome_name']}")
        
        db.commit()
        print("Area encounter types and outcomes seeded successfully")
    except Exception as e:
        db.rollback()
        print(f"Error seeding area encounter data: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_area_encounter_types()