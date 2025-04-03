from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from database.connection import Base

class Equipment(Base):
    """
    Represents an item equipped by a player or npc.
    """
    __tablename__ = "equipment"
    
    equipment_id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    item_id = Column(UUID(as_uuid=True), ForeignKey("item.item_id"))
    player_id = Column(UUID(as_uuid=True), ForeignKey("player.player_id"))
    is_equipped = Column(Boolean)
    is_stolen = Column(Boolean)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    durability = Column(Integer)
    quality = Column(Integer)
    enchantments = Column(JSONB)
    is_cursed = Column(Boolean)
    curse_effect = Column(String)
    curse_duration = Column(Integer)
    curse_remaining = Column(Integer)
    is_broken = Column(Boolean)
    is_locked = Column(Boolean)
    is_hidden = Column(Boolean)
    is_unique = Column(Boolean)
    is_quest_item = Column(Boolean)
    is_artifact = Column(Boolean)
    is_relic = Column(Boolean)
    is_consumable = Column(Boolean)
    is_stackable = Column(Boolean)
    is_equipment = Column(Boolean)