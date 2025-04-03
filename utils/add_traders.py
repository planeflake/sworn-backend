#!/usr/bin/env python
"""
Create new NPCs with trading skills and corresponding traders.
This script adds 5 traders with varying trading specialties to the first 
available world and settlement.
"""

import sys
import os
import uuid
import json
from datetime import datetime
from sqlalchemy import select

# Add the project root to the path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import SessionLocal
from app.models.core import Worlds, Settlements, NpcTypes, Npcs, Traders

def create_traders():
    """Create new NPCs and traders with trading skills"""
    db = SessionLocal()
    try:
        # Get or create world
        world = db.query(Worlds).first()
        if not world:
            world_id = str(uuid.uuid4())
            world = Worlds(
                world_id=world_id,
                world_name="Test World",
                active=True,
                creation_date=datetime.now(),
                last_updated=datetime.now()
            )
            db.add(world)
            db.commit()
            print(f"Created new world: {world.world_name} (ID: {world.world_id})")
        else:
            print(f"Using existing world: {world.world_name} (ID: {world.world_id})")
        
        # Get or create settlement
        settlement = db.query(Settlements).first()
        if not settlement:
            settlement_id = str(uuid.uuid4())
            settlement = Settlements(
                settlement_id=settlement_id,
                world_id=world.world_id,
                settlement_name="Trading Post",
                area_type="town",
                location_x=100,
                location_y=100,
                population=500,
                last_updated=datetime.now()
            )
            db.add(settlement)
            db.commit()
            print(f"Created new settlement: {settlement.settlement_name} (ID: {settlement.settlement_id})")
        else:
            print(f"Using existing settlement: {settlement.settlement_name} (ID: {settlement.settlement_id})")
        
        # Get or create trader NPC type
        npc_type = db.query(NpcTypes).filter(NpcTypes.npc_code == "trader").first()
        if not npc_type:
            npc_type_id = str(uuid.uuid4())
            npc_type = NpcTypes(
                npc_type_id=npc_type_id,
                npc_code="trader",
                npc_name="Merchant",
                role="trading",
                description="A trader who buys and sells goods."
            )
            db.add(npc_type)
            db.commit()
            print(f"Created new NPC type: {npc_type.npc_name} (ID: {npc_type.npc_type_id})")
        else:
            print(f"Using existing NPC type: {npc_type.npc_name} (ID: {npc_type.npc_type_id})")
        
        # Trader data - contains tuples of (name, description, stats, skills, personality, biomes, cart_upgrades, gold, guards)
        trader_data = [
            (
                "Orrin Silverhand", 
                "A master trader known throughout the realm for fair deals and extensive knowledge of markets.",
                {"strength": 10, "dexterity": 14, "intelligence": 18, "charisma": 20},
                {"trading": 95, "negotiation": 90, "appraisal": 85, "leadership": 75},
                {"shrewd": 0.9, "honest": 0.7, "ambitious": 0.8},
                {"coastal": 0.8, "forest": 0.6, "mountain": 0.4},
                ["reinforced_axles", "weather_protection", "hidden_compartment"],
                5000,
                3
            ),
            (
                "Lyra Nightshade", 
                "Specializes in exotic and rare goods from distant lands. Has connections with many secretive suppliers.",
                {"strength": 8, "dexterity": 16, "intelligence": 19, "charisma": 18},
                {"trading": 85, "appraisal": 92, "alchemy": 75, "persuasion": 80},
                {"mysterious": 0.9, "knowledgeable": 0.8, "secretive": 0.7},
                {"swamp": 0.7, "desert": 0.6, "jungle": 0.9},
                ["specialized_containers", "arcane_wards", "climate_control"],
                4200,
                2
            ),
            (
                "Thorne Ironwood", 
                "A gruff but reliable caravan master who specializes in bulk goods and safe transport through dangerous regions.",
                {"strength": 16, "dexterity": 12, "intelligence": 14, "charisma": 16},
                {"trading": 80, "survival": 85, "navigation": 90, "combat": 70},
                {"brave": 0.8, "practical": 0.9, "protective": 0.7},
                {"plains": 0.9, "forest": 0.7, "mountain": 0.8},
                ["additional_wagon", "guard_post", "animal_housing"],
                3800,
                5
            ),
            (
                "Milo Quickfoot", 
                "A nimble peddler who travels light and specializes in small valuable items. Known for finding great deals.",
                {"strength": 9, "dexterity": 18, "intelligence": 15, "charisma": 17},
                {"trading": 75, "stealth": 70, "sleight_of_hand": 80, "bargaining": 90},
                {"charming": 0.9, "opportunistic": 0.8, "adaptable": 0.9},
                {"urban": 0.9, "coastal": 0.7, "plains": 0.6},
                ["lightweight_frame", "quick_release_harness", "concealed_compartments"],
                2500,
                1
            ),
            (
                "Seraphina Goldweaver", 
                "Representative of a powerful trading consortium. Specializes in luxury goods and high-value trade contracts.",
                {"strength": 10, "dexterity": 14, "intelligence": 20, "charisma": 19},
                {"trading": 95, "diplomacy": 90, "economics": 95, "law": 85},
                {"sophisticated": 0.9, "calculating": 0.8, "diplomatic": 0.9},
                {"urban": 0.9, "coastal": 0.8, "mountain": 0.4},
                ["luxury_fittings", "secure_lockboxes", "diplomatic_insignia"],
                10000,
                4
            )
        ]
        
        # Create each trader
        for trader_info in trader_data:
            (name, desc, stats, skills, personality, biomes, upgrades, gold, guards) = trader_info
            
            # Check if this trader already exists
            existing_npc = db.query(Npcs).filter(Npcs.npc_name == name).first()
            if existing_npc:
                print(f"Trader '{name}' already exists, skipping...")
                continue
            
            # Create NPC
            npc_id = str(uuid.uuid4())
            new_npc = Npcs(
                npc_id=npc_id,
                world_id=world.world_id,
                npc_type_id=npc_type.npc_type_id,
                settlement_id=settlement.settlement_id,
                npc_name=name,
                health=100,
                stats=json.dumps(stats),
                skills=json.dumps(skills),
                current_location_type="settlement",
                current_location_id=settlement.settlement_id,
                created_at=datetime.now(),
                last_updated=datetime.now()
            )
            db.add(new_npc)
            
            # Create corresponding Trader
            trader_id = str(uuid.uuid4())
            new_trader = Traders(
                trader_id=trader_id,
                world_id=world.world_id,
                npc_id=npc_id,
                npc_name=name,
                home_settlement_id=settlement.settlement_id,
                current_settlement_id=settlement.settlement_id,
                personality=json.dumps(personality),
                biome_preferences=json.dumps(biomes),
                cart_capacity=1000,
                cart_health=100,
                cart_upgrades=json.dumps(upgrades),
                gold=gold,
                hired_guards=guards,
                last_updated=datetime.now(),
                can_move=True
            )
            db.add(new_trader)
            
            # Commit each trader individually so if one fails, others can still be created
            try:
                db.commit()
                print(f"Created trader: {name} (NPC ID: {npc_id}, Trader ID: {trader_id})")
            except Exception as e:
                db.rollback()
                print(f"Error creating trader {name}: {e}")
        
        print("Trader creation process completed!")
        
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_traders()