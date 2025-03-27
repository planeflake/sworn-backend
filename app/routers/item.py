# routers/trader.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from uuid import UUID

from database.connection import get_db
from app.models.item import Item
from app.schemas.item import ItemBase, ItemResponse, ItemCreate
from app.game_state.managers.item_manager import ItemManager

router = APIRouter(prefix="/items", tags=["items"])

@router.post("/", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    item_manager = ItemManager(db)
    new_item = item_manager.create_item(item)
    return new_item

@router.get("/", response_model=List[ItemResponse])
async def get_items(db: Session = Depends(get_db)):
    item_manager = ItemManager(db)
    items = item_manager.get_all_items()
    return items

@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(item_id: UUID, db: Session = Depends(get_db)):
    item_manager = ItemManager(db)
    item = item_manager.get_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@router.put("/{item_id}", response_model=ItemResponse)
async def update_item(item_id: UUID, item: ItemBase, db: Session = Depends(get_db)):
    item_manager = ItemManager(db)
    updated_item = item_manager.update_item(item_id, item)
    if updated_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return updated_item

@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(item_id: UUID, db: Session = Depends(get_db)):
    item_manager = ItemManager(db)
    item_manager.delete_item(item_id)
    return None