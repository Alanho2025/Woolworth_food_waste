"""Deterministic matching evidence, human decisions, and allocation state."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
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
from backend.app.models.site import Site
from backend.app.models.supply import DonationItem
from backend.app.models.user import User


class MatchRun(Base):
    """One versioned matching execution for one donation item."""

    __tablename__ = "match_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('started', 'completed', 'no_feasible_candidates', 'manual_review')",
            name="ck_match_runs_status",
        ),
        CheckConstraint(
            "completed_at IS NULL OR completed_at >= started_at",
            name="ck_match_runs_completion_time",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Internal identity for one matching execution.",
    )
    donation_item_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("donation_items.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Donation item being matched in this run.",
    )
    requested_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
        comment="Optional human initiator; system-triggered runs may have NULL.",
    )
    policy_version: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Deterministic feasibility and priority policy version.",
    )
    model_identifier: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="Optional agent/model identifier used only for candidate ranking.",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="started",
        server_default="started",
        comment="Run state; no candidate is an allocation by itself.",
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        comment="When the matching run began.",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the matching run reached a result state.",
    )

    donation_item: Mapped[DonationItem] = relationship()
    requested_by_user: Mapped[User | None] = relationship()
    candidates: Mapped[list["MatchCandidate"]] = relationship(
        back_populates="match_run",
        passive_deletes=True,
    )


class MatchCandidate(Base):
    """A recipient candidate with hard-feasibility and ranking evidence."""

    __tablename__ = "match_candidates"
    __table_args__ = (
        CheckConstraint(
            "feasibility_status IN ('feasible', 'infeasible', 'manual_review')",
            name="ck_match_candidates_feasibility_status",
        ),
        CheckConstraint(
            "agent_rank IS NULL OR agent_rank > 0",
            name="ck_match_candidates_agent_rank",
        ),
        UniqueConstraint(
            "match_run_id",
            "recipient_site_id",
            name="uq_match_candidates_run_site",
        ),
        UniqueConstraint(
            "id",
            "recipient_site_id",
            name="uq_match_candidates_id_site",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Internal identity for one recipient candidate result.",
    )
    match_run_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("match_runs.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Matching run that evaluated this candidate.",
    )
    recipient_site_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("sites.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Recipient site evaluated for the donation item.",
    )
    feasibility_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="Deterministic result before agent ranking.",
    )
    reason_code: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Stable explanation code for feasible or excluded result.",
    )
    reason_components: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
        comment="Structured safety, capacity, need, ETA, and distance evidence.",
    )
    agent_rank: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Agent rank among feasible candidates; NULL for excluded candidates.",
    )
    priority_score: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 6),
        nullable=True,
        comment="Optional reproducible ranking score; not a hidden authority decision.",
    )
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        comment="When the candidate facts were evaluated.",
    )

    match_run: Mapped[MatchRun] = relationship(back_populates="candidates")
    recipient_site: Mapped[Site] = relationship()
    decisions: Mapped[list["MatchDecision"]] = relationship(
        back_populates="match_candidate",
        passive_deletes=True,
    )


class MatchDecision(Base):
    """A separate driver, coordinator, or recipient decision on one candidate."""

    __tablename__ = "match_decisions"
    __table_args__ = (
        CheckConstraint(
            "decision_type IN ('driver_confirmation', 'coordinator_exception', "
            "'recipient_acceptance')",
            name="ck_match_decisions_type",
        ),
        CheckConstraint(
            "(decision_type = 'driver_confirmation' AND decision IN ('confirmed', 'rejected')) "
            "OR (decision_type = 'coordinator_exception' AND decision IN ('approved', 'rejected')) "
            "OR (decision_type = 'recipient_acceptance' AND decision IN ('accepted', 'declined'))",
            name="ck_match_decisions_value",
        ),
        UniqueConstraint(
            "match_candidate_id",
            "decision_type",
            name="uq_match_decisions_candidate_type",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Internal identity for one human decision fact.",
    )
    match_candidate_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("match_candidates.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Candidate on which the actor made this decision.",
    )
    decision_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="Separates driver confirmation, coordinator exception, and recipient response.",
    )
    decision: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="Decision value constrained by decision_type.",
    )
    actor_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Actor responsible for the decision; role is checked by future service logic.",
    )
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        comment="When the business decision was made.",
    )
    comment: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Optional human explanation; hard safety blocks cannot be overridden here.",
    )

    match_candidate: Mapped[MatchCandidate] = relationship(back_populates="decisions")
    actor_user: Mapped[User] = relationship()


class Allocation(Base):
    """A single-recipient reservation, confirmation, or fulfilled allocation."""

    __tablename__ = "allocations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('reserved', 'confirmed', 'fulfilled')",
            name="ck_allocations_status",
        ),
        CheckConstraint(
            "allocated_quantity > 0",
            name="ck_allocations_quantity_positive",
        ),
        CheckConstraint(
            "quantity_unit IN ('kg', 'g', 'unit', 'case', 'box', 'crate', 'litre', 'ml')",
            name="ck_allocations_quantity_unit",
        ),
        CheckConstraint(
            "(status = 'reserved' AND confirmed_at IS NULL AND fulfilled_at IS NULL) "
            "OR (status = 'confirmed' AND confirmed_at IS NOT NULL AND fulfilled_at IS NULL) "
            "OR (status = 'fulfilled' AND confirmed_at IS NOT NULL AND fulfilled_at IS NOT NULL)",
            name="ck_allocations_status_timestamps",
        ),
        ForeignKeyConstraint(
            ["match_candidate_id", "recipient_site_id"],
            ["match_candidates.id", "match_candidates.recipient_site_id"],
            ondelete="RESTRICT",
            name="fk_allocations_candidate_recipient_site",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Internal identity for one recipient allocation history.",
    )
    donation_item_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("donation_items.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Donation item reserved for one recipient in this success slice.",
    )
    recipient_site_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("sites.id", ondelete="RESTRICT"),
        nullable=False,
        comment="One recipient site for the initial non-split allocation.",
    )
    match_candidate_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        comment="Candidate confirmed before this allocation was reserved.",
    )
    allocated_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 3),
        nullable=False,
        comment="Allocated quantity in the declared unit; initial item is not split.",
    )
    quantity_unit: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="Unit of allocated_quantity.",
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="reserved",
        server_default="reserved",
        comment="Success-path allocation state; release/failure states are deferred.",
    )
    reserved_by_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Driver or authorised actor who created the reservation.",
    )
    reserved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        comment="When the reservation was created.",
    )
    confirmed_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
        comment="Recipient responder who accepted the reservation.",
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When recipient acceptance changed the reservation to confirmed.",
    )
    fulfilled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the successful delivery fulfilment was recorded.",
    )

    donation_item: Mapped[DonationItem] = relationship()
    recipient_site: Mapped[Site] = relationship()
    match_candidate: Mapped[MatchCandidate] = relationship(overlaps="recipient_site")
    reserved_by_user: Mapped[User] = relationship(foreign_keys=[reserved_by_user_id])
    confirmed_by_user: Mapped[User | None] = relationship(foreign_keys=[confirmed_by_user_id])
    status_events: Mapped[list["AllocationStatusEvent"]] = relationship(
        back_populates="allocation",
        passive_deletes=True,
    )


Index(
    "uq_allocations_active_item",
    Allocation.donation_item_id,
    unique=True,
    postgresql_where=Allocation.status.in_(
        ("reserved", "confirmed"),
    ),
)


class AllocationStatusEvent(Base):
    """Append-only success-path allocation state history."""

    __tablename__ = "allocation_status_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('reserved', 'confirmed', 'fulfilled')",
            name="ck_allocation_status_events_type",
        ),
        CheckConstraint(
            "actor_type IN ('user', 'system')",
            name="ck_allocation_status_events_actor_type",
        ),
        CheckConstraint(
            "(actor_type = 'user' AND actor_user_id IS NOT NULL) "
            "OR (actor_type = 'system' AND actor_user_id IS NULL)",
            name="ck_allocation_status_events_actor_reference",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Internal append-only allocation event identity.",
    )
    allocation_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("allocations.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Allocation whose state history is recorded.",
    )
    event_type: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="Reserved, confirmed, or fulfilled success-path event.",
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
        comment="When the allocation event occurred.",
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
        comment="Optional success-path context; failure-specific reasons are deferred.",
    )

    allocation: Mapped[Allocation] = relationship(back_populates="status_events")
    actor_user: Mapped[User | None] = relationship()


def confirmed_allocation_statement() -> Select[tuple[Allocation]]:
    """Return only confirmed allocations eligible for future route planning."""

    return select(Allocation).where(Allocation.status == "confirmed")
