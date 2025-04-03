#!/usr/bin/env python
"""
Create ruler NPCs for each settlement.

This script:
1. Creates a new 'ruler' role if it doesn't exist
2. Generates a ruler NPC and character for each settlement that lacks one
3. Assigns each ruler with characteristics like expansion, money, happiness, magic focus
4. Updates the settlement owner_character_id to link to the ruler
"""

import sys
import os
import uuid
import json
import random
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import SessionLocal
from app.models.core import Settlements, Npcs, Characters, Worlds, NpcTypes
from app.models.roles import Role, CharacterRole, Skill, CharacterSkill

# Names for rulers by gender
MALE_NAMES = [
    "Lord Alaric", "Baron Cedric", "Duke Rowan", "Count Thorne", "King Gareth",
    "Governor Dorian", "Chancellor Magnus", "Regent Edmund", "Prince Eamon", "Emperor Lucius"
]

FEMALE_NAMES = [
    "Lady Seraphina", "Baroness Elara", "Duchess Lyra", "Countess Aria", "Queen Isolde",
    "Governor Imogen", "Chancellor Thalia", "Regent Octavia", "Princess Freya", "Empress Cora"
]

# Titles by settlement type and size
TITLES = {
    "village": ["Elder", "Chieftain", "Overseer"],
    "town": ["Mayor", "Governor", "Magistrate"],
    "city": ["Lord Mayor", "High Chancellor", "Sovereign"],
    "fortress": ["Commander", "Warden", "Castellan"],
    "outpost": ["Captain", "Marshal", "Custodian"],
    "hamlet": ["Reeve", "Alderman", "Headman"],
    "capital": ["King", "Queen", "Emperor", "Empress", "High Chancellor", "Grand Duke", "Grand Duchess"],
    "port": ["Harbor Master", "Admiral", "Port Sovereign"],
    "mountains": ["Mountain King", "High Thane", "Summit Lord"],
    "plains": ["Plain Warden", "Grassland Chieftain", "Field Sovereign"],
    "forest": ["Forest Lord", "Grove Keeper", "Woodland Sovereign"]
}

# Ruler characteristics/traits
RULER_TRAITS = {
    "governing_style": [
        "Authoritarian", "Democratic", "Meritocratic", "Plutocratic", "Theocratic", 
        "Militaristic", "Diplomatic", "Traditionalist", "Progressive", "Technocratic"
    ],
    "personality": [
        "Ambitious", "Cautious", "Charismatic", "Cunning", "Disciplined", 
        "Eccentric", "Generous", "Harsh", "Innovative", "Paranoid",
        "Patient", "Pious", "Ruthless", "Scholarly", "Volatile"
    ],
    "priorities": [
        "Military", "Commerce", "Education", "Infrastructure", "Culture",
        "Spirituality", "Technology", "Security", "Exploration", "Diplomacy"
    ],
    "age_group": [
        "Young", "Middle-aged", "Elderly", "Ancient"
    ],
    "background": [
        "Noble Birth", "Common Birth", "Military", "Academic", "Religious",
        "Merchant", "Criminal", "Foreign", "Mysterious", "Prophesied"
    ]
}

