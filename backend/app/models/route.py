"""Route planning inputs, proposals, human decisions, and delivery execution."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import Select
from sqlalchemy.types import Uuid

from backend.app.models.base import Base
from backend.app.models.matching import Allocation
from backend.app.models.site import Site, SiteLocation
from backend.app.models.source import SourceRecord
from backend.app.models.user import User


class RoutePlanningRun(Base):
    """One bounded planning session for one driver."""

    __tablename__ = "route_planning_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('started', 'proposal_ready', 'approved', 'committed')",
            name="ck_route_planning_runs_status",
        ),
        CheckConstraint(
            "planning_horizon_end > planning_horizon_start",
            name="ck_route_planning_runs_horizon",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Internal identity for one driver planning session.",
    )
    driver_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Driver whose bounded planning session is represented.",
    )
    planning_horizon_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Inclusive planning horizon start.",
    )
    planning_horizon_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Exclusive planning horizon end.",
    )
    planned_departure_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Departure time used when evaluating route feasibility.",
    )
    policy_version: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Approved route priority and feasibility policy version.",
    )
    model_identifier: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="Optional agent/model identifier; proposal is not a commitment.",
    )
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="started",
        server_default="started",
        comment="Planning state before a human commits a delivery.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        comment="When the planning run was created.",
    )

    driver: Mapped[User] = relationship()
    input_snapshots: Mapped[list["RouteInputSnapshot"]] = relationship(
        back_populates="route_planning_run",
        passive_deletes=True,
    )
    proposals: Mapped[list["RouteProposal"]] = relationship(
        back_populates="route_planning_run",
        passive_deletes=True,
    )


class RouteInputSnapshot(Base):
    """Immutable route input with provider, observation, validity, and payload."""

    __tablename__ = "route_input_snapshots"
    __table_args__ = (
        CheckConstraint(
            "input_kind IN ('traffic', 'road', 'weather', 'eta', 'allocation', "
            "'condition', 'capacity', 'location')",
            name="ck_route_input_snapshots_kind",
        ),
        CheckConstraint(
            "valid_until IS NULL OR valid_until > valid_from",
            name="ck_route_input_snapshots_valid_period",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Internal identity for one immutable route input snapshot.",
    )
    route_planning_run_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("route_planning_runs.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Planning run that captured this input.",
    )
    input_kind: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="Traffic, road, weather, ETA, or operational state input kind.",
    )
    provider: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Provider or source name; exact provider contract is future integration data.",
    )
    coverage_reference: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Road segment, area, route, allocation, or site covered by this snapshot.",
    )
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="When the provider/source observed the input.",
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        comment="When FoodFlow recorded the input snapshot.",
    )
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Inclusive input validity start.",
    )
    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Exclusive validity end; NULL means provider supplied no explicit end.",
    )
    payload: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
        comment="Provider response snapshot needed to reconstruct the proposal input.",
    )
    source_record_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_records.id", ondelete="RESTRICT"),
        nullable=True,
        comment="Optional provenance record for this external input.",
    )

    route_planning_run: Mapped[RoutePlanningRun] = relationship(
        back_populates="input_snapshots",
    )
    source_record: Mapped[SourceRecord | None] = relationship()


class RouteProposal(Base):
    """An agent-generated ordered route proposal that is not yet committed."""

    __tablename__ = "route_proposals"
    __table_args__ = (
        CheckConstraint(
            "proposal_status IN ('draft', 'superseded', 'selected')",
            name="ck_route_proposals_status",
        ),
        CheckConstraint(
            "version > 0",
            name="ck_route_proposals_version",
        ),
        CheckConstraint(
            "total_travel_seconds IS NULL OR total_travel_seconds >= 0",
            name="ck_route_proposals_travel_seconds",
        ),
        CheckConstraint(
            "total_distance_meters IS NULL OR total_distance_meters >= 0",
            name="ck_route_proposals_distance",
        ),
        UniqueConstraint(
            "route_planning_run_id",
            "version",
            name="uq_route_proposals_run_version",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Internal identity for one proposal version.",
    )
    route_planning_run_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("route_planning_runs.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Planning run that produced this proposal.",
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Monotonic proposal version within a planning run.",
    )
    proposal_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="draft",
        server_default="draft",
        comment="Draft/superseded/selected; selected still requires a human decision.",
    )
    proposal_payload: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
        comment="Ordered stops and route structure proposed by the agent.",
    )
    priority_reasons: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
        comment="Structured priority reasons; distance cannot be the sole decision.",
    )
    cost_components: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
        comment="Travel, ETA, weather, road, and other explainable cost components.",
    )
    total_travel_seconds: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Estimated total travel duration from the captured inputs.",
    )
    total_distance_meters: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2),
        nullable=True,
        comment="Estimated total distance; a low-priority efficiency factor.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        comment="When the proposal was generated.",
    )

    route_planning_run: Mapped[RoutePlanningRun] = relationship(
        back_populates="proposals",
    )
    decisions: Mapped[list["RouteDecision"]] = relationship(
        back_populates="route_proposal",
        passive_deletes=True,
    )


class RouteDecision(Base):
    """A human decision that separates proposal from committed delivery."""

    __tablename__ = "route_decisions"
    __table_args__ = (
        CheckConstraint(
            "decision_type IN ('driver_confirmation', 'coordinator_exception')",
            name="ck_route_decisions_type",
        ),
        CheckConstraint(
            "decision IN ('approved', 'rejected')",
            name="ck_route_decisions_value",
        ),
        UniqueConstraint(
            "route_proposal_id",
            "decision_type",
            name="uq_route_decisions_proposal_type",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Internal identity for one route decision fact.",
    )
    route_proposal_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("route_proposals.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Proposal on which the human decision was made.",
    )
    decision_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="Driver confirmation or coordinator exception decision.",
    )
    decision: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="Approved or rejected; no agent decision commits a route.",
    )
    actor_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Human actor responsible for committing or rejecting the proposal.",
    )
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        comment="When the route decision was made.",
    )
    comment: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Optional human explanation.",
    )

    route_proposal: Mapped[RouteProposal] = relationship(back_populates="decisions")
    actor_user: Mapped[User] = relationship()


class Delivery(Base):
    """A human-approved driver delivery execution."""

    __tablename__ = "deliveries"
    __table_args__ = (
        CheckConstraint(
            "status IN ('assigned', 'started', 'completed')",
            name="ck_deliveries_status",
        ),
        CheckConstraint(
            "(status = 'assigned' AND started_at IS NULL AND completed_at IS NULL) "
            "OR (status = 'started' AND started_at IS NOT NULL AND completed_at IS NULL) "
            "OR (status = 'completed' AND started_at IS NOT NULL AND completed_at IS NOT NULL)",
            name="ck_deliveries_status_timestamps",
        ),
        UniqueConstraint(
            "route_decision_id",
            name="uq_deliveries_route_decision",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Internal identity for one committed delivery job.",
    )
    route_decision_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("route_decisions.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Approved route decision that committed this delivery.",
    )
    driver_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Driver executing the approved delivery.",
    )
    planned_departure_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Departure time from the committed route plan.",
    )
    committed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        comment="When the approved route became a delivery job.",
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="assigned",
        server_default="assigned",
        comment="Success-path execution state; failed/cancelled states are deferred.",
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the driver started the delivery.",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When successful delivery completion was recorded.",
    )

    route_decision: Mapped[RouteDecision] = relationship()
    driver: Mapped[User] = relationship()
    stops: Mapped[list["DeliveryStop"]] = relationship(
        back_populates="delivery",
        passive_deletes=True,
    )
    allocations: Mapped[list["DeliveryAllocation"]] = relationship(
        back_populates="delivery",
        passive_deletes=True,
    )
    status_events: Mapped[list["DeliveryStatusEvent"]] = relationship(
        back_populates="delivery",
        passive_deletes=True,
    )


class DeliveryStop(Base):
    """An approved stop with planned and actual order/time fields."""

    __tablename__ = "delivery_stops"
    __table_args__ = (
        CheckConstraint(
            "stop_type IN ('pickup', 'delivery', 'cross_dock')",
            name="ck_delivery_stops_type",
        ),
        CheckConstraint(
            "status IN ('planned', 'in_progress', 'completed')",
            name="ck_delivery_stops_status",
        ),
        CheckConstraint(
            "stop_sequence > 0",
            name="ck_delivery_stops_sequence",
        ),
        CheckConstraint(
            "actual_sequence IS NULL OR actual_sequence > 0",
            name="ck_delivery_stops_actual_sequence",
        ),
        CheckConstraint(
            "window_end IS NULL OR window_start IS NOT NULL AND window_end > window_start",
            name="ck_delivery_stops_window",
        ),
        CheckConstraint(
            "actual_departure_at IS NULL OR actual_arrival_at IS NOT NULL "
            "AND actual_departure_at >= actual_arrival_at",
            name="ck_delivery_stops_actual_times",
        ),
        ForeignKeyConstraint(
            ["site_location_id", "site_id"],
            ["site_locations.id", "site_locations.site_id"],
            ondelete="RESTRICT",
            name="fk_delivery_stops_location_site",
        ),
        UniqueConstraint(
            "delivery_id",
            "stop_sequence",
            name="uq_delivery_stops_sequence",
        ),
        UniqueConstraint(
            "delivery_id",
            "id",
            name="uq_delivery_stops_delivery_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Internal identity for one delivery stop.",
    )
    delivery_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("deliveries.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Committed delivery containing this stop.",
    )
    stop_sequence: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Approved route order; never overwritten by actual order.",
    )
    actual_sequence: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Observed order when it differs from the approved plan.",
    )
    stop_type: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="Pickup, delivery, or approved cross-dock stop.",
    )
    site_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("sites.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Operational site for this stop.",
    )
    site_location_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        comment="Exact approved operational location used by navigation.",
    )
    window_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Optional stop receiving/collection window start.",
    )
    window_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Optional stop receiving/collection window end.",
    )
    planned_arrival_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Planned arrival time from the committed route.",
    )
    planned_departure_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Planned departure time from the committed route.",
    )
    actual_arrival_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Actual arrival time recorded by the driver.",
    )
    actual_departure_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Actual departure time recorded by the driver.",
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="planned",
        server_default="planned",
        comment="Success-path stop state; failed stop behavior is deferred.",
    )
    result_note: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Short successful-stop note; failure reasons are deferred.",
    )

    delivery: Mapped[Delivery] = relationship(back_populates="stops")
    site: Mapped[Site] = relationship()
    site_location: Mapped[SiteLocation] = relationship(overlaps="site")


class DeliveryAllocation(Base):
    """Junction linking one committed delivery to its allocations and stops."""

    __tablename__ = "delivery_allocations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["delivery_id", "pickup_stop_id"],
            ["delivery_stops.delivery_id", "delivery_stops.id"],
            ondelete="RESTRICT",
            name="fk_delivery_allocations_pickup_stop",
        ),
        ForeignKeyConstraint(
            ["delivery_id", "delivery_stop_id"],
            ["delivery_stops.delivery_id", "delivery_stops.id"],
            ondelete="RESTRICT",
            name="fk_delivery_allocations_delivery_stop",
        ),
        UniqueConstraint(
            "delivery_id",
            "allocation_id",
            name="uq_delivery_allocations_delivery_allocation",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Internal identity for one delivery/allocation junction row.",
    )
    delivery_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("deliveries.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Committed delivery carrying the allocation.",
    )
    allocation_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("allocations.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Confirmed allocation included in this delivery.",
    )
    pickup_stop_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        comment="Pickup stop for this allocation.",
    )
    delivery_stop_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        comment="Delivery stop for this allocation.",
    )

    delivery: Mapped[Delivery] = relationship(back_populates="allocations")
    allocation: Mapped[Allocation] = relationship()
    pickup_stop: Mapped[DeliveryStop] = relationship(foreign_keys=[pickup_stop_id])
    delivery_stop: Mapped[DeliveryStop] = relationship(foreign_keys=[delivery_stop_id])


class DeliveryStatusEvent(Base):
    """Append-only success-path delivery and stop event."""

    __tablename__ = "delivery_status_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('assigned', 'started', 'arrived', 'collected', "
            "'delivered', 'completed')",
            name="ck_delivery_status_events_type",
        ),
        CheckConstraint(
            "actor_type IN ('user', 'system')",
            name="ck_delivery_status_events_actor_type",
        ),
        CheckConstraint(
            "(actor_type = 'user' AND actor_user_id IS NOT NULL) "
            "OR (actor_type = 'system' AND actor_user_id IS NULL)",
            name="ck_delivery_status_events_actor_reference",
        ),
        ForeignKeyConstraint(
            ["delivery_id", "stop_id"],
            ["delivery_stops.delivery_id", "delivery_stops.id"],
            ondelete="RESTRICT",
            name="fk_delivery_status_events_delivery_stop",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Internal append-only delivery event identity.",
    )
    delivery_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("deliveries.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Delivery aggregate whose event is recorded.",
    )
    stop_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
        comment="Optional stop-specific event; NULL means delivery-level event.",
    )
    event_type: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="Success-path delivery or stop event type.",
    )
    actor_type: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        default="user",
        server_default="user",
        comment="Whether the event was recorded by a user or system rule.",
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
        comment="When the delivery event occurred.",
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
        comment="Optional successful-stop context; failure-specific reasons are deferred.",
    )

    delivery: Mapped[Delivery] = relationship(back_populates="status_events")
    stop: Mapped[DeliveryStop | None] = relationship(
        overlaps="delivery,status_events",
    )
    actor_user: Mapped[User | None] = relationship()


def confirmed_delivery_statement() -> Select[tuple[Delivery]]:
    """Return delivery jobs that are in the committed success-path states."""

    return select(Delivery).where(Delivery.status.in_(("assigned", "started", "completed")))
