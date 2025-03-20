from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from models.core import Base

class Equipment(Base):
    """
    Represents an item equipped by a player or npc.
    """
    equipment_id = Column(UUID(as_uuid=True), primary_key=True, server_default=Text("uuid_generate_v4()"))
    item_id = Column(UUID(as_uuid=True), ForeignKey("item.item_id"))
    player_id = Column(UUID(as_uuid=True), ForeignKey("player.player_id"))
    is_equipped = Column(Boolean)
    is_stolen = Column(Boolean)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())