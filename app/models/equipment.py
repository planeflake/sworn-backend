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