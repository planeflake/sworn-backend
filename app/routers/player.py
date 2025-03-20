# routers/player.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from database.connection import get_db
from models.core import Players, Characters, CharacterInventory
from models.roles import CharacterSkill
from app.schemas.player import PlayerCreate, PlayerResponse, CharacterCreate, CharacterResponse, InventoryResponse

router = APIRouter(prefix="/players", tags=["players"])

@router.post("/", response_model=PlayerResponse, status_code=status.HTTP_201_CREATED)
async def create_player(player: PlayerCreate, db: Session = Depends(get_db)):
    db_player = Players(**player.dict())
    db.add(db_player)
    db.commit()
    db.refresh(db_player)
    return db_player

@router.get("/{player_id}", response_model=PlayerResponse)
async def get_player(player_id: UUID, db: Session = Depends(get_db)):
    player = db.query(Players).filter(Players.player_id == player_id).first()
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")
    return player

@router.get("/{player_id}/characters", response_model=List[CharacterResponse])
async def get_player_characters(player_id: UUID, db: Session = Depends(get_db)):
    characters = db.query(Characters).filter(Characters.player_id == player_id).all()
    return characters

@router.post("/{player_id}/characters", response_model=CharacterResponse, status_code=status.HTTP_201_CREATED)
async def create_character(player_id: UUID, character: CharacterCreate, db: Session = Depends(get_db)):
    # Check if player exists
    player = db.query(Players).filter(Players.player_id == player_id).first()
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")
    
    db_character = Characters(**character.dict(), player_id=player_id)
    db.add(db_character)
    db.commit()
    db.refresh(db_character)
    return db_character

@router.get("/characters/{character_id}/inventory", response_model=List[InventoryResponse])
async def get_character_inventory(character_id: UUID, db: Session = Depends(get_db)):
    inventory = db.query(CharacterInventory).filter(CharacterInventory.character_id == character_id).all()
    return inventory

@router.post("/characters/{character_id}/gather/{resource_code}")
async def gather_resource(character_id: UUID, resource_code: str, db: Session = Depends(get_db)):
    # This would trigger a task to gather resources based on character location and skills
    # For now, just a placeholder that would later connect to your worker
    return {"status": "Resource gathering initiated", "character_id": str(character_id), "resource": resource_code}