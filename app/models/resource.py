from sqlalchemy import Column, String, Integer, UUID
from typing import Optional
from database.connection import Base

class Resource(Base):
    __tablename__ = "resource_types"
    resource_type_id = Column(UUID, primary_key=True, index=True)
    resource_name = Column(String, nullable=False)
    description = Column(String)
    type = Column(String)
    core_biome = Column(String)
    rarity = Column(Integer)
    value = Column(Integer)
    weight = Column(Integer)

class ResourceSites(Base):
    __tablename__ = "resource_sites"
    resource_site_id = Column(UUID, primary_key=True, index=True)
    resource_type_id = Column(UUID)
    location_id = Column(UUID)
    quantity = Column(Integer)
    quality = Column(Integer)
    is_depleted = Column(Integer)