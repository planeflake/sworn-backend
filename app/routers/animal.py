# routers/animal.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from database.connection import get_db
from app.models.animals import Animal
# Removed duplicate import
from app.schemas.animal import AnimalCreate, AnimalResponse

router = APIRouter(prefix="/animal", tags=["animals"])

@router.post("/", response_model=AnimalResponse, status_code=status.HTTP_201_CREATED)
async def create_player(player: AnimalCreate, db: Session = Depends(get_db)):
    db_player = Animal(**player.dict())
    db.add(db_player)
    db.commit()
    db.refresh(db_player)
    return db_player

@router.post("/animals/{area_id}", response_model=AnimalResponse, status_code=status.HTTP_201_CREATED)
async def create_animal(area_id: UUID, animal: AnimalCreate, db: Session = Depends(get_db)):
    db_animal = Animal(**animal.dict(), area_id=area_id)
    db.add(db_animal)
    db.commit()
    db.refresh(db_animal)
    return db_animal

@router.get("/animals/{animal_id}", response_model=AnimalResponse)
async def read_animal(animal_id: UUID, db: Session = Depends(get_db)):
    db_animal = db.query(Animal).filter(Animal.animal_id == animal_id).first()
    if db_animal is None:
        raise HTTPException(status_code=404, detail="Animal not found")
    return db_animal

@router.get("/animals/relations", response_model=List[AnimalResponse])
async def get_animal_relations(
    relation: str = Query(..., regex="^(prey|predators)$"),
    area_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db)
):
    if relation == "prey":
        query = db.query(Animal).filter(Animal.is_prey == True)
    elif relation == "predators":
        query = db.query(Animal).filter(Animal.is_predator == True)
    else:
        raise HTTPException(status_code=400, detail="Invalid relation type")
    
    if area_id:
        query = query.filter(Animal.area_id == area_id)
    
    animals = query.all()
    return animals
