"""Donation batches, item snapshots, condition observations, and status history."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from backend.app.models.base import Base
from backend.app.models.site import Site
from backend.app.models.source import FoodProduct, SourceRecord
from backend.app.models.user import User


class Donation(Base):
    """One donor supply event with a pickup window and safety deadline."""

    __tablename__ = "donations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'listed', 'manual_review', 'hard_blocked', "
            "'collected', 'delivered')",
            name="ck_donations_status",
        ),
        CheckConstraint(
            "pickup_window_end > pickup_window_start",
            name="ck_donations_pickup_window",
        ),
        CheckConstraint(
            "safe_deadline > pickup_window_start",
            name="ck_donations_safe_deadline",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Internal identity for one donor supply event.",
    )
    source_site_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("sites.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Verified donor site where this supply event can be collected.",
    )
    created_by_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Business actor who created the donation listing.",
    )
    source_record_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_records.id", ondelete="RESTRICT"),
        nullable=True,
        comment="Optional external source provenance; not the donation identity.",
    )
    pickup_window_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Inclusive earliest collection time.",
    )
    pickup_window_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Exclusive latest collection time.",
    )
    safe_deadline: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Latest safe delivery target used by future feasibility checks.",
    )
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="draft",
        server_default="draft",
        comment="Current success-path state; detailed history is append-only events.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        comment="When the donation aggregate was created.",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=func.now(),
        comment="When current donation fields were last changed.",
    )

    source_site: Mapped[Site] = relationship()
    created_by_user: Mapped[User] = relationship()
    source_record: Mapped[SourceRecord | None] = relationship()
    items: Mapped[list["DonationItem"]] = relationship(
        back_populates="donation",
        passive_deletes=True,
    )
    status_events: Mapped[list["DonationStatusEvent"]] = relationship(
        back_populates="donation",
        passive_deletes=True,
    )


class DonationItem(Base):
    """A food line with immutable facts copied from the current product identity."""

    __tablename__ = "donation_items"
    __table_args__ = (
        CheckConstraint(
            "line_number > 0",
            name="ck_donation_items_line_number",
        ),
        CheckConstraint(
            "quantity > 0",
            name="ck_donation_items_quantity_positive",
        ),
        CheckConstraint(
            "quantity_unit IN ('kg', 'g', 'unit', 'case', 'box', 'crate', 'litre', 'ml')",
            name="ck_donation_items_quantity_unit",
        ),
        CheckConstraint(
            "storage_class IN ('ambient', 'chilled', 'frozen', 'unknown')",
            name="ck_donation_items_storage_class",
        ),
        CheckConstraint(
            "date_mark_type IN ('use_by', 'best_before', 'packed_on', 'none', 'unknown')",
            name="ck_donation_items_date_mark_type",
        ),
        CheckConstraint(
            "date_mark_type IN ('none', 'unknown') OR date_mark IS NOT NULL",
            name="ck_donation_items_date_mark_value",
        ),
        CheckConstraint(
            "packaging_condition IN ('sealed', 'opened', 'damaged', 'unknown')",
            name="ck_donation_items_packaging_condition",
        ),
        CheckConstraint(
            "recall_status IN ('not_checked', 'not_recalled', 'recalled')",
            name="ck_donation_items_recall_status",
        ),
        UniqueConstraint(
            "donation_id",
            "line_number",
            name="uq_donation_items_line_number",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Internal identity for this donation line; not a GTIN.",
    )
    donation_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("donations.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Donation batch containing this line.",
    )
    line_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Stable line number within this donation submission.",
    )
    food_product_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("food_products.id", ondelete="RESTRICT"),
        nullable=True,
        comment="Optional reusable product identity; no-barcode lines leave this NULL.",
    )
    product_name_snapshot: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Product name at listing time; not overwritten by product master changes.",
    )
    brand_snapshot: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Brand at listing time, if known.",
    )
    variant_snapshot: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Size/flavour/variant at listing time, if known.",
    )
    gtin_snapshot: Mapped[str | None] = mapped_column(
        String(14),
        nullable=True,
        comment="Optional GTIN copied into the historical item snapshot.",
    )
    lot_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Lot or batch mark for this physical food line, if known.",
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 3),
        nullable=False,
        comment="Quantity offered in the declared unit; initial item is not split in this slice.",
    )
    quantity_unit: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="Controlled quantity unit; conversions are not implied by the schema.",
    )
    storage_class: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="Required storage lane: ambient, chilled, frozen, or unknown.",
    )
    date_mark_type: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="Date meaning is separate from the date value.",
    )
    date_mark: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="Use-by, best-before, packed-on, or NULL when not applicable/known.",
    )
    packaging_condition: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="unknown",
        server_default="unknown",
        comment="Listing-time packaging state; unsafe states are handled by future rules.",
    )
    recall_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="not_checked",
        server_default="not_checked",
        comment="Recall fact used by a future non-overridable eligibility rule.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        comment="When this donation line was created.",
    )

    donation: Mapped[Donation] = relationship(back_populates="items")
    food_product: Mapped[FoodProduct | None] = relationship()
    condition_observations: Mapped[list["FoodConditionObservation"]] = relationship(
        back_populates="donation_item",
        passive_deletes=True,
    )


class FoodConditionObservation(Base):
    """An append-only condition observation at a selected operational checkpoint."""

    __tablename__ = "food_condition_observations"
    __table_args__ = (
        CheckConstraint(
            "checkpoint IN ('listing', 'pickup', 'delivery')",
            name="ck_food_condition_observations_checkpoint",
        ),
        CheckConstraint(
            "condition_status IN ('acceptable', 'manual_review', 'unsafe', 'unknown')",
            name="ck_food_condition_observations_condition_status",
        ),
        CheckConstraint(
            "temperature_celsius IS NULL OR temperature_celsius BETWEEN -100 AND 100",
            name="ck_food_condition_observations_temperature_range",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Internal identity for one observed condition fact.",
    )
    donation_item_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("donation_items.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Food line whose condition was observed.",
    )
    observed_by_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Actor responsible for recording this observation.",
    )
    checkpoint: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="Operational checkpoint: listing, pickup, or delivery.",
    )
    condition_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="Observation outcome used by future safety evaluation.",
    )
    temperature_celsius: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Observed temperature when relevant; NULL means not measured.",
    )
    notes: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Short operational observation; not a replacement for controlled status.",
    )
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="When the condition was observed.",
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        comment="When FoodFlow recorded the observation.",
    )

    donation_item: Mapped[DonationItem] = relationship(back_populates="condition_observations")
    observed_by_user: Mapped[User] = relationship()


class DonationStatusEvent(Base):
    """Append-only first-slice success-path history for a donation aggregate."""

    __tablename__ = "donation_status_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('created', 'listed', 'manual_review', 'hard_blocked', "
            "'collected', 'delivered')",
            name="ck_donation_status_events_type",
        ),
        CheckConstraint(
            "actor_type IN ('user', 'system')",
            name="ck_donation_status_events_actor_type",
        ),
        CheckConstraint(
            "(actor_type = 'user' AND actor_user_id IS NOT NULL) "
            "OR (actor_type = 'system' AND actor_user_id IS NULL)",
            name="ck_donation_status_events_actor_reference",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Internal append-only event identity.",
    )
    donation_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("donations.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Donation aggregate whose state history is recorded.",
    )
    event_type: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        comment="Success-path transition or review event.",
    )
    actor_type: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        default="user",
        server_default="user",
        comment="Whether the event was recorded by a user or deterministic system rule.",
    )
    actor_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
        comment="User actor when actor_type is user; NULL for system events.",
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="When the business event occurred.",
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        comment="When the event was recorded.",
    )
    notes: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Optional event context; failure-specific reason fields are deferred.",
    )

    donation: Mapped[Donation] = relationship(back_populates="status_events")
    actor_user: Mapped[User | None] = relationship()
