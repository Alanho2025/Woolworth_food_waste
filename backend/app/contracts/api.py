"""Frozen public API contracts for the P2 frontend hand-off.

These are Pydantic transport models only. They deliberately import neither
FastAPI nor SQLAlchemy, and no ORM row is ever exposed through this surface.
P4 will bind these models to routes without changing their public shape.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StrictInt, model_validator

from backend.app.contracts.core import (
    AgentStateEvent,
    AllocationDecision,
    CommunityOrganisation,
    DeliveryOrder,
    DeliveryStatus,
    DonationInventory,
    DonationRequest,
    Driver,
    FoodItem,
    RematchDecision,
    TimeWindow,
)
from backend.app.domain.errors import ErrorCode


class _ApiModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class AgentRunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class AgentRunKind(StrEnum):
    INITIAL = "initial"
    REMATCH = "rematch"


class AgentRunTransport(StrEnum):
    LIVE = "live"
    REPLAY = "replay"


class DeliveryAcceptanceOutcome(StrEnum):
    FULL = "full"
    PARTIAL = "partial"
    REJECTED = "rejected"


class CreateDonationRequest(_ApiModel):
    """Donation form payload; the backend mints the authoritative donation ID.

    ``donation_id`` remains an optional preview-only reference so the JSON
    example in Requirement.md section 4 still validates. The create use case
    must never treat it as the authoritative persisted identifier.
    ``store_location`` is resolved from the configured store record.
    """

    donation_id: str | None = Field(default=None, min_length=1)
    store_id: str = Field(min_length=1)
    pickup_window: TimeWindow
    items: list[FoodItem] = Field(min_length=1)
    handling_notes: str = ""


class CreateDonationResponse(_ApiModel):
    donation: DonationRequest
    inventory: DonationInventory


class StartMatchResponse(_ApiModel):
    """Immediate 202 response; the run continues after this is returned."""

    run_id: str = Field(min_length=1)
    donation_id: str = Field(min_length=1)
    status: Literal[AgentRunStatus.QUEUED] = AgentRunStatus.QUEUED
    kind: AgentRunKind
    transport: AgentRunTransport


class InitialAgentRunResult(_ApiModel):
    kind: Literal[AgentRunKind.INITIAL] = AgentRunKind.INITIAL
    decision: AllocationDecision
    inventory: DonationInventory
    order_refs: list[str] = Field(min_length=1)


class RematchAgentRunResult(_ApiModel):
    kind: Literal[AgentRunKind.REMATCH] = AgentRunKind.REMATCH
    decision: RematchDecision
    inventory: DonationInventory
    order_refs: list[str] = Field(min_length=1)


AgentRunResult = Annotated[
    InitialAgentRunResult | RematchAgentRunResult,
    Field(discriminator="kind"),
]


class AgentRunResponse(_ApiModel):
    """Incrementally readable Agent run, safe to poll while still running."""

    run_id: str = Field(min_length=1)
    donation_id: str = Field(min_length=1)
    status: AgentRunStatus
    kind: AgentRunKind
    transport: AgentRunTransport
    started_at: AwareDatetime | None = None
    completed_at: AwareDatetime | None = None
    events: list[AgentStateEvent]
    result: AgentRunResult | None = None
    error_code: ErrorCode | None = None

    @model_validator(mode="after")
    def terminal_fields_match_status(self) -> AgentRunResponse:
        if self.status is AgentRunStatus.SUCCEEDED and self.result is None:
            raise ValueError("a succeeded Agent run requires a typed result")
        if self.status is AgentRunStatus.FAILED and self.error_code is None:
            raise ValueError("a failed Agent run requires an error code")
        if self.status in {AgentRunStatus.QUEUED, AgentRunStatus.RUNNING} and (
            self.result is not None or self.error_code is not None
        ):
            raise ValueError("a non-terminal Agent run cannot carry a result or error")
        if self.status is AgentRunStatus.QUEUED and (
            self.started_at is not None or self.completed_at is not None
        ):
            raise ValueError("a queued Agent run cannot have start or completion timestamps")
        if self.status is AgentRunStatus.RUNNING and (
            self.started_at is None or self.completed_at is not None
        ):
            raise ValueError("a running Agent run requires only a start timestamp")
        if self.status in {AgentRunStatus.SUCCEEDED, AgentRunStatus.FAILED} and (
            self.started_at is None or self.completed_at is None
        ):
            raise ValueError("a terminal Agent run requires start and completion timestamps")
        if (
            self.started_at is not None
            and self.completed_at is not None
            and self.completed_at < self.started_at
        ):
            raise ValueError("Agent run completion cannot precede its start")
        if self.result is not None and self.result.kind is not self.kind:
            raise ValueError("Agent run kind and result kind must agree")
        return self


class DeliveryStatusEvent(_ApiModel):
    sequence: Annotated[StrictInt, Field(ge=0)]
    status: DeliveryStatus
    label: str = Field(min_length=1)
    occurred_at: AwareDatetime


class DeliveryDetailResponse(_ApiModel):
    order: DeliveryOrder
    donation: DonationRequest
    driver: Driver
    destination: CommunityOrganisation
    inventory: DonationInventory
    status: DeliveryStatus
    status_timeline: list[DeliveryStatusEvent]

    @model_validator(mode="after")
    def duplicated_status_matches_order(self) -> DeliveryDetailResponse:
        if self.status is not self.order.status:
            raise ValueError("delivery detail status must match order.status")
        return self


class ConfirmDeliveryRequest(_ApiModel):
    outcome: DeliveryAcceptanceOutcome
    accepted_kg: Annotated[StrictInt, Field(ge=0, description="Whole kilograms")]
    reason: str = ""

    @model_validator(mode="after")
    def outcome_matches_quantity_and_reason(self) -> ConfirmDeliveryRequest:
        if self.outcome is DeliveryAcceptanceOutcome.REJECTED and self.accepted_kg != 0:
            raise ValueError("a rejected delivery must accept zero kilograms")
        if self.outcome is not DeliveryAcceptanceOutcome.REJECTED and self.accepted_kg == 0:
            raise ValueError("a full or partial acceptance must accept a positive quantity")
        if self.outcome is not DeliveryAcceptanceOutcome.FULL and not self.reason.strip():
            raise ValueError("a partial or rejected delivery requires a reason")
        return self


class ConfirmDeliveryResponse(_ApiModel):
    delivery: DeliveryOrder
    outcome: DeliveryAcceptanceOutcome
    planned_kg: Annotated[StrictInt, Field(gt=0)]
    accepted_kg: Annotated[StrictInt, Field(ge=0)]
    remaining_kg: Annotated[StrictInt, Field(ge=0)]
    corrected_community: CommunityOrganisation
    inventory: DonationInventory
    rematch_run_id: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def rematch_presence_matches_remainder(self) -> ConfirmDeliveryResponse:
        if self.planned_kg != self.accepted_kg + self.remaining_kg:
            raise ValueError("planned kilograms must equal accepted plus remaining kilograms")
        if (self.remaining_kg > 0) != (self.rematch_run_id is not None):
            raise ValueError("exactly one rematch run is required when food remains")
        return self


class DashboardKpis(_ApiModel):
    active_surplus_kg: Annotated[StrictInt, Field(ge=0)]
    matched_kg: Annotated[StrictInt, Field(ge=0)]
    food_in_transit_kg: Annotated[StrictInt, Field(ge=0)]
    food_at_risk_kg: Annotated[StrictInt, Field(ge=0)]
    active_deliveries: Annotated[StrictInt, Field(ge=0)]
    community_demand_count: Annotated[StrictInt, Field(ge=0)]
    rescued_kg: Annotated[StrictInt, Field(ge=0)]
    active_donations: Annotated[StrictInt, Field(ge=0)]


class CapacityChangeAlert(_ApiModel):
    community_id: str
    community_name: str
    declared_capacity_kg: Annotated[StrictInt, Field(ge=0)]
    accepted_kg: Annotated[StrictInt, Field(ge=0)]
    message: str


class AgentRunSummary(_ApiModel):
    run_id: str
    donation_id: str
    status: AgentRunStatus
    kind: AgentRunKind
    transport: AgentRunTransport


class GlobalDashboardResponse(_ApiModel):
    """Global operations view; quantity ledgers remain donation-scoped."""

    kpis: DashboardKpis
    donations: list[DonationRequest]
    inventories: list[DonationInventory]
    deliveries: list[DeliveryOrder]
    communities: list[CommunityOrganisation]
    drivers: list[Driver]
    agent_runs: list[AgentRunSummary]
    capacity_alerts: list[CapacityChangeAlert]
    urgent_donation: DonationRequest | None = None
    active_agent_decision: AgentRunSummary | None = None
    active_delivery: DeliveryOrder | None = None
    capacity_change_highlight: CapacityChangeAlert | None = None


class ApiFieldError(_ApiModel):
    field: str
    message: str


class ApiErrorResponse(_ApiModel):
    code: ErrorCode
    detail: str
    retryable: bool = False
    field_errors: list[ApiFieldError] = Field(default_factory=list)
    run_id: str | None = None


class HealthResponse(_ApiModel):
    status: Literal["ok"] = "ok"
    service: Literal["foodflow-backend"] = "foodflow-backend"
