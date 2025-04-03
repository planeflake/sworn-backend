from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from database.connection import Base

class Faction(Base):
    """
    Represents a faction with membership consisting of player's or npc's.
    """
    __tablename__ = "faction"
    faction_id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    name = Column(String)
    description = Column(String)
    faction_type = Column(String)
    leader_id = Column(UUID(as_uuid=True), ForeignKey("entity.entity_id"))
    members = Column(JSONB)
    controlled_areas = Column(JSONB)
    controlled_settlements = Column(JSONB)
    controlled_entities = Column(JSONB)
    reputation = Column(JSONB)
    relations = Column(JSONB)
    is_hostile = Column(Boolean)
    is_peaceful = Column(Boolean)
    is_neutral = Column(Boolean)
    is_player_faction = Column(Boolean)
    is_npc_faction = Column(Boolean)
    is_retired = Column(Boolean)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())