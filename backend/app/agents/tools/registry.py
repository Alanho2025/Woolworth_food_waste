"""The canonical eighteen FoodFlow tools, with injected application dependencies."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from backend.app.agents.bounds import AgentBounds, call_tool_within_budget
from backend.app.agents.schemas import (
    AcceptanceResultView,
    AssignDriverInput,
    CalculateRouteInput,
    CandidateListResult,
    CommunityCapacityView,
    CreateDeliveryOrderInput,
    CreateRematchedDeliveryInput,
    DeliveryOrderResult,
    DonationView,
    DriverListResult,
    GetAvailableDriversInput,
    GetCommunityCapacityInput,
    GetDonationInput,
    InventoryView,
    ListCandidateCommunitiesInput,
    RecordPartialAcceptanceInput,
    ReleaseRemainingInventoryInput,
    ReservationProjection,
    ReserveInventoryInput,
    ReserveRecipientCapacityInput,
    RouteResult,
    ToolFailure,
    ToolResult,
    UpdateDriverRouteInput,
    ValidateCategoryAcceptanceInput,
    ValidateDriverCapacityInput,
    ValidateReceivingWindowInput,
    ValidateRecipientCapacityInput,
    ValidateStorageCompatibilityInput,
    ValidationResult,
)
from backend.app.application.allocate_donation import (
    AllocateDonation,
    AllocationCommand,
    CandidateQuery,
)
from backend.app.application.record_acceptance import RecordAcceptance
from backend.app.application.rematch import RematchRemaining
from backend.app.contracts.core import CommunityOrganisation, DonationInventory
from backend.app.domain.errors import ErrorCode, FoodFlowError
from backend.app.domain.policies import quantity_integrity
from backend.app.domain.policies.driver import validate_driver_capacity as check_driver_capacity
from backend.app.domain.policies.eligibility import (
    validate_category_acceptance as check_category_acceptance,
)
from backend.app.domain.policies.eligibility import (
    validate_receiving_window as check_receiving_window,
)
from backend.app.domain.policies.eligibility import (
    validate_recipient_capacity as check_recipient_capacity,
)
from backend.app.domain.policies.eligibility import (
    validate_storage_compatibility as check_storage_compatibility,
)
from backend.app.domain.ports import RouteSimulator, UnitOfWork

CANONICAL_TOOL_NAMES: tuple[str, ...] = (
    "get_donation",
    "list_candidate_communities",
    "get_community_capacity",
    "get_available_drivers",
    "calculate_route",
    "validate_category_acceptance",
    "validate_storage_compatibility",
    "validate_recipient_capacity",
    "validate_receiving_window",
    "validate_driver_capacity",
    "reserve_inventory",
    "reserve_recipient_capacity",
    "create_delivery_order",
    "assign_driver",
    "record_partial_acceptance",
    "release_remaining_inventory",
    "create_rematched_delivery",
    "update_driver_route",
)

ToolFunction = Callable[..., Awaitable[ToolResult]]


@dataclass(frozen=True)
class ToolDependencies:
    uow: UnitOfWork
    allocator: AllocateDonation
    acceptance: RecordAcceptance
    rematcher: RematchRemaining
    routes: RouteSimulator
    bounds: AgentBounds


class FoodFlowTools:
    """Thin typed adapters; all decisions and writes stay in policies/use cases."""

    def __init__(self, dependencies: ToolDependencies) -> None:
        self._deps = dependencies

    async def _invoke(self, name: str, work: Callable[[], ToolResult]) -> ToolResult:
        try:
            return await call_tool_within_budget(name, work, self._deps.bounds)
        except FoodFlowError as error:
            return ToolFailure(code=error.code, detail=error.detail)
        except Exception:
            return ToolFailure(
                code=ErrorCode.TOOL_INTERNAL_FAILURE,
                detail="internal tool failure",
            )

    async def get_donation(self, request: GetDonationInput) -> ToolResult:
        """Read one donation and its current quantity ledger; never write."""
        return await self._invoke("get_donation", lambda: self._get_donation(request))

    def _get_donation(self, request: GetDonationInput) -> ToolResult:
        with self._deps.uow as uow:
            donation = uow.donations.get(request.donation_id)
            inventory = uow.donations.get_inventory(request.donation_id)
            if donation is None or inventory is None:
                return ToolFailure(code=ErrorCode.TOOL_NOT_FOUND, detail="donation not found")
            return DonationView(donation=donation, inventory=inventory)

    async def list_candidate_communities(
        self, request: ListCandidateCommunitiesInput
    ) -> ToolResult:
        """Return complete facts for every candidate, excluded candidates included."""
        return await self._invoke(
            "list_candidate_communities",
            lambda: self._list_candidate_communities(request),
        )

    def _list_candidate_communities(self, request: ListCandidateCommunitiesInput) -> ToolResult:
        if request.declined_order_id is not None:
            context = self._deps.rematcher.context_for(
                request.declined_order_id, request.required_kg
            )
            candidates = self._deps.rematcher.propose(context).candidates
        else:
            candidates = self._deps.allocator.assess_candidates(
                CandidateQuery(
                    donation_id=request.donation_id,
                    required_kg=request.required_kg,
                    origin=request.origin,
                    declined_community_ids=request.declined_community_ids,
                )
            )
        return CandidateListResult(required_kg=request.required_kg, candidates=candidates)

    async def get_community_capacity(self, request: GetCommunityCapacityInput) -> ToolResult:
        """Read need and capacity as distinct facts; never write."""
        return await self._invoke(
            "get_community_capacity", lambda: self._get_community_capacity(request)
        )

    def _get_community_capacity(self, request: GetCommunityCapacityInput) -> ToolResult:
        with self._deps.uow as uow:
            community = uow.communities.get(request.community_id)
            if community is None:
                return ToolFailure(code=ErrorCode.TOOL_NOT_FOUND, detail="community not found")
            return CommunityCapacityView(
                community_id=community.community_id,
                name=community.name,
                needs=community.needs,
                remaining_capacity_kg=community.remaining_capacity_kg,
                receiving_window=community.receiving_window,
                is_open=community.is_open,
            )

    async def get_available_drivers(self, request: GetAvailableDriversInput) -> ToolResult:
        """Read feasible available drivers for one quantity; never write."""
        return await self._invoke(
            "get_available_drivers",
            lambda: DriverListResult(
                quantity_kg=request.quantity_kg,
                drivers=self._deps.allocator.feasible_drivers(
                    request.donation_id, request.quantity_kg
                ),
            ),
        )

    async def calculate_route(self, request: CalculateRouteInput) -> ToolResult:
        """Calculate one deterministic, explicitly simulated route."""
        return await self._invoke(
            "calculate_route",
            lambda: RouteResult(route=self._deps.routes.route(request.origin, request.destination)),
        )

    async def validate_category_acceptance(
        self, request: ValidateCategoryAcceptanceInput
    ) -> ToolResult:
        """Delegate category acceptance to the P1 eligibility policy."""
        return await self._validation(
            "validate_category_acceptance",
            request.community_id,
            lambda community: check_category_acceptance(community, request.category),
        )

    async def validate_storage_compatibility(
        self, request: ValidateStorageCompatibilityInput
    ) -> ToolResult:
        """Delegate storage compatibility to the P1 eligibility policy."""
        return await self._validation(
            "validate_storage_compatibility",
            request.community_id,
            lambda community: check_storage_compatibility(community, request.storage_type),
        )

    async def validate_recipient_capacity(
        self, request: ValidateRecipientCapacityInput
    ) -> ToolResult:
        """Delegate recipient capacity to the P1 eligibility policy."""
        return await self._validation(
            "validate_recipient_capacity",
            request.community_id,
            lambda community: check_recipient_capacity(community, request.required_kg),
        )

    async def validate_receiving_window(self, request: ValidateReceivingWindowInput) -> ToolResult:
        """Delegate receiving-window validation to the P1 eligibility policy."""
        return await self._validation(
            "validate_receiving_window",
            request.community_id,
            lambda community: check_receiving_window(community, request.route),
        )

    async def validate_driver_capacity(self, request: ValidateDriverCapacityInput) -> ToolResult:
        """Delegate availability and vehicle capacity to the P1 driver policy."""
        return await self._invoke(
            "validate_driver_capacity", lambda: self._validate_driver_capacity(request)
        )

    def _validate_driver_capacity(self, request: ValidateDriverCapacityInput) -> ToolResult:
        with self._deps.uow as uow:
            driver = uow.drivers.get(request.driver_id)
            if driver is None:
                return ToolFailure(code=ErrorCode.TOOL_NOT_FOUND, detail="driver not found")
            check_driver_capacity(driver, request.required_kg)
            return ValidationResult(ok=True)

    async def _validation(
        self,
        name: str,
        community_id: str,
        validate: Callable[[CommunityOrganisation], None],
    ) -> ToolResult:
        def work() -> ToolResult:
            with self._deps.uow as uow:
                community = uow.communities.get(community_id)
                if community is None:
                    return ToolFailure(code=ErrorCode.TOOL_NOT_FOUND, detail="community not found")
                validate(community)
                return ValidationResult(ok=True)

        return await self._invoke(name, work)

    async def reserve_inventory(self, request: ReserveInventoryInput) -> ToolResult:
        """Project inventory reservation; create_delivery_order commits atomically."""
        return await self._invoke("reserve_inventory", lambda: self._reserve_inventory(request))

    def _reserve_inventory(self, request: ReserveInventoryInput) -> ToolResult:
        with self._deps.uow as uow:
            inventory = uow.donations.get_inventory(request.donation_id)
            if inventory is None:
                return ToolFailure(code=ErrorCode.TOOL_NOT_FOUND, detail="inventory not found")
            projected = quantity_integrity.reserve(inventory, request.quantity_kg)
            return ReservationProjection(
                ok=True,
                quantity_kg=request.quantity_kg,
                available_kg_after=projected.available_kg,
            )

    async def reserve_recipient_capacity(
        self, request: ReserveRecipientCapacityInput
    ) -> ToolResult:
        """Project recipient reservation; create_delivery_order commits atomically."""
        return await self._invoke(
            "reserve_recipient_capacity",
            lambda: self._reserve_recipient_capacity(request),
        )

    def _reserve_recipient_capacity(self, request: ReserveRecipientCapacityInput) -> ToolResult:
        with self._deps.uow as uow:
            community = uow.communities.get(request.community_id)
            if community is None:
                return ToolFailure(code=ErrorCode.TOOL_NOT_FOUND, detail="community not found")
            check_recipient_capacity(community, request.quantity_kg)
            return ReservationProjection(
                ok=True,
                quantity_kg=request.quantity_kg,
                recipient_capacity_kg_after=(community.remaining_capacity_kg - request.quantity_kg),
            )

    async def create_delivery_order(self, request: CreateDeliveryOrderInput) -> ToolResult:
        """Atomically validate, reserve, and create an initial delivery order."""
        return await self._invoke(
            "create_delivery_order", lambda: self._create_delivery_order(request)
        )

    def _create_delivery_order(self, request: CreateDeliveryOrderInput) -> ToolResult:
        order = self._deps.allocator.execute(
            AllocationCommand(
                donation_id=request.donation_id,
                community_id=request.community_id,
                quantity_kg=request.quantity_kg,
                driver_id=request.driver_id,
                origin=request.origin,
            )
        )
        return DeliveryOrderResult(order=order, inventory=self._inventory(order.donation_id))

    async def assign_driver(self, request: AssignDriverInput) -> ToolResult:
        """Assign the chosen feasible driver through the allocation use case."""
        return await self._invoke("assign_driver", lambda: self._assign_driver(request))

    def _assign_driver(self, request: AssignDriverInput) -> ToolResult:
        order = self._deps.allocator.assign_driver(request.order_id, request.driver_id)
        return DeliveryOrderResult(order=order, inventory=self._inventory(order.donation_id))

    async def record_partial_acceptance(self, request: RecordPartialAcceptanceInput) -> ToolResult:
        """Atomically record accepted and remaining quantities through the use case."""
        return await self._invoke(
            "record_partial_acceptance", lambda: self._record_partial_acceptance(request)
        )

    def _record_partial_acceptance(self, request: RecordPartialAcceptanceInput) -> ToolResult:
        result = self._deps.acceptance.execute(
            request.order_id, request.accepted_kg, request.reason
        )
        return AcceptanceResultView(
            order=result.order,
            planned_kg=result.outcome.planned_kg,
            accepted_kg=result.outcome.accepted_kg,
            remaining_kg=result.outcome.remaining_kg,
            corrected_capacity_kg=result.outcome.corrected_capacity_kg,
            requires_rematch=result.outcome.requires_rematch,
            inventory=result.inventory,
        )

    async def release_remaining_inventory(
        self, request: ReleaseRemainingInventoryInput
    ) -> ToolResult:
        """Read the already-atomic acceptance release; never move quantity twice."""
        return await self._invoke(
            "release_remaining_inventory",
            lambda: self._released_inventory(request),
        )

    def _released_inventory(self, request: ReleaseRemainingInventoryInput) -> ToolResult:
        with self._deps.uow as uow:
            acceptance = uow.acceptances.get(request.order_id)
            if acceptance is None:
                return ToolFailure(code=ErrorCode.TOOL_NOT_FOUND, detail="acceptance not found")
            inventory = uow.donations.get_inventory(acceptance.donation_id)
            if inventory is None:
                return ToolFailure(code=ErrorCode.TOOL_NOT_FOUND, detail="inventory not found")
            return InventoryView(
                inventory=inventory,
                detail=f"{acceptance.remaining_kg} kg already returned atomically",
            )

    async def create_rematched_delivery(self, request: CreateRematchedDeliveryInput) -> ToolResult:
        """Create only the persisted remainder's replacement delivery."""
        return await self._invoke(
            "create_rematched_delivery",
            lambda: self._create_rematched_delivery(request),
        )

    def _create_rematched_delivery(self, request: CreateRematchedDeliveryInput) -> ToolResult:
        context = self._deps.rematcher.context_for(request.declined_order_id, request.remaining_kg)
        order = self._deps.rematcher.execute(context, request.community_id)
        return DeliveryOrderResult(order=order, inventory=self._inventory(order.donation_id))

    async def update_driver_route(self, request: UpdateDriverRouteInput) -> ToolResult:
        """Persist the deterministic route attached to the current delivery leg."""
        return await self._invoke("update_driver_route", lambda: self._update_driver_route(request))

    def _update_driver_route(self, request: UpdateDriverRouteInput) -> ToolResult:
        order = self._deps.allocator.update_route(request.order_id)
        return DeliveryOrderResult(order=order, inventory=self._inventory(order.donation_id))

    def _inventory(self, donation_id: str) -> DonationInventory:
        with self._deps.uow as uow:
            inventory = uow.donations.get_inventory(donation_id)
            if inventory is None:
                raise FoodFlowError(ErrorCode.NOT_FOUND, "inventory not found")
            return inventory


def build_tool_functions(dependencies: ToolDependencies) -> list[ToolFunction]:
    """Build exactly the canonical list, in the same order as both specifications."""
    tools = FoodFlowTools(dependencies)
    functions: list[ToolFunction] = [getattr(tools, name) for name in CANONICAL_TOOL_NAMES]
    if tuple(function.__name__ for function in functions) != CANONICAL_TOOL_NAMES:
        raise RuntimeError("canonical tool registry drifted from the specification")
    return functions
