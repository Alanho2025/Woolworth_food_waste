"""Allocate a donation quantity to one recipient.

This module owns the allocation transaction boundary of clean_code_spec 6.2:

    1. validate current inventory
    2. validate recipient capacity
    3. reserve inventory
    4. reserve recipient capacity
    5. create delivery order
    6. create audit event

Any failure rolls the whole sequence back. The failure audit is written
*outside* the transaction, on a separate connection, because a literal reading
of 6.2 rolls back the audit record of a failed attempt and destroys exactly the
evidence AGENTS_FoodFlow.md 14 requires for diagnosis.
See docs/phase_review_findings.md R-10.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from backend.app.contracts.core import (
    AuditEvent,
    CandidateAssessment,
    DeliveryOrder,
    DeliveryStatus,
    DonationInventory,
    DonationRequest,
    Driver,
    FoodItem,
    Location,
)
from backend.app.domain import delivery_state
from backend.app.domain.clock import Clock
from backend.app.domain.errors import (
    EligibilityError,
    ErrorCode,
    FoodFlowError,
)
from backend.app.domain.policies import quantity_integrity
from backend.app.domain.policies.capacity import reserve_recipient_capacity
from backend.app.domain.policies.driver import (
    validate_driver_capacity,
    validate_vehicle_capacity,
)
from backend.app.domain.policies.eligibility import (
    AssessmentRequest,
    assess_candidates,
    validate_category_acceptance,
    validate_delivery_deadline,
    validate_receiving_window,
    validate_recipient_capacity,
    validate_storage_compatibility,
)
from backend.app.domain.ports import RouteSimulator, UnitOfWork

_ACTIVE_STATUSES = frozenset(
    {
        DeliveryStatus.CREATED,
        DeliveryStatus.DRIVER_ASSIGNED,
        DeliveryStatus.IN_TRANSIT,
        DeliveryStatus.ARRIVED,
        DeliveryStatus.PARTIALLY_ACCEPTED,
        DeliveryStatus.COMPLETED,
    }
)


@dataclass(frozen=True)
class AllocationCommand:
    """One placement, fully specified. The Agent proposes it; this layer validates it."""

    donation_id: str
    community_id: str
    quantity_kg: int
    driver_id: str
    origin: Location
    is_rematch: bool = False
    # Set for a rematch: the leg that was partially accepted, recorded in the
    # audit trail so the two orders are linked.
    supersedes_order_id: str = ""


@dataclass(frozen=True)
class CandidateQuery:
    donation_id: str
    required_kg: int
    origin: Location | None = None
    declined_community_ids: tuple[str, ...] = field(default_factory=tuple)


class AllocateDonation:
    """Assemble candidate facts, and commit one allocation atomically."""

    def __init__(self, uow: UnitOfWork, routes: RouteSimulator, clock: Clock) -> None:
        self._uow = uow
        self._routes = routes
        self._clock = clock

    # -- read -------------------------------------------------------------

    def assess_candidates(self, query: CandidateQuery) -> list[CandidateAssessment]:
        """Complete fact set for every community, including excluded ones (R-18)."""
        with self._uow as uow:
            donation = _require_donation(uow, query.donation_id)
            item = primary_item(donation)
            request = AssessmentRequest(
                origin=query.origin or donation.store_location,
                category=item.category,
                storage_type=item.storage_type,
                required_kg=query.required_kg,
                delivery_deadline=item.delivery_deadline,
                now=self._clock.now(),
                declined_community_ids=query.declined_community_ids,
            )
            return assess_candidates(request, uow.communities.list_all(), self._routes)

    def feasible_drivers(self, donation_id: str, quantity_kg: int) -> list[Driver]:
        """Available drivers whose vehicle can carry `quantity_kg`."""
        with self._uow as uow:
            _require_donation(uow, donation_id)
            return [
                d
                for d in uow.drivers.list_available()
                if d.is_available and d.vehicle_capacity_kg >= quantity_kg
            ]

    # -- write ------------------------------------------------------------

    def execute(self, command: AllocationCommand) -> DeliveryOrder:
        """Run the six-step allocation transaction, or roll it back entirely."""
        try:
            return self._execute(command)
        except FoodFlowError as error:
            self._record_failure(command, error)
            raise

    def _execute(self, command: AllocationCommand) -> DeliveryOrder:
        with self._uow as uow:
            donation = _require_donation(uow, command.donation_id)
            item = primary_item(donation)

            existing = _existing_order(uow, command)
            if existing is not None:
                # Action tools are idempotent where practical (clean_code_spec
                # 7.4): re-running an allocation the Agent already committed
                # returns the same order instead of duplicating quantity.
                return existing

            # 1. validate current inventory
            inventory = _require_inventory(uow, command.donation_id)
            quantity_integrity.assert_balanced(inventory, at="allocate:entry")
            if inventory.available_kg < command.quantity_kg:
                raise EligibilityError(
                    ErrorCode.INSUFFICIENT_INVENTORY,
                    f"Donation {command.donation_id} has {inventory.available_kg} kg available, "
                    f"less than the {command.quantity_kg} kg requested",
                )

            # 2. validate every recipient, route, and driver hard constraint.
            community = uow.communities.get(command.community_id)
            if community is None:
                raise EligibilityError(
                    ErrorCode.NOT_FOUND, f"Unknown community {command.community_id}"
                )
            route = self._routes.route(command.origin, community.location)
            validate_category_acceptance(community, item.category)
            validate_storage_compatibility(community, item.storage_type)
            validate_recipient_capacity(community, command.quantity_kg)
            validate_receiving_window(community, route)
            validate_delivery_deadline(route, item.delivery_deadline)

            driver = uow.drivers.get(command.driver_id)
            if driver is None:
                raise EligibilityError(ErrorCode.NOT_FOUND, f"Unknown driver {command.driver_id}")
            if _is_retained_rematch_driver(uow, command):
                validate_vehicle_capacity(driver, command.quantity_kg)
            else:
                validate_driver_capacity(driver, command.quantity_kg)

            # 3. reserve inventory
            uow.donations.save_inventory(quantity_integrity.reserve(inventory, command.quantity_kg))

            # 4. reserve recipient capacity
            uow.communities.save(reserve_recipient_capacity(community, command.quantity_kg))

            # 5. create delivery order
            order = DeliveryOrder(
                order_id=_new_id("ORD"),
                donation_id=command.donation_id,
                # Explicit, never implicitly the donating store: the rematched
                # leg departs from where the driver already stands (C-4).
                origin=command.origin,
                destination_community_id=command.community_id,
                quantity_kg=command.quantity_kg,
                driver_id=command.driver_id,
                route=route,
                status=DeliveryStatus.CREATED,
                deadline=item.delivery_deadline,
                is_rematch=command.is_rematch,
            )
            uow.deliveries.add(order)

            # 6. create audit event
            uow.audit.record(
                AuditEvent(
                    event_id=_new_id("AUD"),
                    donation_id=command.donation_id,
                    action="rematch_allocated" if command.is_rematch else "allocated",
                    detail=(
                        f"{command.quantity_kg} kg to {community.name} "
                        f"({community.community_id}) via driver {command.driver_id}"
                        + (
                            f", superseding {command.supersedes_order_id}"
                            if command.supersedes_order_id
                            else ""
                        )
                    ),
                    occurred_at=self._clock.now(),
                    succeeded=True,
                )
            )
            uow.commit()
            return order

    def assign_driver(self, order_id: str, driver_id: str) -> DeliveryOrder:
        """Attach a driver to a created order and take that driver off the pool."""
        with self._uow as uow:
            order = _require_order(uow, order_id)
            if order.status is DeliveryStatus.DRIVER_ASSIGNED and order.driver_id == driver_id:
                return order  # idempotent

            driver = uow.drivers.get(driver_id)
            if driver is None:
                raise EligibilityError(ErrorCode.NOT_FOUND, f"Unknown driver {driver_id}")
            if not driver.is_available and order.driver_id != driver_id:
                raise EligibilityError(
                    ErrorCode.DRIVER_UNAVAILABLE, f"{driver.name} is not available"
                )
            if driver.vehicle_capacity_kg < order.quantity_kg:
                raise EligibilityError(
                    ErrorCode.DRIVER_CAPACITY_EXCEEDED,
                    f"{driver.name}'s vehicle carries {driver.vehicle_capacity_kg} kg, "
                    f"less than the order's {order.quantity_kg} kg",
                )

            assigned = delivery_state.transition(
                order.model_copy(update={"driver_id": driver_id}),
                DeliveryStatus.DRIVER_ASSIGNED,
            )
            uow.deliveries.save(assigned)
            uow.drivers.save(driver.model_copy(update={"is_available": False}))
            uow.audit.record(
                AuditEvent(
                    event_id=_new_id("AUD"),
                    donation_id=order.donation_id,
                    action="driver_assigned",
                    detail=f"{driver.name} ({driver_id}) assigned to {order_id}",
                    occurred_at=self._clock.now(),
                    succeeded=True,
                )
            )
            uow.commit()
            return assigned

    def update_route(self, order_id: str) -> DeliveryOrder:
        """Recompute and persist an order's simulated route from its own origin."""
        with self._uow as uow:
            order = _require_order(uow, order_id)
            community = uow.communities.get(order.destination_community_id)
            if community is None:
                raise EligibilityError(
                    ErrorCode.NOT_FOUND,
                    f"Unknown community {order.destination_community_id}",
                )
            updated = order.model_copy(
                update={"route": self._routes.route(order.origin, community.location)}
            )
            uow.deliveries.save(updated)
            uow.commit()
            return updated

    def _record_failure(self, command: AllocationCommand, error: FoodFlowError) -> None:
        """Durable evidence of a rejected attempt, written outside the transaction."""
        with self._uow as uow:
            uow.audit.record_failure(
                AuditEvent(
                    event_id=_new_id("AUD"),
                    donation_id=command.donation_id,
                    action="allocation_failed",
                    detail=f"{error.code.value}: {error.detail}",
                    occurred_at=self._clock.now(),
                    succeeded=False,
                )
            )


