"""Recipient capability, need, and time-bounded availability state."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
    select,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import Select
from sqlalchemy.types import Uuid

from backend.app.models.base import Base
from backend.app.models.site import Site
from backend.app.models.source import SourceRecord
from backend.app.models.user import User


class RecipientCapability(Base):
    """A versioned rule describing what a recipient site can normally handle."""

    __tablename__ = "recipient_capabilities"
    __table_args__ = (
        CheckConstraint(
            "storage_class IN ('ambient', 'chilled', 'frozen', 'any')",
            name="ck_recipient_capabilities_storage_class",
        ),
        CheckConstraint(
            "visibility IN ('operational', 'protected')",
            name="ck_recipient_capabilities_visibility",
        ),
        CheckConstraint(
            "valid_until IS NULL OR valid_until > valid_from",
            name="ck_recipient_capabilities_valid_period",
        ),
        UniqueConstraint(
            "site_id",
            "food_category",
            "storage_class",
            "valid_from",
            name="uq_recipient_capabilities_version",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Internal identity for one capability version.",
    )
    site_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("sites.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Recipient operational site to which the capability applies.",
    )
    food_category: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Food category or matching lane; taxonomy is intentionally data-driven.",
    )
    storage_class: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="Storage lane accepted by the site.",
    )
    visibility: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="operational",
        server_default="operational",
        comment="Operational or protected recipient-state visibility.",
    )
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        comment="Inclusive start of this capability version.",
    )
    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Exclusive end; NULL means no recorded end.",
    )
    updated_by_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Operator responsible for this capability version.",
    )
    notes: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Operational handling note; not a substitute for the controlled lane.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        comment="When this capability version was recorded.",
    )

    site: Mapped[Site] = relationship()
    updated_by_user: Mapped[User] = relationship()


class RecipientNeed(Base):
    """A time-bounded quantity need declared by a recipient site."""

    __tablename__ = "recipient_needs"
    __table_args__ = (
        CheckConstraint(
            "quantity > 0",
            name="ck_recipient_needs_quantity_positive",
        ),
        CheckConstraint(
            "quantity_unit IN ('kg', 'g', 'unit', 'case', 'box', 'crate', 'litre', 'ml')",
            name="ck_recipient_needs_quantity_unit",
        ),
        CheckConstraint(
            "storage_class IN ('ambient', 'chilled', 'frozen', 'any')",
            name="ck_recipient_needs_storage_class",
        ),
        CheckConstraint(
            "priority BETWEEN 1 AND 5",
            name="ck_recipient_needs_priority",
        ),
        CheckConstraint(
            "receiving_window_end > receiving_window_start",
            name="ck_recipient_needs_receiving_window",
        ),
        CheckConstraint(
            "valid_until IS NULL OR valid_until > valid_from",
            name="ck_recipient_needs_valid_period",
        ),
        CheckConstraint(
            "visibility IN ('operational', 'protected')",
            name="ck_recipient_needs_visibility",
        ),
        UniqueConstraint(
            "site_id",
            "food_category",
            "storage_class",
            "valid_from",
            name="uq_recipient_needs_version",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Internal identity for one need declaration.",
    )
    site_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("sites.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Recipient site declaring the need.",
    )
    food_category: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Food category or matching lane requested by the site.",
    )
    storage_class: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="Storage lane required for the need.",
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 3),
        nullable=False,
        comment="Requested quantity in the declared unit.",
    )
    quantity_unit: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="Controlled quantity unit; no implicit conversion is performed.",
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Priority input from 1 to 5; 5 is highest urgency.",
    )
    receiving_window_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Inclusive receiving-window start.",
    )
    receiving_window_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Exclusive receiving-window end.",
    )
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        comment="Inclusive start of this need version.",
    )
    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Exclusive end; NULL means no recorded end.",
    )
    visibility: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="operational",
        server_default="operational",
        comment="Operational or protected need visibility.",
    )
    updated_by_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Operator responsible for this need version.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        comment="When this need version was recorded.",
    )

    site: Mapped[Site] = relationship()
    updated_by_user: Mapped[User] = relationship()


class RecipientAvailabilitySnapshot(Base):
    """A time-bounded capacity snapshot used as matching input."""

    __tablename__ = "recipient_availability_snapshots"
    __table_args__ = (
        CheckConstraint(
            "capacity_status IN ('known', 'unknown')",
            name="ck_recipient_availability_capacity_status",
        ),
        CheckConstraint(
            "(capacity_status = 'known' AND available_quantity IS NOT NULL "
            "AND available_quantity >= 0) "
            "OR (capacity_status = 'unknown' AND available_quantity IS NULL)",
            name="ck_recipient_availability_quantity_semantics",
        ),
        CheckConstraint(
            "quantity_unit IN ('kg', 'g', 'unit', 'case', 'box', 'crate', 'litre', 'ml')",
            name="ck_recipient_availability_quantity_unit",
        ),
        CheckConstraint(
            "storage_class IN ('ambient', 'chilled', 'frozen', 'any')",
            name="ck_recipient_availability_storage_class",
        ),
        CheckConstraint(
            "receiving_window_end > receiving_window_start",
            name="ck_recipient_availability_receiving_window",
        ),
        CheckConstraint(
            "valid_until > valid_from",
            name="ck_recipient_availability_valid_period",
        ),
        CheckConstraint(
            "visibility IN ('operational', 'protected')",
            name="ck_recipient_availability_visibility",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Internal identity for one capacity snapshot.",
    )
    site_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("sites.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Recipient site whose current capacity is represented.",
    )
    food_category: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Food category or matching lane for this capacity.",
    )
    storage_class: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="Storage lane for this capacity snapshot.",
    )
    capacity_status: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        comment="Known zero is different from unknown capacity.",
    )
    available_quantity: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 3),
        nullable=True,
        comment="Remaining capacity when capacity_status is known.",
    )
    quantity_unit: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="Unit of available_quantity.",
    )
    receiving_window_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Inclusive receiving-window start.",
    )
    receiving_window_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Exclusive receiving-window end.",
    )
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="When the operator/provider observed the capacity.",
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        comment="When FoodFlow recorded the snapshot.",
    )
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        comment="Inclusive start of the snapshot validity window.",
    )
    valid_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Exclusive freshness boundary; stale data is not current capacity.",
    )
    visibility: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="operational",
        server_default="operational",
        comment="Operational or protected capacity visibility.",
    )
    updated_by_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Operator responsible for this snapshot.",
    )
    source_record_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_records.id", ondelete="RESTRICT"),
        nullable=True,
        comment="Optional external provenance for a capacity observation.",
    )

    site: Mapped[Site] = relationship()
    updated_by_user: Mapped[User] = relationship()
    source_record: Mapped[SourceRecord | None] = relationship()


def current_recipient_availability_statement(
    *,
    as_of: datetime,
) -> Select[tuple[RecipientAvailabilitySnapshot]]:
    """Return current snapshots without treating unknown capacity as zero."""

    return (
        select(RecipientAvailabilitySnapshot)
        .join(RecipientAvailabilitySnapshot.site)
        .where(
            Site.status == "active",
            RecipientAvailabilitySnapshot.valid_from <= as_of,
            RecipientAvailabilitySnapshot.valid_until > as_of,
        )
    )


def public_recipient_availability_statement(
    *,
    as_of: datetime,
) -> Select[tuple[RecipientAvailabilitySnapshot]]:
    """Return only operationally visible current capacity snapshots."""

    return current_recipient_availability_statement(as_of=as_of).where(
        RecipientAvailabilitySnapshot.visibility == "operational",
    )
