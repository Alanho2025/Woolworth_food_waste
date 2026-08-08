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

from pydantic import BaseModel, ConfigDict, Field, StrictInt

from backend.app.contracts.core import (
    CandidateAssessment,
    CommunityNeed,
    DeliveryOrder,
    DonationInventory,
    DonationRequest,
    Driver,
    FoodCategory,
    Location,
    RouteLeg,
    StorageType,
    TimeWindow,
)
from backend.app.domain.errors import ErrorCode


class _ToolModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class GetDonationInput(_ToolModel):
    donation_id: str = Field(min_length=1)


class ListCandidateCommunitiesInput(_ToolModel):
    donation_id: str = Field(min_length=1)
    required_kg: StrictInt = Field(gt=0)
    origin: Location | None = None
    declined_community_ids: tuple[str, ...] = ()
    declined_order_id: str | None = None


class GetCommunityCapacityInput(_ToolModel):
    community_id: str = Field(min_length=1)


class GetAvailableDriversInput(_ToolModel):
    donation_id: str = Field(min_length=1)
    quantity_kg: StrictInt = Field(gt=0)


class CalculateRouteInput(_ToolModel):
    origin: Location
    destination: Location


class ValidateCategoryAcceptanceInput(_ToolModel):
    community_id: str = Field(min_length=1)
    category: FoodCategory


class ValidateStorageCompatibilityInput(_ToolModel):
    community_id: str = Field(min_length=1)
    storage_type: StorageType


class ValidateRecipientCapacityInput(_ToolModel):
    community_id: str = Field(min_length=1)
    required_kg: StrictInt = Field(gt=0)


class ValidateReceivingWindowInput(_ToolModel):
    community_id: str = Field(min_length=1)
    route: RouteLeg


class ValidateDriverCapacityInput(_ToolModel):
    driver_id: str = Field(min_length=1)
    required_kg: StrictInt = Field(gt=0)


class ReserveInventoryInput(_ToolModel):
    donation_id: str = Field(min_length=1)
    quantity_kg: StrictInt = Field(gt=0)


class ReserveRecipientCapacityInput(_ToolModel):
    community_id: str = Field(min_length=1)
    quantity_kg: StrictInt = Field(gt=0)


class CreateDeliveryOrderInput(_ToolModel):
    donation_id: str = Field(min_length=1)
    community_id: str = Field(min_length=1)
    quantity_kg: StrictInt = Field(gt=0)
    driver_id: str = Field(min_length=1)
    origin: Location


class AssignDriverInput(_ToolModel):
    order_id: str = Field(min_length=1)
    driver_id: str = Field(min_length=1)


class RecordPartialAcceptanceInput(_ToolModel):
    order_id: str = Field(min_length=1)
    accepted_kg: StrictInt = Field(ge=0)
    reason: str = ""


class ReleaseRemainingInventoryInput(_ToolModel):
    order_id: str = Field(min_length=1)


class CreateRematchedDeliveryInput(_ToolModel):
    declined_order_id: str = Field(min_length=1)
    community_id: str = Field(min_length=1)
    remaining_kg: StrictInt = Field(gt=0)


class UpdateDriverRouteInput(_ToolModel):
    order_id: str = Field(min_length=1)


class ToolFailure(_ToolModel):
    """Every tool failure the Agent sees, in one shape.

    AGENTS_FoodFlow.md 9 requires tool failures to be distinguishable as
    validation failure, not found, timeout, rate limited, invalid result, or
    internal failure -- so the code travels with the message and the Agent never
    has to parse an exception string to decide what to do next.
    """

    ok: bool = False
    code: ErrorCode
    detail: str


class DonationView(_ToolModel):
    donation: DonationRequest
    inventory: DonationInventory


class CandidateListResult(_ToolModel):
    """Complete facts for EVERY community, excluded ones included (R-18)."""

    required_kg: int
    candidates: list[CandidateAssessment]


class CommunityCapacityView(_ToolModel):
    """Need and capacity, kept deliberately separate (Requirement.md 9)."""

    community_id: str
    name: str
    needs: list[CommunityNeed]
    remaining_capacity_kg: int
    receiving_window: TimeWindow
    is_open: bool


class DriverListResult(_ToolModel):
    quantity_kg: int
    drivers: list[Driver]


class RouteResult(_ToolModel):
    route: RouteLeg


class ValidationResult(_ToolModel):
    """The answer to one hard-constraint question.

    `ok=False` is a business outcome, not an error: the Agent is expected to use
    it to exclude a candidate and carry on.
    """

    ok: bool
    code: ErrorCode | None = None
    detail: str = ""


class ReservationProjection(_ToolModel):
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


class DeliveryOrderResult(_ToolModel):
    order: DeliveryOrder
    inventory: DonationInventory


class AcceptanceResultView(_ToolModel):
    order: DeliveryOrder
    planned_kg: int
    accepted_kg: int
    remaining_kg: int
    corrected_capacity_kg: int
    requires_rematch: bool
    inventory: DonationInventory


class InventoryView(_ToolModel):
    inventory: DonationInventory
    detail: str = ""


ToolResult = (
    ToolFailure
    | DonationView
    | CandidateListResult
    | CommunityCapacityView
    | DriverListResult
    | RouteResult
    | ValidationResult
    | ReservationProjection
    | DeliveryOrderResult
    | AcceptanceResultView
    | InventoryView
)
