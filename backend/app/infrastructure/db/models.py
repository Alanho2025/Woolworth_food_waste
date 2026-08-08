"""SQLAlchemy 2 ORM models — persistence only.

These classes describe rows in SQLite and nothing else. They are never returned
from a repository, never serialised to the API, and never handed to the Agent;
the Pydantic contracts in `backend/app/contracts/core.py` do all of that
(clean_code_spec 4, 9). Keeping the two apart is what lets the storage shape
change — child tables for ordered lists, denormalised route columns — without
touching a single consumer.

Two persistence decisions are load-bearing and deliberate:

* **No surrogate autoincrement keys anywhere.** Every table has a natural or
  composite primary key. `python -m backend.app.seed.seed` must produce a
  byte-identical database on a second run, and AUTOINCREMENT would add a
  drifting `sqlite_sequence` row to the dump.
* **Ordered lists are child tables with an explicit `ordinal`,** not JSON blobs,
  so `accepted_categories` and `needs` come back in the order they were seeded
  rather than in whatever order SQLite happens to return.

Enumerations are stored as their plain string values rather than as SQL ENUMs.
`StrEnum` members round-trip losslessly through `str`, and a text column keeps
the dump readable and diffable during the demo.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    TypeDecorator,
)
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class UtcDateTime(TypeDecorator[datetime]):
    """A datetime column that is always timezone-aware UTC on both sides.

    SQLite has no native timestamp type and discards `tzinfo`, so a naive value
    comes back out of a plain `DateTime` column. Every receiving-window and
    deadline comparison in this product is a timezone-aware comparison against
    `Clock.now()` (domain/clock.py), and mixing a naive value into one of those
    raises `TypeError` at the exact moment the demo needs an answer. Normalising
    at the column boundary means no repository can forget.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(
        self,
        value: datetime | None,
        dialect: Dialect,  # noqa: ARG002 - required by the SQLAlchemy TypeDecorator API
    ) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("UtcDateTime requires a timezone-aware datetime")
        return value.astimezone(UTC)

    def process_result_value(
        self,
        value: datetime | None,
        dialect: Dialect,  # noqa: ARG002 - required by the SQLAlchemy TypeDecorator API
    ) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class Base(DeclarativeBase):
    """Declarative base for every persistence model."""


# --------------------------------------------------------------------------
# Donation
# --------------------------------------------------------------------------


class DonationRow(Base):
    __tablename__ = "donations"

    donation_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    store_id: Mapped[str] = mapped_column(String(32))
    store_name: Mapped[str] = mapped_column(String(128))
    store_latitude: Mapped[float] = mapped_column(Float)
    store_longitude: Mapped[float] = mapped_column(Float)
    pickup_window_start: Mapped[datetime] = mapped_column(UtcDateTime)
    pickup_window_end: Mapped[datetime] = mapped_column(UtcDateTime)
    handling_notes: Mapped[str] = mapped_column(Text, default="")


class DonationItemRow(Base):
    """One line of a donation. `ordinal` preserves the submitted order."""

    __tablename__ = "donation_items"

    donation_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("donations.donation_id"), primary_key=True
    )
    ordinal: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_name: Mapped[str] = mapped_column(String(128))
    category: Mapped[str] = mapped_column(String(32))
    quantity_kg: Mapped[int] = mapped_column(Integer)
    unit: Mapped[str] = mapped_column(String(8), default="kg")
    storage_type: Mapped[str] = mapped_column(String(16))
    delivery_deadline: Mapped[datetime] = mapped_column(UtcDateTime)


class DonationInventoryRow(Base):
    """The quantity ledger. The four components must always sum to `total_kg`.

    The invariant is a domain rule and is enforced in the domain and application
    layers; this table only stores the four numbers so the UI can render them as
    the stacked bar that clean_code_spec 8.4 requires as visible proof.
    """

    __tablename__ = "donation_inventory"

    donation_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("donations.donation_id"), primary_key=True
    )
    total_kg: Mapped[int] = mapped_column(Integer)
    available_kg: Mapped[int] = mapped_column(Integer)
    reserved_kg: Mapped[int] = mapped_column(Integer)
    in_transit_kg: Mapped[int] = mapped_column(Integer)
    delivered_kg: Mapped[int] = mapped_column(Integer)


# --------------------------------------------------------------------------
# Community
# --------------------------------------------------------------------------


class CommunityRow(Base):
    __tablename__ = "communities"

    community_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    location_name: Mapped[str] = mapped_column(String(128))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    # Latest stated maximum and the unreserved portion of that maximum.
    declared_capacity_kg: Mapped[int] = mapped_column(Integer)
    remaining_capacity_kg: Mapped[int] = mapped_column(Integer)
    receiving_window_start: Mapped[datetime] = mapped_column(UtcDateTime)
    receiving_window_end: Mapped[datetime] = mapped_column(UtcDateTime)
    is_open: Mapped[bool] = mapped_column(Boolean)


class CommunityCategoryRow(Base):
    """A food category this community accepts. Capacity, not need."""

    __tablename__ = "community_accepted_categories"

    community_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("communities.community_id"), primary_key=True
    )
    ordinal: Mapped[int] = mapped_column(Integer, primary_key=True)
    category: Mapped[str] = mapped_column(String(32))


class CommunityStorageRow(Base):
    """A storage type this community can hold. Capacity, not need."""

    __tablename__ = "community_supported_storage"

    community_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("communities.community_id"), primary_key=True
    )
    ordinal: Mapped[int] = mapped_column(Integer, primary_key=True)
    storage_type: Mapped[str] = mapped_column(String(16))


