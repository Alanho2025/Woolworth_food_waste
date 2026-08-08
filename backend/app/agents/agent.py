"""Single FoodRedistributionAgent and deterministic replay execution."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from google.adk.agents import LlmAgent
from pydantic import BaseModel, ConfigDict, Field

from backend.app.agents.bounds import AgentBounds, run_within_budget
from backend.app.agents.instructions import FOOD_REDISTRIBUTION_INSTRUCTION
from backend.app.agents.schemas import (
    AssignDriverInput,
    CandidateListResult,
    CreateDeliveryOrderInput,
    CreateRematchedDeliveryInput,
    DeliveryOrderResult,
    DonationView,
    DriverListResult,
    GetAvailableDriversInput,
    GetDonationInput,
    ListCandidateCommunitiesInput,
    ReleaseRemainingInventoryInput,
    ReserveInventoryInput,
    ReserveRecipientCapacityInput,
    ToolFailure,
    UpdateDriverRouteInput,
)
from backend.app.agents.tools import FoodFlowTools, ToolDependencies, build_tool_functions
from backend.app.contracts.api import (
    AgentRunKind,
    AgentRunResult,
    InitialAgentRunResult,
    RematchAgentRunResult,
)
from backend.app.contracts.core import (
    AgentState,
    AgentStateEvent,
    AllocationDecision,
    CandidateAssessment,
    CandidateStatus,
    RematchDecision,
)
from backend.app.domain.clock import Clock
from backend.app.domain.errors import AgentError, ErrorCode
from backend.app.domain.ports import UnitOfWork

FIXTURE_PATH = Path(__file__).with_name("fixtures") / "journey.json"


class AgentInvocation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str = Field(min_length=1)
    donation_id: str = Field(min_length=1)
    kind: AgentRunKind
    declined_order_id: str | None = None
    original_community_id: str | None = None
    accepted_kg: int = Field(default=0, ge=0)
    remaining_kg: int = Field(default=0, ge=0)


@dataclass(frozen=True)
class AgentExecutionResult:
    result: AgentRunResult
    events: tuple[AgentStateEvent, ...]
    tool_trace: tuple[str, ...]
    recovered_failures: int = 0


class AgentExecutor(Protocol):
    async def run(self, invocation: AgentInvocation) -> AgentExecutionResult: ...


class ReplayFixture(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    initial_candidates: tuple[str, ...]
    initial_driver_id: str
    initial_explanation: str
    rematch_candidates: tuple[str, ...]
    rematch_explanation: str


class AgentEventStore:
    """Commit each visible event in its own short transaction for live polling."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def create(self, invocation: AgentInvocation) -> None:
        with self._uow as uow:
            uow.agent_runs.create(invocation.run_id, invocation.donation_id)
            uow.commit()

    def append(self, run_id: str, event: AgentStateEvent) -> None:
        with self._uow as uow:
            uow.agent_runs.append_event(run_id, event)
            uow.commit()

    def complete(self, run_id: str, error_code: ErrorCode | None = None) -> None:
        with self._uow as uow:
            uow.agent_runs.complete(run_id, error_code.value if error_code else None)
            uow.commit()


