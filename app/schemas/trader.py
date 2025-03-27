# schemas/trader.py
from pydantic import BaseModel, UUID4, validator, Field
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime

from app.schemas.base import TimeStampModel

class TraderBase(BaseModel):
    npc_id: UUID4
    npc_name: str
    home_settlement_id: UUID4
    current_settlement_id: Optional[UUID4] = None  # Ensure this is optional
    cart_capacity: int = Field(..., gt=0)
    cart_health: int = Field(..., ge=0, le=100)
    gold: int = Field(..., ge=0)
    hired_guards: int = Field(..., ge=0)

class TraderCreate(TraderBase):
    world_id: UUID4
    personality: Dict[str, Any] = {}
    biome_preferences: Dict[str, float] = {}
    cart_upgrades: List[str] = []
    schedule: Dict[str, Any] = {}
    life_goal: Dict[str, Any] = {}

class TraderResponse(TraderBase, TimeStampModel):
    trader_id: UUID4
    world_id: UUID4
    personality: Dict[str, Any] = {}
    biome_preferences: Dict[str, float] = {}
    cart_upgrades: List[str] = []
    schedule: Dict[str, Any] = {}
    npc_name: str  # This would be joined from npcs

    class Config:
        orm_mode = True
        
class TraderUpdate(BaseModel):
    npc_name: Optional[str] = None
    current_settlement_id: Optional[UUID4] = None
    destination_id: Optional[UUID4] = None
    cart_capacity: Optional[int] = None
    cart_health: Optional[int] = None
    gold: Optional[int] = None
    personality: Optional[Dict[str, Any]] = None
    biome_preferences: Optional[Dict[str, float]] = None
    cart_upgrades: Optional[List[str]] = None
    schedule: Optional[Dict[str, Any]] = None
    
class TraderWithPath(TraderResponse):
    current_area_id: Optional[str] = None
    journey_path: Optional[List[str]] = None
    path_position: Optional[int] = None
    journey_progress: Optional[int] = None

class TraderInventoryBase(BaseModel):
    resource_type_id: UUID4
    quantity: int = Field(..., ge=0)
    price_modifier: float = Field(..., gt=0)

class TraderInventoryCreate(TraderInventoryBase):
    trader_id: UUID4

class TraderInventoryResponse(TraderInventoryBase, TimeStampModel):
    trader_inventory_id: UUID4
    trader_id: UUID4
    resource_name: str  # This would be joined from resource_types
    base_value: float  # This would be joined from resource_types
    effective_price: float  # Calculated field = base_price * price_modifier

    class Config:
        orm_mode = True

class TradeItemRequest(BaseModel):
    resource_type_id: UUID4
    quantity: int = Field(..., gt=0)

class TradeRequest(BaseModel):
    buy_items: Optional[List[TradeItemRequest]] = []
    sell_items: Optional[List[TradeItemRequest]] = []

class TradeResponse(BaseModel):
    status: str
    trader_id: str
    character_id: str
    gold_spent: int
    gold_received: int
    items_bought: List[Dict[str, Any]]
    items_sold: List[Dict[str, Any]]