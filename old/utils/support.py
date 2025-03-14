from models import Characters, PlayerSkills, PlayerInventory
from sqlalchemy.orm import Session
from fastapi import HTTPException
from typing import Dict


def get_character_data(character_id: int, db: Session):
    character = db.query(Characters).filter(Characters.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    # Get skills
    skills = db.query(PlayerSkills).filter(PlayerSkills.character_id == character_id).all()
    skills_dict = {str(skill.skill_id): skill.level for skill in skills}
    
    # Get inventory
    inventory = db.query(PlayerInventory).filter(PlayerInventory.character_id == character_id).all()
    inventory_dict = {str(item.item_id): item.amount for item in inventory}
    
    # Build character data
    character_data = {
        "id": character.id,
        "name": character.name,
        "starting_area_id": character.starting_area_id,
        "background_id": character.background_id,
        "level": character.level,
        "xp": character.xp,
        "energy": character.energy,
        "max_energy": character.max_energy,
        "gold": character.gold,
        "skills": skills_dict,
        "inventory": inventory_dict
    }
    
    return character_data
