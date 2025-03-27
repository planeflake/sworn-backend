from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from database.connection import Base

class Item(Base):
    __tablename__ = "items"
    
    item_id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    name = Column(String)
    description = Column(String)
    properties = Column(JSONB)
    is_quest_item = Column(Boolean)
    is_equippable = Column(Boolean)
    is_consumable = Column(Boolean)
    is_stackable = Column(Boolean)
    is_unique = Column(Boolean)
    is_stolen = Column(Boolean)
    durability = Column(Integer)
    _dirty = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())