# --------------------------------------------------------------------------
# Shared helpers. Kept here because every application service needs them and
# a separate `helpers` module is exactly the dumping ground clean_code_spec 3
# prohibits.
# --------------------------------------------------------------------------


def primary_item(donation: DonationRequest) -> FoodItem:
    """The item the journey allocates.

    Requirement.md 1 pins the pitch scenario to a single line item (60 kg of
    ambient vegetables). Multi-item donations are out of scope for the MVP, so
    this is the one place that assumption is stated rather than assumed in five.
    """
    return donation.items[0]


def _require_donation(uow: UnitOfWork, donation_id: str) -> DonationRequest:
    donation = uow.donations.get(donation_id)
    if donation is None:
        raise EligibilityError(ErrorCode.NOT_FOUND, f"Unknown donation {donation_id}")
    return donation


def _require_inventory(uow: UnitOfWork, donation_id: str) -> DonationInventory:
    inventory = uow.donations.get_inventory(donation_id)
    if inventory is None:
        raise EligibilityError(
            ErrorCode.NOT_FOUND, f"Donation {donation_id} has no inventory ledger"
        )
    return inventory


def _require_order(uow: UnitOfWork, order_id: str) -> DeliveryOrder:
    order = uow.deliveries.get(order_id)
    if order is None:
        raise EligibilityError(ErrorCode.NOT_FOUND, f"Unknown delivery order {order_id}")
    return order


def _existing_order(uow: UnitOfWork, command: AllocationCommand) -> DeliveryOrder | None:
    for order in uow.deliveries.list_for_donation(command.donation_id):
        if (
            order.destination_community_id == command.community_id
            and order.quantity_kg == command.quantity_kg
            and order.status in _ACTIVE_STATUSES
        ):
            return order
    return None


def _is_retained_rematch_driver(uow: UnitOfWork, command: AllocationCommand) -> bool:
    """Allow the already-assigned driver to carry the remainder from Community A."""
    if not command.is_rematch or not command.supersedes_order_id:
        return False
    previous = uow.deliveries.get(command.supersedes_order_id)
    return (
        previous is not None
        and previous.donation_id == command.donation_id
        and previous.driver_id == command.driver_id
        and previous.status in {DeliveryStatus.PARTIALLY_ACCEPTED, DeliveryStatus.REJECTED}
    )


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"
