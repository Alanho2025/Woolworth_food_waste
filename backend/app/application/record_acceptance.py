"""Record what a recipient actually took on arrival.

clean_code_spec 6.2 requires partial acceptance to preserve the accepted
quantity, return ONLY the rejected quantity to active inventory, avoid
duplicating quantity, and trigger rematching for only the remainder. All four
happen inside one transaction here; the rematch itself is a separate use case.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from backend.app.contracts.core import (
    AuditEvent,
    CommunityOrganisation,
    DeliveryOrder,
    DeliveryStatus,
    DonationInventory,
)
from backend.app.domain import delivery_state
from backend.app.domain.acceptance import AcceptanceRecord
from backend.app.domain.clock import Clock
from backend.app.domain.errors import EligibilityError, ErrorCode, FoodFlowError
from backend.app.domain.policies import quantity_integrity
from backend.app.domain.policies.partial_acceptance import (
    PartialAcceptanceOutcome,
    correct_declared_capacity,
    evaluate_acceptance,
)
from backend.app.domain.ports import UnitOfWork


@dataclass(frozen=True)
class AcceptanceResult:
    order: DeliveryOrder
    outcome: PartialAcceptanceOutcome
    inventory: DonationInventory
    community: CommunityOrganisation


class RecordAcceptance:
    """Apply the recipient's decision to the order, the ledger, and the capacity report."""

    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    def execute(self, order_id: str, accepted_kg: int, reason: str = "") -> AcceptanceResult:
        try:
            return self._execute(order_id, accepted_kg, reason)
        except FoodFlowError as error:
            self._record_failure(order_id, error)
            raise

    def _execute(self, order_id: str, accepted_kg: int, reason: str) -> AcceptanceResult:
        with self._uow as uow:
            order = uow.deliveries.get(order_id)
            if order is None:
                raise EligibilityError(ErrorCode.NOT_FOUND, f"Unknown delivery order {order_id}")

            inventory = uow.donations.get_inventory(order.donation_id)
            if inventory is None:
                raise EligibilityError(
                    ErrorCode.NOT_FOUND, f"Donation {order.donation_id} has no inventory ledger"
                )
            community = uow.communities.get(order.destination_community_id)
            if community is None:
                raise EligibilityError(
                    ErrorCode.NOT_FOUND,
                    f"Unknown community {order.destination_community_id}",
                )

            persisted = uow.acceptances.get(order_id)
            if persisted is not None:
                # Idempotent even after the 25 kg rematch has been reserved: the
                # original 35/25 confirmation is an immutable persisted fact,
                # never reconstructed from the donation's current aggregate ledger.
                return AcceptanceResult(
                    order=order,
                    outcome=_persisted_outcome(persisted),
                    inventory=inventory,
                    community=community,
                )
            if order.status in _SETTLED:
                raise EligibilityError(
                    ErrorCode.INVALID_STATE_TRANSITION,
                    f"Settled order {order_id} has no persisted acceptance record",
                )

            outcome = evaluate_acceptance(
                order_id=order.order_id,
                community_id=order.destination_community_id,
                planned_kg=order.quantity_kg,
                accepted_kg=accepted_kg,
            )

            arrived, inventory = self._advance_to_arrived(order, inventory)

            # Preserve the accepted quantity...
            inventory = quantity_integrity.deliver(inventory, outcome.accepted_kg)
            # ...and return ONLY the rejected quantity to active inventory.
            inventory = quantity_integrity.return_to_available(inventory, outcome.remaining_kg)
            quantity_integrity.assert_balanced(inventory, at="record_acceptance:settled")
            uow.donations.save_inventory(inventory)

            # C-3(a): the capacity report was wrong; correct it rather than
            # merely unreserving, or the recipient shows free capacity at zero
            # travel distance and the Agent may re-select it.
            corrected = (
                community
                if outcome.is_full_acceptance
                else correct_declared_capacity(community, outcome)
            )
            uow.communities.save(corrected)

            settled = delivery_state.transition(arrived, _settled_status(outcome))
            uow.deliveries.save(settled)
            uow.acceptances.add(
                AcceptanceRecord(
                    order_id=order.order_id,
                    donation_id=order.donation_id,
                    community_id=order.destination_community_id,
                    planned_kg=outcome.planned_kg,
                    accepted_kg=outcome.accepted_kg,
                    remaining_kg=outcome.remaining_kg,
                    reason=reason,
                    recorded_at=self._clock.now(),
                )
            )

            driver = uow.drivers.get(order.driver_id)
            if driver is not None and outcome.is_full_acceptance:
                uow.drivers.save(driver.model_copy(update={"is_available": True}))

            uow.audit.record(
                AuditEvent(
                    event_id=_new_id("AUD"),
                    donation_id=order.donation_id,
                    action="partial_acceptance_recorded",
                    detail=(
                        f"{community.name} accepted {outcome.accepted_kg} of "
                        f"{outcome.planned_kg} kg; {outcome.remaining_kg} kg returned to "
                        f"active inventory; declared capacity corrected to "
                        f"{outcome.corrected_capacity_kg} kg"
                        + (f"; reason: {reason}" if reason else "")
                    ),
                    occurred_at=self._clock.now(),
                    succeeded=True,
                )
            )
            uow.commit()
            return AcceptanceResult(
                order=settled, outcome=outcome, inventory=inventory, community=corrected
            )

    def _advance_to_arrived(
        self, order: DeliveryOrder, inventory: DonationInventory
    ) -> tuple[DeliveryOrder, DonationInventory]:
        """Walk the order to ARRIVED, moving the ledger with it.

        The pitch journey jumps from the driver screen to the confirmation
        screen; the intermediate states still have to be traversed legally, and
        the reserved kilograms still have to become in-transit kilograms before
        any of them can be delivered.
        """
        current = order
        for target in delivery_state.steps_to_arrival(order.status):
            if target is DeliveryStatus.IN_TRANSIT:
                inventory = quantity_integrity.dispatch(inventory, order.quantity_kg)
            current = delivery_state.transition(current, target)
        return current, inventory

    def _record_failure(self, order_id: str, error: FoodFlowError) -> None:
        with self._uow as uow:
            order = uow.deliveries.get(order_id)
            uow.audit.record_failure(
                AuditEvent(
                    event_id=_new_id("AUD"),
                    donation_id=order.donation_id if order else "",
                    action="partial_acceptance_failed",
                    detail=f"{error.code.value}: {error.detail}",
                    occurred_at=self._clock.now(),
                    succeeded=False,
                )
            )


_SETTLED = frozenset(
    {DeliveryStatus.PARTIALLY_ACCEPTED, DeliveryStatus.COMPLETED, DeliveryStatus.REJECTED}
)


def _settled_status(outcome: PartialAcceptanceOutcome) -> DeliveryStatus:
    if outcome.is_rejection:
        return DeliveryStatus.REJECTED
    if outcome.is_full_acceptance:
        return DeliveryStatus.COMPLETED
    return DeliveryStatus.PARTIALLY_ACCEPTED


def _persisted_outcome(record: AcceptanceRecord) -> PartialAcceptanceOutcome:
    """Return the original confirmation without consulting the mutable ledger."""
    return PartialAcceptanceOutcome(
        order_id=record.order_id,
        community_id=record.community_id,
        planned_kg=record.planned_kg,
        accepted_kg=record.accepted_kg,
        remaining_kg=record.remaining_kg,
        corrected_declared_capacity_kg=record.accepted_kg,
        corrected_remaining_capacity_kg=0,
    )


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"