def create_ruler_role(db) -> str:
    """Create a ruler role if it doesn't exist yet."""
    ruler_role = db.query(Role).filter(Role.role_code == "ruler").first()
    
    if ruler_role:
        print(f"Ruler role already exists: {ruler_role.role_name}")
        return str(ruler_role.role_id)
    
    # Define the ruler role attributes schema
    attribute_schema = {
        "type": "object",
        "properties": {
            # Ruler focus areas (0-100 scale)
            "expansion_focus": {
                "type": "number",
                "description": "How focused the ruler is on territorial expansion"
            },
            "wealth_focus": {
                "type": "number",
                "description": "How focused the ruler is on accumulating wealth"
            },
            "happiness_focus": {
                "type": "number",
                "description": "How focused the ruler is on citizens' happiness"
            },
            "magic_focus": {
                "type": "number",
                "description": "How focused the ruler is on magical development"
            },
            "military_focus": {
                "type": "number",
                "description": "How focused the ruler is on military strength"
            },
            "innovation_focus": {
                "type": "number",
                "description": "How focused the ruler is on technological innovation"
            },
            
            # Ruler personality traits
            "governing_style": {
                "type": "string",
                "description": "The ruler's general approach to governance"
            },
            "personality_traits": {
                "type": "array",
                "items": {
                    "type": "string"
                },
                "description": "Key personality traits of the ruler"
            },
            "priorities": {
                "type": "array",
                "items": {
                    "type": "string"
                },
                "description": "The ruler's policy priorities"
            },
            
            # Ruler stats
            "popularity": {
                "type": "number",
                "description": "How popular the ruler is with their subjects (0-100)"
            },
            "corruption": {
                "type": "number",
                "description": "How corrupt the ruler's administration is (0-100)"
            },
            "diplomatic_influence": {
                "type": "number",
                "description": "The ruler's influence in diplomatic matters (0-100)"
            },
            
            # Ruler background
            "title": {
                "type": "string",
                "description": "The ruler's formal title"
            },
            "years_in_power": {
                "type": "number",
                "description": "How many years the ruler has been in power"
            },
            "age_group": {
                "type": "string",
                "description": "The age category of the ruler"
            },
            "background": {
                "type": "string",
                "description": "The ruler's background before taking power"
            }
        }
    }
    
    # Create the role
    ruler_role_id = str(uuid.uuid4())
    ruler_role = Role(
        role_id=ruler_role_id,
        role_code="ruler",
        role_name="Ruler",
        description="Leader of a settlement who makes decisions about growth, development, and policies",
        attribute_schema=attribute_schema,
        required_skills={
            "leadership": 30,
            "diplomacy": 20,
            "administration": 20
        },
        role_benefits={
            "tax_income": True,
            "command_authority": True,
            "settlement_control": True
        }
    )
    
    db.add(ruler_role)
    db.commit()
    
    print(f"Created new ruler role with ID: {ruler_role_id}")
    return ruler_role_id

def generate_ruler_name(area_type: str) -> tuple:
    """Generate a appropriate ruler name based on settlement type."""
    gender = random.choice(["male", "female"])
    
    # Select title based on area type
    title_category = area_type if area_type in TITLES else "town"
    title = random.choice(TITLES[title_category])
    
    # Adjust title for gender if needed
    if gender == "female" and title in ["King", "Emperor", "Grand Duke"]:
        title = {"King": "Queen", "Emperor": "Empress", "Grand Duke": "Grand Duchess"}[title]
    
    # Select name based on gender
    if gender == "male":
        name = random.choice(MALE_NAMES)
    else:
        name = random.choice(FEMALE_NAMES)
    
    return (f"{title} {name}", gender)

def generate_ruler_attributes() -> Dict[str, Any]:
    """Generate ruler attributes with random but sensible values."""
    # Select personality traits
    governing_style = random.choice(RULER_TRAITS["governing_style"])
    personality_traits = random.sample(RULER_TRAITS["personality"], k=random.randint(2, 4))
    priorities = random.sample(RULER_TRAITS["priorities"], k=random.randint(2, 3))
    age_group = random.choice(RULER_TRAITS["age_group"])
    background = random.choice(RULER_TRAITS["background"])
    
    # Generate focus areas (these will influence decision-making)
    expansion_focus = random.randint(0, 100)
    wealth_focus = random.randint(0, 100)
    happiness_focus = random.randint(0, 100)
    magic_focus = random.randint(0, 100)
    military_focus = random.randint(0, 100)
    innovation_focus = random.randint(0, 100)
    
    # Generate popularity and other stats
    popularity = random.randint(20, 90)
    corruption = random.randint(0, 70)
    diplomatic_influence = random.randint(10, 100)
    years_in_power = random.randint(1, 30)
    
    return {
        "expansion_focus": expansion_focus,
        "wealth_focus": wealth_focus,
        "happiness_focus": happiness_focus,
        "magic_focus": magic_focus,
        "military_focus": military_focus,
        "innovation_focus": innovation_focus,
        "governing_style": governing_style,
        "personality_traits": personality_traits,
        "priorities": priorities,
        "popularity": popularity,
        "corruption": corruption,
        "diplomatic_influence": diplomatic_influence,
        "age_group": age_group,
        "background": background,
        "years_in_power": years_in_power
    }

