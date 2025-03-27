from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from models.core import Base

class Quest(Base):
    quest_id = Column(UUID(as_uuid=True), primary_key=True, server_default=Text("uuid_generate_v4()"))
    name = Column(String)
    description = Column(String)
    type = Column(String)
    status = Column(String)
    objectives = Column(JSONB)
    properties = Column(JSONB)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    _is_dirty = Column(Boolean, default=True)
    