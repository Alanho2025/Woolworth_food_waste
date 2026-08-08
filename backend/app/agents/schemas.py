"""Typed input and output schemas for the eighteen Agent tools.

clean_code_spec 7.3 requires prompts, tool schemas, and output schemas to be
centrally managed under `backend/app/agents/`. Every tool returns one of these
models; nothing returns a bare dictionary, because an untyped core dictionary is
a blocker smell (clean_code_spec 9).

Model output is untrusted until it passes schema validation, hard-constraint
validation, current-state validation, and transaction validation. These models
are stage one; the domain policies are stage two; the application services are
stages three and four.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from backend.app.contracts.core import (
    CandidateAssessment,
    CommunityNeed,
    DeliveryOrder,
    DonationInventory,
    DonationRequest,
    Driver,
    RouteLeg,
    TimeWindow,
)
from backend.app.domain.errors import ErrorCode


class _ToolResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ToolFailure(_ToolResult):
    """Every tool failure the Agent sees, in one shape.

    AGENTS_FoodFlow.md 9 requires tool failures to be distinguishable as
    validation failure, not found, timeout, rate limited, invalid result, or
    internal failure -- so the code travels with the message and the Agent never
    has to parse an exception string to decide what to do next.
    """

    ok: bool = False
    code: ErrorCode
    detail: str


class DonationView(_ToolResult):
    donation: DonationRequest
    inventory: DonationInventory


class CandidateListResult(_ToolResult):
    """Complete facts for EVERY community, excluded ones included (R-18)."""

    required_kg: int
    candidates: list[CandidateAssessment]


class CommunityCapacityView(_ToolResult):
    """Need and capacity, kept deliberately separate (Requirement.md 9)."""

    community_id: str
    name: str
    needs: list[CommunityNeed]
    remaining_capacity_kg: int
    receiving_window: TimeWindow
    is_open: bool


class DriverListResult(_ToolResult):
    quantity_kg: int
    drivers: list[Driver]


class RouteResult(_ToolResult):
    route: RouteLeg


class ValidationResult(_ToolResult):
    """The answer to one hard-constraint question.

    `ok=False` is a business outcome, not an error: the Agent is expected to use
    it to exclude a candidate and carry on.
    """

    ok: bool
    code: ErrorCode | None = None
    detail: str = ""


class ReservationProjection(_ToolResult):
    """What the ledger and the recipient's capacity WILL look like after commit.

    The durable write happens atomically inside `create_delivery_order`, because
    clean_code_spec 6.2 requires steps 3-6 of the allocation transaction to
    succeed or roll back together. Splitting the write across independent tool
    calls would strand reserved kilograms if the model stopped mid-plan, so
    these two tools confirm and stage the reservation rather than committing it.
    That also makes them trivially idempotent (clean_code_spec 7.4).
    """

    ok: bool
    quantity_kg: int
    available_kg_after: int = Field(default=0, ge=0)
    recipient_capacity_kg_after: int = Field(default=0, ge=0)
    detail: str = ""


class DeliveryOrderResult(_ToolResult):
    order: DeliveryOrder
    inventory: DonationInventory


class AcceptanceResultView(_ToolResult):
    order: DeliveryOrder
    planned_kg: int
    accepted_kg: int
    remaining_kg: int
    corrected_capacity_kg: int
    requires_rematch: bool
    inventory: DonationInventory


class InventoryView(_ToolResult):
    inventory: DonationInventory
    detail: str = ""