class ReplayAgentExecutor:
    """Replay recorded model choices while executing real typed Python tools."""

    def __init__(
        self,
        dependencies: ToolDependencies,
        event_store: AgentEventStore,
        clock: Clock,
        *,
        fixture_path: Path = FIXTURE_PATH,
        event_delay_seconds: float = 0.0,
    ) -> None:
        self._tools = FoodFlowTools(dependencies)
        self._store = event_store
        self._clock = clock
        self._bounds: AgentBounds = dependencies.bounds
        self._fixture = ReplayFixture.model_validate_json(fixture_path.read_text(encoding="utf-8"))
        self._delay = event_delay_seconds

    async def run(self, invocation: AgentInvocation) -> AgentExecutionResult:
        self._store.create(invocation)
        try:
            result = await run_within_budget(self._run(invocation), self._bounds)
        except AgentError as error:
            self._store.complete(invocation.run_id, error.code)
            raise
        self._store.complete(invocation.run_id)
        return result

    async def _run(self, invocation: AgentInvocation) -> AgentExecutionResult:
        if invocation.kind is AgentRunKind.INITIAL:
            return await self._initial(invocation)
        return await self._rematch(invocation)

    async def _emit(
        self,
        invocation: AgentInvocation,
        events: list[AgentStateEvent],
        state: AgentState,
        label: str,
        detail: str = "",
    ) -> None:
        event = AgentStateEvent(
            sequence=len(events) + 1,
            state=state,
            label=label,
            detail=detail,
            occurred_at=self._clock.now(),
        )
        self._store.append(invocation.run_id, event)
        events.append(event)
        if self._delay:
            await asyncio.sleep(self._delay)

    async def _initial(self, invocation: AgentInvocation) -> AgentExecutionResult:
        events: list[AgentStateEvent] = []
        trace: list[str] = []
        await self._emit(invocation, events, AgentState.READING_DONATION, "Reading donation")
        donation = await self._tools.get_donation(
            GetDonationInput(donation_id=invocation.donation_id)
        )
        trace.append("get_donation")
        donation = _expect(donation, DonationView)
        quantity = donation.inventory.available_kg

        await self._emit(
            invocation, events, AgentState.CHECKING_DEMAND, "Checking community demand"
        )
        candidates = await self._tools.list_candidate_communities(
            ListCandidateCommunitiesInput(donation_id=invocation.donation_id, required_kg=quantity)
        )
        trace.append("list_candidate_communities")
        candidates = _expect(candidates, CandidateListResult)
        await self._emit(invocation, events, AgentState.CHECKING_CAPACITY, "Checking capacity")
        await self._emit(
            invocation, events, AgentState.CHECKING_WINDOWS, "Checking receiving windows"
        )
        await self._emit(
            invocation,
            events,
            AgentState.COMPARING_RECIPIENTS,
            "Comparing feasible recipients",
        )
        chosen, recovered = _choose_candidate(
            candidates.candidates, self._fixture.initial_candidates
        )
        drivers = await self._tools.get_available_drivers(
            GetAvailableDriversInput(donation_id=invocation.donation_id, quantity_kg=quantity)
        )
        trace.append("get_available_drivers")
        drivers = _expect(drivers, DriverListResult)
        if self._fixture.initial_driver_id not in {driver.driver_id for driver in drivers.drivers}:
            raise AgentError(ErrorCode.AGENT_OUTPUT_INVALID, "fixture selected an invalid driver")

        await self._tools.reserve_inventory(
            ReserveInventoryInput(donation_id=invocation.donation_id, quantity_kg=quantity)
        )
        trace.append("reserve_inventory")
        await self._tools.reserve_recipient_capacity(
            ReserveRecipientCapacityInput(
                community_id=chosen.community.community_id, quantity_kg=quantity
            )
        )
        trace.append("reserve_recipient_capacity")
        await self._emit(invocation, events, AgentState.CREATING_ORDER, "Creating delivery order")
        created = await self._tools.create_delivery_order(
            CreateDeliveryOrderInput(
                donation_id=invocation.donation_id,
                community_id=chosen.community.community_id,
                quantity_kg=quantity,
                driver_id=self._fixture.initial_driver_id,
                origin=donation.donation.store_location,
            )
        )
        trace.append("create_delivery_order")
        created = _expect(created, DeliveryOrderResult)
        await self._emit(invocation, events, AgentState.ASSIGNING_DRIVER, "Assigning driver")
        assigned = await self._tools.assign_driver(
            AssignDriverInput(
                order_id=created.order.order_id, driver_id=self._fixture.initial_driver_id
            )
        )
        trace.append("assign_driver")
        assigned = _expect(assigned, DeliveryOrderResult)
        decision = AllocationDecision(
            donation_id=invocation.donation_id,
            selected_community_id=chosen.community.community_id,
            allocated_kg=quantity,
            driver_id=self._fixture.initial_driver_id,
            route=assigned.order.route,
            explanation=self._fixture.initial_explanation,
            candidates=_mark_recommended(candidates.candidates, chosen.community.community_id),
        )
        return AgentExecutionResult(
            result=InitialAgentRunResult(
                decision=decision,
                inventory=assigned.inventory,
                order_refs=[assigned.order.order_id],
            ),
            events=tuple(events),
            tool_trace=tuple(trace),
            recovered_failures=recovered,
        )

    async def _rematch(self, invocation: AgentInvocation) -> AgentExecutionResult:
        declined_order_id = invocation.declined_order_id
        original_community_id = invocation.original_community_id
        if not declined_order_id or not original_community_id or not invocation.remaining_kg:
            raise AgentError(ErrorCode.AGENT_OUTPUT_INVALID, "rematch invocation is incomplete")
        events: list[AgentStateEvent] = []
        trace: list[str] = []
        await self._emit(
            invocation,
            events,
            AgentState.CONDITION_CHANGED,
            "Delivery condition changed",
            f"{invocation.remaining_kg} kg requires rematch",
        )
        await self._tools.release_remaining_inventory(
            ReleaseRemainingInventoryInput(order_id=declined_order_id)
        )
        trace.append("release_remaining_inventory")
        await self._emit(invocation, events, AgentState.REEVALUATING, "Re-evaluating alternatives")
        candidates = await self._tools.list_candidate_communities(
            ListCandidateCommunitiesInput(
                donation_id=invocation.donation_id,
                required_kg=invocation.remaining_kg,
                declined_order_id=declined_order_id,
            )
        )
        trace.append("list_candidate_communities")
        candidates = _expect(candidates, CandidateListResult)
        chosen, recovered = _choose_candidate(
            candidates.candidates, self._fixture.rematch_candidates
        )
        created = await self._tools.create_rematched_delivery(
            CreateRematchedDeliveryInput(
                declined_order_id=declined_order_id,
                community_id=chosen.community.community_id,
                remaining_kg=invocation.remaining_kg,
            )
        )
        trace.append("create_rematched_delivery")
        created = _expect(created, DeliveryOrderResult)
        await self._emit(invocation, events, AgentState.UPDATING_ROUTE, "Updating route")
        updated = await self._tools.update_driver_route(
            UpdateDriverRouteInput(order_id=created.order.order_id)
        )
        trace.append("update_driver_route")
        updated = _expect(updated, DeliveryOrderResult)
        await self._emit(invocation, events, AgentState.REMATCH_COMPLETE, "Rematch complete")
        decision = RematchDecision(
            donation_id=invocation.donation_id,
            original_community_id=original_community_id,
            accepted_kg=invocation.accepted_kg,
            remaining_kg=invocation.remaining_kg,
            new_community_id=chosen.community.community_id,
            new_route=updated.order.route,
            explanation=self._fixture.rematch_explanation,
            candidates=_mark_recommended(candidates.candidates, chosen.community.community_id),
        )
        return AgentExecutionResult(
            result=RematchAgentRunResult(
                decision=decision,
                inventory=updated.inventory,
                order_refs=[updated.order.order_id],
            ),
            events=tuple(events),
            tool_trace=tuple(trace),
            recovered_failures=recovered,
        )


