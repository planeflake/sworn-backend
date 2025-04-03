#!/usr/bin/env python
"""
List all settlements and their rulers with detailed characteristics.

This script displays:
1. Settlement information
2. Ruler details including name, title, and role
3. Ruler characteristics like expansion focus, wealth focus, etc.
4. Ruler traits, priorities, and governing style
"""

import sys
import os
import json
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import SessionLocal
from app.models.core import Settlements, Npcs, Characters
from app.models.roles import Role, CharacterRole

def get_ruler_data(db, settlement):
    """Get detailed information about a settlement's ruler."""
    if not settlement.owner_character_id:
        return None
    
    # Get character
    character = db.query(Characters).filter(
        Characters.character_id == settlement.owner_character_id
    ).first()
    
    if not character:
        return {"error": "Character not found", "character_id": settlement.owner_character_id}
    
    # Get character role
    character_role = db.query(CharacterRole).filter(
        CharacterRole.character_id == character.character_id,
        CharacterRole.character_type == "npc",
        CharacterRole.is_active == True
    ).first()
    
    role_data = {}
    if character_role:
        role = db.query(Role).filter(Role.role_id == character_role.role_id).first()
        role_data = {
            "role_id": str(role.role_id) if role else None,
            "role_name": role.role_name if role else None,
            "role_level": character_role.level,
            "attributes": character_role.attributes
        }
    
    # Get NPC
    npc = db.query(Npcs).filter(
        Npcs.npc_name == character.character_name
    ).first()
    
    npc_data = {}
    if npc:
        skills = {}
        stats = {}
        
        try:
            if npc.skills:
                if isinstance(npc.skills, str):
                    skills = json.loads(npc.skills)
                else:
                    skills = npc.skills
        except:
            skills = {"error": "Could not parse skills"}
            
        try:
            if npc.stats:
                if isinstance(npc.stats, str):
                    stats = json.loads(npc.stats)
                else:
                    stats = npc.stats
        except:
            stats = {"error": "Could not parse stats"}
            
        npc_data = {
            "npc_id": str(npc.npc_id),
            "skills": skills,
            "stats": stats
        }
    
    return {
        "character_id": str(character.character_id),
        "name": character.character_name,
        "role": role_data,
        "npc": npc_data
    }

def format_focus_bar(value, max_width=20):
    """Create a visual bar representation of a focus value."""
    filled = int((value / 100) * max_width)
    return f"[{'#' * filled}{' ' * (max_width - filled)}] {value}/100"

def main():
    """Main function to list all settlements and their rulers."""
    db = SessionLocal()
    try:
        # Get all settlements
        settlements = db.query(Settlements).all()
        
        print(f"=== Settlements and Rulers (Total: {len(settlements)}) ===\n")
        
        for settlement in settlements:
            print(f"Settlement: {settlement.settlement_name}")
            print(f"  ID: {settlement.settlement_id}")
            print(f"  Type: {settlement.area_type}")
            print(f"  Biome: {settlement.biome}")
            print(f"  Population: {settlement.population}")
            
            ruler_data = get_ruler_data(db, settlement)
            
            if ruler_data:
                print(f"  Ruler: {ruler_data['name']}")
                
                if "role" in ruler_data and ruler_data["role"] and "attributes" in ruler_data["role"]:
                    attrs = ruler_data["role"]["attributes"]
                    
                    if attrs:
                        print("\n  Characteristics:")
                        
                        focus_areas = [
                            ("Expansion", attrs.get("expansion_focus", 0)),
                            ("Wealth", attrs.get("wealth_focus", 0)),
                            ("Happiness", attrs.get("happiness_focus", 0)),
                            ("Magic", attrs.get("magic_focus", 0)),
                            ("Military", attrs.get("military_focus", 0)),
                            ("Innovation", attrs.get("innovation_focus", 0))
                        ]
                        
                        for name, value in focus_areas:
                            print(f"    {name + ':':12} {format_focus_bar(value)}")
                            
                        print("\n  Governance:")
                        print(f"    Style:      {attrs.get('governing_style', 'Unknown')}")
                        print(f"    Priorities: {', '.join(attrs.get('personality_traits', []))}")
                        print(f"    Focuses:    {', '.join(attrs.get('priorities', []))}")
                        print(f"    Age:        {attrs.get('age_group', 'Unknown')}")
                        print(f"    Background: {attrs.get('background', 'Unknown')}")
                        print(f"    Years in power: {attrs.get('years_in_power', 'Unknown')}")
                        
                        print("\n  Stats:")
                        print(f"    Popularity:         {format_focus_bar(attrs.get('popularity', 0))}")
                        print(f"    Corruption:         {format_focus_bar(attrs.get('corruption', 0))}")
                        print(f"    Diplomatic influence: {format_focus_bar(attrs.get('diplomatic_influence', 0))}")
                
                if "npc" in ruler_data and ruler_data["npc"] and "skills" in ruler_data["npc"]:
                    skills = ruler_data["npc"]["skills"]
                    if skills and not isinstance(skills, str) and not "error" in skills:
                        print("\n  Skills:")
                        for skill, value in skills.items():
                            print(f"    {skill + ':':14} {format_focus_bar(value)}")
                
                if "npc" in ruler_data and ruler_data["npc"] and "stats" in ruler_data["npc"]:
                    stats = ruler_data["npc"]["stats"]
                    if stats and not isinstance(stats, str) and not "error" in stats:
                        print("\n  Base Stats:")
                        for stat, value in stats.items():
                            print(f"    {stat + ':':14} {value}")
            else:
                print("  No ruler assigned")
            
            print("\n" + "-" * 80 + "\n")
        
    except Exception as e:
        print(f"Error listing settlement rulers: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()