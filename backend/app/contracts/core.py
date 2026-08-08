"""Core typed contracts — the integration seam.

These Pydantic models are the shared vocabulary for persistence, the Agent
tools, the API, and the generated frontend client. SQLAlchemy models represent
persistence only and are never used as API schemas (clean_code_spec 4, 9).

Four concepts are kept deliberately separate and must not be collapsed
(Requirement.md 9, AGENTS_FoodFlow.md 8.2):

  Need        what a community currently wants
  Capacity    what it can currently receive and store
  Eligibility whether hard constraints allow a delivery
  Decision    which eligible option the Agent selected, and why

A community can have urgent need and still be ineligible for lack of capacity.
That distinction is the product's value proposition.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StrictInt, model_validator

from backend.app.domain.errors import ErrorCode
from backend.app.domain.quantity import Kilograms, PositiveKilograms


class _Base(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


# --------------------------------------------------------------------------
# Enumerations
# --------------------------------------------------------------------------


class FoodCategory(StrEnum):
    VEGETABLES = "vegetables"
    FRUIT = "fruit"
    BAKERY = "bakery"
    DAIRY = "dairy"
    MEAT = "meat"
    AMBIENT_GROCERY = "ambient_grocery"


class StorageType(StrEnum):
    AMBIENT = "ambient"
    CHILLED = "chilled"
    FROZEN = "frozen"


class NeedLevel(StrEnum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class DeliveryStatus(StrEnum):
    CREATED = "created"
    DRIVER_ASSIGNED = "driver_assigned"
    IN_TRANSIT = "in_transit"
    ARRIVED = "arrived"
    PARTIALLY_ACCEPTED = "partially_accepted"
    COMPLETED = "completed"
    REJECTED = "rejected"


class CandidateStatus(StrEnum):
    """Final label shown on each community card on the Agent Match screen."""

    RECOMMENDED = "recommended"
    FEASIBLE_ALTERNATIVE = "feasible_alternative"
    EXCLUDED = "excluded"


class AgentState(StrEnum):
    """The eleven visible states of Requirement.md 12.

    Persisted incrementally as the run proceeds so the UI can poll and reveal
    them live. Accumulating them and returning the list at the end would put
    every state on screen *after* the decision it exists to explain.
    See docs/phase_review_findings.md R-2.
    """

    READING_DONATION = "reading_donation"
    CHECKING_DEMAND = "checking_community_demand"
    CHECKING_CAPACITY = "checking_capacity"
    CHECKING_WINDOWS = "checking_receiving_windows"
    COMPARING_RECIPIENTS = "comparing_feasible_recipients"
    CREATING_ORDER = "creating_delivery_order"
    ASSIGNING_DRIVER = "assigning_driver"
    CONDITION_CHANGED = "delivery_condition_changed"
    REEVALUATING = "re_evaluating_alternatives"
    UPDATING_ROUTE = "updating_route"
    REMATCH_COMPLETE = "rematch_complete"


# --------------------------------------------------------------------------
# Geography
# --------------------------------------------------------------------------


class Location(_Base):
    name: str = Field(min_length=1)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class TimeWindow(_Base):
    start: AwareDatetime
    end: AwareDatetime

    @model_validator(mode="after")
    def end_follows_start(self) -> TimeWindow:
        if self.end <= self.start:
            raise ValueError("time-window end must be after start")
        return self


class RouteLeg(_Base):
    """A simulated route. Never presented as real routing (AGENTS_FoodFlow.md 2)."""

    origin: Location
    destination: Location
    # Hand-traced plausible road geometry. A straight geodesic renders as a line
    # through the Waitemata Harbour and reads as broken to an Auckland judge.
    # See docs/phase_review_findings.md R-19.
    polyline: list[tuple[float, float]] = Field(min_length=2)
    distance_km: float = Field(ge=0)
    duration_minutes: StrictInt = Field(ge=0)
    eta: AwareDatetime
    simulated: bool = True


# --------------------------------------------------------------------------
# Donation
# --------------------------------------------------------------------------


class FoodItem(_Base):
    item_name: str = Field(min_length=1)
    category: FoodCategory
    quantity: PositiveKilograms
    unit: Literal["kg"] = "kg"
    storage_type: StorageType
    delivery_deadline: AwareDatetime


class DonationRequest(_Base):
    donation_id: str = Field(min_length=1)
    store_id: str = Field(min_length=1)
    store_location: Location
    pickup_window: TimeWindow
    items: list[FoodItem] = Field(min_length=1)
    handling_notes: str = ""


class DonationInventory(_Base):
    """The quantity ledger for one donation.

    The four components must always sum to `total_kg`. This is asserted at every
    state transition, not merely tested on one path -- AGENTS_FoodFlow.md 8.4
    calls it blocker-level. The UI renders these four as a stacked bar, which is
    the visible proof clean_code_spec 8.4 requires.
    """

    donation_id: str
    total_kg: PositiveKilograms
    available_kg: Kilograms
    reserved_kg: Kilograms
    in_transit_kg: Kilograms
    delivered_kg: Kilograms

    @model_validator(mode="after")
    def components_equal_total(self) -> DonationInventory:
        if not self.is_balanced:
            raise ValueError("inventory components must sum to total_kg")
        return self

    @property
    def is_balanced(self) -> bool:
        return (
            self.available_kg + self.reserved_kg + self.in_transit_kg + self.delivered_kg
        ) == self.total_kg


# --------------------------------------------------------------------------
# Community
# --------------------------------------------------------------------------


class CommunityNeed(_Base):
    """What the organisation WANTS. Distinct from what it can receive."""

    category: FoodCategory
    level: NeedLevel


class CommunityOrganisation(_Base):
    community_id: str
    name: str
    location: Location
    accepted_categories: list[FoodCategory] = Field(min_length=1)
    supported_storage: list[StorageType] = Field(min_length=1)
    needs: list[CommunityNeed] = Field(min_length=1)
    # The latest declared maximum for the current operational window. This can
    # be corrected when a recipient reports that its earlier capacity was wrong.
    declared_capacity_kg: Kilograms
    # What it can still RECEIVE AND STORE after reservations/acceptances.
    remaining_capacity_kg: Kilograms
    receiving_window: TimeWindow
    is_open: bool

    @model_validator(mode="after")
    def remaining_does_not_exceed_declared(self) -> CommunityOrganisation:
        if self.remaining_capacity_kg > self.declared_capacity_kg:
            raise ValueError("remaining capacity cannot exceed declared capacity")
        return self


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------


class Driver(_Base):
    driver_id: str
    name: str
    start_location: Location
    vehicle_capacity_kg: PositiveKilograms
    is_available: bool


# --------------------------------------------------------------------------
# Agent decision surface
# --------------------------------------------------------------------------


class ExclusionReason(_Base):
    code: ErrorCode
    # Shown verbatim on the community card. The wording for an insufficient
    # capacity must say "insufficient for a single-destination allocation" --
    # a bare "insufficient capacity" is subtly untrue and a judge can challenge
    # it with "but it could take 10 of the 25".
    # See docs/assumption_audit.md C-2.
    display_text: str


class CandidateAssessment(_Base):
    """One community's complete fact set, plus its eligibility label.

    Every displayable fact is computed for EVERY candidate, including ones that
    already failed a hard constraint. Requirement.md 5 requires an ETA on all
    four cards; a validator that short-circuits on category leaves blank cells
    in the centrepiece comparison table of the most important pitch screen.
    Eligibility is a label over a complete fact set, never an early return.
    See docs/phase_review_findings.md R-18.
    """

    community: CommunityOrganisation
    matched_need: CommunityNeed | None
    category_compatible: bool
    storage_compatible: bool
    capacity_sufficient: bool
    window_open_on_arrival: bool
    within_deadline: bool
    route: RouteLeg
    status: CandidateStatus
    exclusions: list[ExclusionReason] = Field(default_factory=list)


class AllocationDecision(_Base):
    donation_id: str
    selected_community_id: str
    allocated_kg: PositiveKilograms
    driver_id: str
    route: RouteLeg
    # Concise operational explanation. Never chain-of-thought.
    explanation: str
    candidates: list[CandidateAssessment]


class RematchDecision(_Base):
    donation_id: str
    original_community_id: str
    accepted_kg: Kilograms
    remaining_kg: PositiveKilograms
    new_community_id: str
    new_route: RouteLeg
    explanation: str
    candidates: list[CandidateAssessment]


class DeliveryOrder(_Base):
    order_id: str
    donation_id: str
    # Explicit location, NOT implicitly the donating store. The rematched leg
    # departs from Community A where the driver is already standing; a
    # store-origin default would draw a phantom return trip to Mount Eden.
    # See docs/assumption_audit.md C-4.
    origin: Location
    destination_community_id: str
    quantity_kg: PositiveKilograms
    driver_id: str
    route: RouteLeg
    status: DeliveryStatus
    deadline: AwareDatetime
    is_rematch: bool = False


class AgentStateEvent(_Base):
    """One visible step of an Agent run.

    Persisted as it happens so `GET /agent-runs/{id}` can return a growing list
    while the run is still in flight.
    """

    sequence: int
    state: AgentState
    label: str
    detail: str = ""
    occurred_at: AwareDatetime


class AgentRun(_Base):
    run_id: str
    donation_id: str
    events: list[AgentStateEvent]
    is_complete: bool
    # Set only on failure; a run never reports success with an error present.
    error_code: ErrorCode | None = None


class AuditEvent(_Base):
    event_id: str
    donation_id: str
    action: str
    detail: str
    occurred_at: AwareDatetime
    succeeded: bool