def create_ruler_for_settlement(db, settlement, ruler_role_id):
    """Create a ruler NPC and character for a settlement."""
    # Generate appropriate name and title
    full_name, gender = generate_ruler_name(settlement.area_type)
    name_parts = full_name.split(" ", 1)
    title = name_parts[0] if len(name_parts) > 1 else ""
    name = name_parts[1] if len(name_parts) > 1 else name_parts[0]
    
    # Get or create NPC type for rulers
    npc_type = db.query(NpcTypes).filter(NpcTypes.npc_code == "ruler").first()
    if not npc_type:
        npc_type_id = str(uuid.uuid4())
        npc_type = NpcTypes(
            npc_type_id=npc_type_id,
            npc_code="ruler",
            npc_name="Settlement Ruler",
            role="governance",
            description="Leader of a settlement who makes decisions about development and policy"
        )
        db.add(npc_type)
        db.commit()
    
    # Generate ruler attributes
    attributes = generate_ruler_attributes()
    attributes["title"] = title
    
    # Create character
    character_id = str(uuid.uuid4())
    character = Characters(
        character_id=character_id,
        world_id=settlement.world_id,
        character_name=full_name,
        health=100,
        energy=100,
        created_at=datetime.now(),
        last_active=datetime.now()
    )
    db.add(character)
    
    # Create NPC
    npc_id = str(uuid.uuid4())
    skills_json = {
        "leadership": random.randint(50, 100),
        "diplomacy": random.randint(30, 90),
        "administration": random.randint(40, 95),
        "warfare": random.randint(20, 80) if attributes["military_focus"] > 50 else random.randint(10, 40),
        "magic": random.randint(50, 90) if attributes["magic_focus"] > 50 else random.randint(5, 30),
        "economics": random.randint(50, 90) if attributes["wealth_focus"] > 50 else random.randint(30, 60)
    }
    
    stats_json = {
        "strength": random.randint(3, 18),
        "dexterity": random.randint(3, 18),
        "constitution": random.randint(3, 18),
        "intelligence": random.randint(8, 18),  # Rulers tend to be more intelligent
        "wisdom": random.randint(8, 18),
        "charisma": random.randint(10, 18)  # Rulers tend to be charismatic
    }
    
    npc = Npcs(
        npc_id=npc_id,
        world_id=settlement.world_id,
        npc_type_id=npc_type.npc_type_id,
        settlement_id=settlement.settlement_id,
        npc_name=full_name,
        health=100,
        stats=json.dumps(stats_json),
        skills=json.dumps(skills_json),
        current_location_type="settlement",
        current_location_id=settlement.settlement_id,
        created_at=datetime.now(),
        last_updated=datetime.now()
    )
    db.add(npc)
    
    # Create character role
    character_role_id = str(uuid.uuid4())
    character_role = CharacterRole(
        character_role_id=character_role_id,
        character_id=character_id,
        character_type="npc",
        role_id=ruler_role_id,
        level=random.randint(1, 10),
        attributes=attributes,
        is_active=True,
        gained_at=datetime.now(),
        updated_at=datetime.now()
    )
    db.add(character_role)
    
    # Update settlement with owner
    settlement.owner_character_id = character_id
    
    # Commit changes
    db.commit()
    
    print(f"Created ruler '{full_name}' for settlement '{settlement.settlement_name}'")
    print(f"  Character ID: {character_id}")
    print(f"  NPC ID: {npc_id}")
    print(f"  Focus areas: Expansion {attributes['expansion_focus']}, Wealth {attributes['wealth_focus']}, " + 
          f"Happiness {attributes['happiness_focus']}, Magic {attributes['magic_focus']}")
    print(f"  Personality: {attributes['governing_style']} ruler with traits: {', '.join(attributes['personality_traits'])}")
    
    return character_id, npc_id

def main():
    """Main function to create rulers for all settlements."""
    db = SessionLocal()
    try:
        # Create ruler role if needed
        ruler_role_id = create_ruler_role(db)
        
        # Get all settlements without owners
        settlements = db.query(Settlements).filter(Settlements.owner_character_id.is_(None)).all()
        
        print(f"Found {len(settlements)} settlements without rulers")
        
        # Process each settlement
        for settlement in settlements:
            print(f"\nProcessing settlement: {settlement.settlement_name} (Type: {settlement.area_type})")
            create_ruler_for_settlement(db, settlement, ruler_role_id)
            
    except Exception as e:
        db.rollback()
        print(f"Error creating settlement rulers: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
        
    print("\nSettlement ruler creation complete!")

if __name__ == "__main__":
    main()