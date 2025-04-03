# app/models/buildings.py
import uuid
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List

# Pydantic Imports
from pydantic import BaseModel, Field, ConfigDict

# SQLAlchemy Imports
from sqlalchemy import (
    ForeignKey,
    Integer,
    String,
    Boolean,
    DateTime,
    Numeric,
    Text,
    MetaData,
    text,
    func
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# --- SQLAlchemy Base Definition ---

class Base(DeclarativeBase):
    """Base class for SQLAlchemy declarative models."""
    pass

# --- SQLAlchemy Models ---

class BuildingType(Base):
    __tablename__ = 'building_types'

    building_type_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()")
    )

    theme_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True
    )

    building_code: Mapped[str] = mapped_column(
        String,
        nullable=False,
        unique=True
    )

    building_name: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    building_category: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    construction_time: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )

    resource_requirements: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True
    )

    personnel_requirements: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True
    )

    effects: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True
    )

    upgrade_path: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True
    )

    area_type_bonuses: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True
    )

    # Relationship back to SettlementBuilding
    settlement_buildings: Mapped[List["SettlementBuilding"]] = relationship(
        back_populates="building_type"
    )

    def __repr__(self) -> str:
        return (f"<BuildingType(building_type_id={self.building_type_id!r}, "
                f"code={self.building_code!r}, name={self.building_name!r})>")


class SettlementBuilding(Base):
    __tablename__ = 'settlement_buildings'

    settlement_building_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()")
    )

    settlement_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True
    )

    building_type_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("building_types.building_type_id"),
        nullable=True
    )

    building_type: Mapped[Optional["BuildingType"]] = relationship(
        back_populates="settlement_buildings"
    )

    construction_status: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
        server_default='planned'
    )

    construction_progress: Mapped[Optional[Decimal]] = mapped_column(
        Numeric,
        nullable=True,
        server_default=text("0")
    )

    health: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        server_default=text("100")
    )

    staff_assigned: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True
    )

    is_operational: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
        server_default=text("false")
    )

    constructed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    last_updated: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        server_default=func.now(),
        onupdate=func.now()
    )

    def __repr__(self) -> str:
        return (f"<SettlementBuilding(settlement_building_id={self.settlement_building_id!r}, "
                f"settlement_id={self.settlement_id!r}, type_id={self.building_type_id!r}, "
                f"status={self.construction_status!r})>")

# --- Pydantic Models ---

class SettlementBuildingPydantic(BaseModel):
    """
    Pydantic model representing a record in the settlement_buildings table.
    Uses Python 3.10+ syntax for optional types ( | None ).
    """
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True  # Allow SQLAlchemy types to be used
    )

    settlement_building_id: UUID
    settlement_id: UUID | None = None
    building_type_id: UUID | None = None
    construction_status: str | None = Field(default='planned', description="DB default: 'planned'")
    construction_progress: Decimal | None = Field(default=Decimal(0), description="DB default: 0")
    health: int | None = Field(default=100, description="DB default: 100")
    staff_assigned: Dict[str, Any] | None = None # Representing jsonb
    is_operational: bool | None = Field(default=False, description="DB default: false")
    constructed_at: datetime | None = None
    last_updated: datetime | None = None # Note: DB default CURRENT_TIMESTAMP handled by DB


class BuildingTypePydantic(BaseModel):
    """
    Pydantic model representing a record in the building_types table.
    Uses Python 3.10+ syntax for optional types ( | None ).
    """
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True  # Allow SQLAlchemy types to be used
    )

    building_type_id: UUID
    building_code: str
    building_name: str
    theme_id: UUID | None = None
    building_category: str | None = None
    description: str | None = None
    construction_time: int | None = None
    resource_requirements: Dict[str, Any] | None = None # Flexible JSONB
    personnel_requirements: Dict[str, Any] | None = None # Flexible JSONB
    effects: Dict[str, Any] | None = None # Flexible JSONB
    upgrade_path: Dict[str, Any] | None = None # Flexible JSONB
    area_type_bonuses: Dict[str, Any] | None = None # Flexible JSONB