def build_food_redistribution_agent(model: object, dependencies: ToolDependencies) -> LlmAgent:
    """Build the one allowed ADK root Agent."""
    return LlmAgent(
        name="FoodRedistributionAgent",
        model=model,  # type: ignore[arg-type]
        instruction=FOOD_REDISTRIBUTION_INSTRUCTION,
        tools=build_tool_functions(dependencies),  # type: ignore[arg-type]
    )


def _expect[T: BaseModel](value: BaseModel, expected: type[T]) -> T:
    if isinstance(value, ToolFailure):
        raise AgentError(value.code, value.detail)
    if not isinstance(value, expected):
        raise AgentError(ErrorCode.TOOL_INVALID_RESULT, "tool returned an invalid result type")
    return value


def _choose_candidate(
    candidates: list[CandidateAssessment], preferences: tuple[str, ...]
) -> tuple[CandidateAssessment, int]:
    by_id = {candidate.community.community_id: candidate for candidate in candidates}
    for recovered, community_id in enumerate(preferences):
        candidate = by_id.get(community_id)
        if candidate is not None and candidate.status is not CandidateStatus.EXCLUDED:
            return candidate, recovered
    raise AgentError(ErrorCode.AGENT_OUTPUT_INVALID, "no replay candidate passed validation")


def _mark_recommended(
    candidates: list[CandidateAssessment], community_id: str
) -> list[CandidateAssessment]:
    return [
        candidate.model_copy(update={"status": CandidateStatus.RECOMMENDED})
        if candidate.community.community_id == community_id
        else candidate
        for candidate in candidates
    ]
