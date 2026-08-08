"""Application orchestration used by the HTTP transport.

FastAPI routes delegate here so transport code contains no allocation,
quantity, rematch, or dashboard decisions.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from backend.app.agents.agent import (
    AgentEventStore,
    AgentExecutionResult,
    AgentInvocation,
    ReplayAgentExecutor,
)
from backend.app.agents.bounds import AgentBounds
from backend.app.agents.tools import ToolDependencies
from backend.app.application.allocate_donation import AllocateDonation
from backend.app.application.record_acceptance import RecordAcceptance
from backend.app.application.rematch import RematchRemaining
from backend.app.config import Settings
from backend.app.contracts.api import (
    AgentRunKind,
    AgentRunResponse,
    AgentRunStatus,
    AgentRunSummary,
    AgentRunTransport,
    CapacityChangeAlert,
    ConfirmDeliveryRequest,
    ConfirmDeliveryResponse,
    CreateDonationRequest,
    CreateDonationResponse,
    DashboardKpis,
    DeliveryAcceptanceOutcome,
    DeliveryDetailResponse,
    DeliveryStatusEvent,
    GlobalDashboardResponse,
    StartMatchResponse,
)
from backend.app.contracts.core import (
    AgentRun,
    DeliveryStatus,
    DonationInventory,
    DonationRequest,
)
from backend.app.domain.clock import Clock
from backend.app.domain.errors import EligibilityError, ErrorCode, FoodFlowError
from backend.app.domain.ports import RouteSimulator, UnitOfWork
from backend.app.seed.data import STORE_ID, STORE_LOCATION

UowFactory = Callable[[], UnitOfWork]


@dataclass
class _RunRecord:
    run_id: str
    donation_id: str
    kind: AgentRunKind
    transport: AgentRunTransport
    status: AgentRunStatus = AgentRunStatus.QUEUED
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: AgentExecutionResult | None = None
    error_code: ErrorCode | None = None


class AgentRunCoordinator:
    """Supervise replay tasks and join process metadata with durable events."""

    def __init__(
        self,
        uow_factory: UowFactory,
        routes: RouteSimulator,
        clock: Clock,
        settings: Settings,
        *,
        replay_event_delay_seconds: float = 0.02,
    ) -> None:
        self._uow_factory = uow_factory
        self._routes = routes
        self._clock = clock
        self._settings = settings
        self._delay = replay_event_delay_seconds
        self._runs: dict[str, _RunRecord] = {}
        self._tasks: set[asyncio.Task[None]] = set()

    def start_initial(self, donation_id: str) -> StartMatchResponse:
        with self._uow_factory() as uow:
            if uow.donations.get(donation_id) is None:
                raise EligibilityError(ErrorCode.NOT_FOUND, f"Unknown donation {donation_id}")
        record = self._start(
            AgentInvocation(
                run_id=_new_id("RUN"),
                donation_id=donation_id,
                kind=AgentRunKind.INITIAL,
            )
        )
        return StartMatchResponse(
            run_id=record.run_id,
            donation_id=record.donation_id,
            transport=record.transport,
        )

    def start_rematch(
        self,
        *,
        donation_id: str,
        declined_order_id: str,
        original_community_id: str,
        accepted_kg: int,
        remaining_kg: int,
    ) -> str:
        record = self._start(
            AgentInvocation(
                run_id=_new_id("RUN"),
                donation_id=donation_id,
                kind=AgentRunKind.REMATCH,
                declined_order_id=declined_order_id,
                original_community_id=original_community_id,
                accepted_kg=accepted_kg,
                remaining_kg=remaining_kg,
            )
        )
        return record.run_id

    def _start(self, invocation: AgentInvocation) -> _RunRecord:
        transport = AgentRunTransport(self._settings.agent_transport.value)
        if transport is AgentRunTransport.LIVE:
            raise FoodFlowError(
                ErrorCode.AGENT_OUTPUT_INVALID,
                "Live transport is configured but the full journey is not verified; use replay",
            )
        record = _RunRecord(
            run_id=invocation.run_id,
            donation_id=invocation.donation_id,
            kind=invocation.kind,
            transport=transport,
        )
        self._runs[record.run_id] = record
        task = asyncio.create_task(self._execute(record, invocation))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return record

    async def _execute(self, record: _RunRecord, invocation: AgentInvocation) -> None:
        record.status = AgentRunStatus.RUNNING
        record.started_at = self._clock.now()
        try:
            record.result = await self._executor().run(invocation)
        except FoodFlowError as error:
            record.error_code = error.code
            record.status = AgentRunStatus.FAILED
        except Exception:
            record.error_code = ErrorCode.TOOL_INTERNAL_FAILURE
            record.status = AgentRunStatus.FAILED
        else:
            record.status = AgentRunStatus.SUCCEEDED
        finally:
            record.completed_at = self._clock.now()

    def _executor(self) -> ReplayAgentExecutor:
        agent_uow = self._uow_factory()
        allocator = AllocateDonation(agent_uow, self._routes, self._clock)
        dependencies = ToolDependencies(
            uow=agent_uow,
            allocator=allocator,
            acceptance=RecordAcceptance(self._uow_factory(), self._clock),
            rematcher=RematchRemaining(self._uow_factory(), allocator),
            routes=self._routes,
            bounds=AgentBounds.from_settings(self._settings),
        )
        return ReplayAgentExecutor(
            dependencies,
            AgentEventStore(self._uow_factory()),
            self._clock,
            event_delay_seconds=self._delay,
        )

    def get(self, run_id: str) -> AgentRunResponse:
        record = self._runs.get(run_id)
        if record is None:
            raise EligibilityError(ErrorCode.NOT_FOUND, f"Unknown Agent run {run_id}")
        persisted: AgentRun | None
        with self._uow_factory() as uow:
            persisted = uow.agent_runs.get(run_id)
        result = record.result.result if record.result is not None else None
        return AgentRunResponse(
            run_id=record.run_id,
            donation_id=record.donation_id,
            status=record.status,
            kind=record.kind,
            transport=record.transport,
            started_at=record.started_at,
            completed_at=record.completed_at,
            events=persisted.events if persisted is not None else [],
            result=result,
            error_code=record.error_code,
        )

    def summaries(self) -> list[AgentRunSummary]:
        return [
            AgentRunSummary(
                run_id=record.run_id,
                donation_id=record.donation_id,
                status=record.status,
                kind=record.kind,
                transport=record.transport,
                latest_event=(response.events[-1] if response.events else None),
            )
            for record in self._runs.values()
            for response in [self.get(record.run_id)]
        ]

    async def shutdown(self) -> None:
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)


class FoodFlowApiService:
    """Typed application facade for the seven public endpoints."""

    def __init__(
        self,
        uow_factory: UowFactory,
        acceptance: RecordAcceptance,
        coordinator: AgentRunCoordinator,
        clock: Clock,
    ) -> None:
        self._uow_factory = uow_factory
        self._acceptance = acceptance
        self._coordinator = coordinator
        self._clock = clock

    def create_donation(self, request: CreateDonationRequest) -> CreateDonationResponse:
        if request.store_id != STORE_ID:
            raise EligibilityError(ErrorCode.NOT_FOUND, f"Unknown store {request.store_id}")
        donation_id = _new_id("DON")
        donation = DonationRequest(
            donation_id=donation_id,
            store_id=request.store_id,
            store_location=STORE_LOCATION,
            pickup_window=request.pickup_window,
            items=request.items,
            handling_notes=request.handling_notes,
        )
        total = sum(item.quantity for item in donation.items)
        inventory = DonationInventory(
            donation_id=donation_id,
            total_kg=total,
            available_kg=total,
            reserved_kg=0,
            in_transit_kg=0,
            delivered_kg=0,
        )
        with self._uow_factory() as uow:
            uow.donations.add(donation)
            uow.donations.save_inventory(inventory)
            uow.commit()
        return CreateDonationResponse(donation=donation, inventory=inventory)

    def start_match(self, donation_id: str) -> StartMatchResponse:
        return self._coordinator.start_initial(donation_id)

    def get_agent_run(self, run_id: str) -> AgentRunResponse:
        return self._coordinator.get(run_id)

    def get_delivery(self, delivery_id: str) -> DeliveryDetailResponse:
        with self._uow_factory() as uow:
            order = uow.deliveries.get(delivery_id)
            if order is None:
                raise EligibilityError(ErrorCode.NOT_FOUND, f"Unknown delivery {delivery_id}")
            donation = uow.donations.get(order.donation_id)
            inventory = uow.donations.get_inventory(order.donation_id)
            driver = uow.drivers.get(order.driver_id)
            community = uow.communities.get(order.destination_community_id)
        if donation is None or inventory is None or driver is None or community is None:
            raise EligibilityError(ErrorCode.NOT_FOUND, "Delivery references missing data")
        return DeliveryDetailResponse(
            order=order,
            donation=donation,
            driver=driver,
            destination=community,
            inventory=inventory,
            status=order.status,
            status_timeline=_status_timeline(order.status, self._clock.now()),
        )

    def confirm_delivery(
        self, delivery_id: str, request: ConfirmDeliveryRequest
    ) -> ConfirmDeliveryResponse:
        with self._uow_factory() as uow:
            planned = uow.deliveries.get(delivery_id)
        if planned is None:
            raise EligibilityError(ErrorCode.NOT_FOUND, f"Unknown delivery {delivery_id}")
        expected_outcome = _acceptance_outcome(
            request.accepted_kg,
            planned.quantity_kg - request.accepted_kg,
        )
        if request.outcome is not expected_outcome:
            raise EligibilityError(
                ErrorCode.INVALID_STATE_TRANSITION,
                f"Outcome {request.outcome.value} does not match accepted quantity",
            )
        accepted = self._acceptance.execute(delivery_id, request.accepted_kg, request.reason)
        actual = _acceptance_outcome(
            accepted.outcome.accepted_kg,
            accepted.outcome.remaining_kg,
        )
        rematch_run_id = None
        if accepted.outcome.remaining_kg:
            rematch_run_id = self._coordinator.start_rematch(
                donation_id=accepted.order.donation_id,
                declined_order_id=accepted.order.order_id,
                original_community_id=accepted.order.destination_community_id,
                accepted_kg=accepted.outcome.accepted_kg,
                remaining_kg=accepted.outcome.remaining_kg,
            )
        return ConfirmDeliveryResponse(
            delivery=accepted.order,
            outcome=actual,
            planned_kg=accepted.outcome.planned_kg,
            accepted_kg=accepted.outcome.accepted_kg,
            remaining_kg=accepted.outcome.remaining_kg,
            corrected_community=accepted.community,
            inventory=accepted.inventory,
            rematch_run_id=rematch_run_id,
        )

    def dashboard(self) -> GlobalDashboardResponse:
        with self._uow_factory() as uow:
            donations = uow.donations.list_all()
            inventories = uow.donations.list_inventories()
            deliveries = uow.deliveries.list_all()
            communities = uow.communities.list_all()
            drivers = uow.drivers.list_all()
            acceptances = [uow.acceptances.get(order.order_id) for order in deliveries]
        alerts = [
            CapacityChangeAlert(
                community_id=acceptance.community_id,
                community_name=next(
                    community.name
                    for community in communities
                    if community.community_id == acceptance.community_id
                ),
                declared_capacity_kg=acceptance.accepted_kg,
                accepted_kg=acceptance.accepted_kg,
                message=(
                    f"Capacity corrected after accepting {acceptance.accepted_kg} of "
                    f"{acceptance.planned_kg} kg"
                ),
            )
            for acceptance in acceptances
            if acceptance is not None and acceptance.remaining_kg > 0
        ]
        summaries = self._coordinator.summaries()
        active_statuses = {
            DeliveryStatus.DRIVER_ASSIGNED,
            DeliveryStatus.IN_TRANSIT,
            DeliveryStatus.ARRIVED,
        }
        active_deliveries = [order for order in deliveries if order.status in active_statuses]
        kpis = DashboardKpis(
            active_surplus_kg=sum(item.available_kg for item in inventories),
            matched_kg=sum(
                item.reserved_kg + item.in_transit_kg + item.delivered_kg for item in inventories
            ),
            food_in_transit_kg=sum(item.in_transit_kg for item in inventories),
            food_at_risk_kg=sum(item.available_kg for item in inventories),
            active_deliveries=len(active_deliveries),
            community_demand_count=sum(bool(community.needs) for community in communities),
            rescued_kg=sum(item.delivered_kg for item in inventories),
            active_donations=sum(item.available_kg > 0 for item in inventories),
        )
        urgent = next(
            (donation for donation in donations if donation.donation_id == "DON-001"), None
        )
        return GlobalDashboardResponse(
            kpis=kpis,
            donations=donations,
            inventories=inventories,
            deliveries=deliveries,
            communities=communities,
            drivers=drivers,
            agent_runs=summaries,
            capacity_alerts=alerts,
            urgent_donation=urgent or (donations[0] if donations else None),
            active_agent_decision=summaries[-1] if summaries else None,
            active_delivery=active_deliveries[0] if active_deliveries else None,
            capacity_change_highlight=alerts[-1] if alerts else None,
        )


def _status_timeline(status: DeliveryStatus, at: datetime) -> list[DeliveryStatusEvent]:
    ordered = [
        DeliveryStatus.CREATED,
        DeliveryStatus.DRIVER_ASSIGNED,
        DeliveryStatus.IN_TRANSIT,
        DeliveryStatus.ARRIVED,
    ]
    terminal = {
        DeliveryStatus.PARTIALLY_ACCEPTED,
        DeliveryStatus.COMPLETED,
        DeliveryStatus.REJECTED,
    }
    states = ordered[: ordered.index(status) + 1] if status in ordered else [*ordered, status]
    if status in terminal and states[-1] is not status:
        states.append(status)
    return [
        DeliveryStatusEvent(
            sequence=index, status=item, label=item.value.replace("_", " "), occurred_at=at
        )
        for index, item in enumerate(states)
    ]


def _acceptance_outcome(accepted_kg: int, remaining_kg: int) -> DeliveryAcceptanceOutcome:
    if accepted_kg == 0:
        return DeliveryAcceptanceOutcome.REJECTED
    if remaining_kg == 0:
        return DeliveryAcceptanceOutcome.FULL
    return DeliveryAcceptanceOutcome.PARTIAL


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"
