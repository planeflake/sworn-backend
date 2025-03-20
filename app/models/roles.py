from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from models.core import Base

class Role(Base):
    """Defines a character role like trader, blacksmith, etc."""
    __tablename__ = 'roles'
    
    role_id = Column(UUID, primary_key=True)
    role_code = Column(String, nullable=False, unique=True)
    role_name = Column(String, nullable=False)
    description = Column(Text)
    attribute_schema = Column(JSONB)  # JSON schema defining required attributes
    required_skills = Column(JSONB)  # Skills needed to gain this role
    role_benefits = Column(JSONB)  # Benefits gained from this role
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class CharacterRole(Base):
    """Assigns roles to characters (NPCs or players)"""
    __tablename__ = 'character_roles'
    
    character_role_id = Column(UUID, primary_key=True)
    character_id = Column(UUID, nullable=False)
    character_type = Column(String, nullable=False)  # 'npc' or 'player'
    role_id = Column(UUID, ForeignKey('roles.role_id', ondelete='CASCADE'), nullable=False)
    level = Column(Integer, nullable=False, default=1)
    attributes = Column(JSONB)  # Role-specific attributes
    is_active = Column(Boolean, nullable=False, default=True)
    gained_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class Skill(Base):
    """Defines a skill that characters can learn"""
    __tablename__ = 'skills'
    
    skill_id = Column(UUID, primary_key=True)
    skill_code = Column(String, nullable=False, unique=True)
    skill_name = Column(String, nullable=False)
    category = Column(String)
    description = Column(Text)
    max_level = Column(Integer, default=100)
    xp_curve = Column(JSONB)  # How XP requirements scale
    effects = Column(JSONB)  # Effects at different levels
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class CharacterSkill(Base):
    """Tracks a character's skill level"""
    __tablename__ = 'character_skills'
    
    character_skill_id = Column(UUID, primary_key=True)
    character_id = Column(UUID, nullable=False)
    character_type = Column(String, nullable=False)  # 'npc' or 'player'
    skill_id = Column(UUID, ForeignKey('skills.skill_id', ondelete='CASCADE'), nullable=False)
    level = Column(Integer, nullable=False, default=0)
    xp = Column(Integer, nullable=False, default=0)
    last_used = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())