class CommunityNeedRow(Base):
    """What this community WANTS.

    Deliberately a separate table from what it can accept, because a community
    with urgent need and no capacity is exactly the case the product exists to
    make visible (Requirement.md 9).
    """

    __tablename__ = "community_needs"

    community_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("communities.community_id"), primary_key=True
    )
    ordinal: Mapped[int] = mapped_column(Integer, primary_key=True)
    category: Mapped[str] = mapped_column(String(32))
    level: Mapped[str] = mapped_column(String(16))


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------


class DriverRow(Base):
    __tablename__ = "drivers"

    driver_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    start_location_name: Mapped[str] = mapped_column(String(128))
    start_latitude: Mapped[float] = mapped_column(Float)
    start_longitude: Mapped[float] = mapped_column(Float)
    vehicle_capacity_kg: Mapped[int] = mapped_column(Integer)
    is_available: Mapped[bool] = mapped_column(Boolean)


# --------------------------------------------------------------------------
# Delivery
# --------------------------------------------------------------------------


class DeliveryOrderRow(Base):
    """One delivery leg, with its simulated route denormalised onto the row.

    `origin_*` is stored explicitly and is NOT assumed to be the donating store.
    The rematched leg departs from Community A where the driver is already
    standing; defaulting the origin to Mount Eden would draw a phantom return
    trip on Screen 6. See docs/assumption_audit.md C-4.
    """

    __tablename__ = "delivery_orders"

    order_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    donation_id: Mapped[str] = mapped_column(String(32), ForeignKey("donations.donation_id"))
    origin_name: Mapped[str] = mapped_column(String(128))
    origin_latitude: Mapped[float] = mapped_column(Float)
    origin_longitude: Mapped[float] = mapped_column(Float)
    destination_community_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("communities.community_id")
    )
    quantity_kg: Mapped[int] = mapped_column(Integer)
    driver_id: Mapped[str] = mapped_column(String(32), ForeignKey("drivers.driver_id"))
    status: Mapped[str] = mapped_column(String(32))
    deadline: Mapped[datetime] = mapped_column(UtcDateTime)
    is_rematch: Mapped[bool] = mapped_column(Boolean, default=False)

    # Simulated route. `route_simulated` is persisted rather than assumed so the
    # honesty label survives a round-trip (AGENTS_FoodFlow.md 2).
    route_destination_name: Mapped[str] = mapped_column(String(128))
    route_destination_latitude: Mapped[float] = mapped_column(Float)
    route_destination_longitude: Mapped[float] = mapped_column(Float)
    route_polyline: Mapped[list[list[float]]] = mapped_column(JSON)
    route_distance_km: Mapped[float] = mapped_column(Float)
    route_duration_minutes: Mapped[int] = mapped_column(Integer)
    route_eta: Mapped[datetime] = mapped_column(UtcDateTime)
    route_simulated: Mapped[bool] = mapped_column(Boolean, default=True)


class PartialAcceptanceRow(Base):
    """The original confirmation, retained independently of later ledger moves."""

    __tablename__ = "partial_acceptances"

    order_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("delivery_orders.order_id"), primary_key=True
    )
    donation_id: Mapped[str] = mapped_column(String(32), ForeignKey("donations.donation_id"))
    community_id: Mapped[str] = mapped_column(String(32), ForeignKey("communities.community_id"))
    planned_kg: Mapped[int] = mapped_column(Integer)
    accepted_kg: Mapped[int] = mapped_column(Integer)
    remaining_kg: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(Text, default="")
    recorded_at: Mapped[datetime] = mapped_column(UtcDateTime)


# --------------------------------------------------------------------------
# Agent run and audit
# --------------------------------------------------------------------------


class AgentRunRow(Base):
    __tablename__ = "agent_runs"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    donation_id: Mapped[str] = mapped_column(String(32))
    is_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)


class AgentRunEventRow(Base):
    """One visible state of an Agent run, written as it happens.

    Rows accumulate during the run so `GET /agent-runs/{id}` can return a
    growing list mid-flight; batching them until completion would put every
    state on screen after the decision it exists to explain.
    See docs/phase_review_findings.md R-2.
    """

    __tablename__ = "agent_run_events"

    run_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("agent_runs.run_id"), primary_key=True
    )
    sequence: Mapped[int] = mapped_column(Integer, primary_key=True)
    state: Mapped[str] = mapped_column(String(48))
    label: Mapped[str] = mapped_column(String(160))
    detail: Mapped[str] = mapped_column(Text, default="")
    occurred_at: Mapped[datetime] = mapped_column(UtcDateTime)


class AuditEventRow(Base):
    __tablename__ = "audit_events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    donation_id: Mapped[str] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(64))
    detail: Mapped[str] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(UtcDateTime)
    succeeded: Mapped[bool] = mapped_column(Boolean)


# Deletion order for a clean re-seed: children before parents.
# `backend/app/seed/seed.py` walks this to make re-seeding idempotent, and it is
# defined here because it is a property of the schema, not of the demo data.
DELETE_ORDER: tuple[type[Base], ...] = (
    AgentRunEventRow,
    AgentRunRow,
    AuditEventRow,
    PartialAcceptanceRow,
    DeliveryOrderRow,
    DonationItemRow,
    DonationInventoryRow,
    DonationRow,
    CommunityNeedRow,
    CommunityStorageRow,
    CommunityCategoryRow,
    CommunityRow,
    DriverRow,
)
