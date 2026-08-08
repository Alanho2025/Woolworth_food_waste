"""The delivery-order state machine.

AGENTS_FoodFlow.md 8.3 lists "create an invalid delivery-state transition" among
the allocations backend validation MUST reject, so the legal moves are a table
here rather than a set of `if` statements scattered across the application
services.
"""

from __future__ import annotations

from backend.app.contracts.core import DeliveryOrder, DeliveryStatus
from backend.app.domain.errors import ErrorCode, StateTransitionError

_ALLOWED: dict[DeliveryStatus, frozenset[DeliveryStatus]] = {
    DeliveryStatus.CREATED: frozenset({DeliveryStatus.DRIVER_ASSIGNED, DeliveryStatus.REJECTED}),
    DeliveryStatus.DRIVER_ASSIGNED: frozenset({DeliveryStatus.IN_TRANSIT, DeliveryStatus.REJECTED}),
    DeliveryStatus.IN_TRANSIT: frozenset({DeliveryStatus.ARRIVED, DeliveryStatus.REJECTED}),
    DeliveryStatus.ARRIVED: frozenset(
        {
            DeliveryStatus.PARTIALLY_ACCEPTED,
            DeliveryStatus.COMPLETED,
            DeliveryStatus.REJECTED,
        }
    ),
    # A partially accepted delivery is finished for its own quantity. The
    # remainder is a NEW order created by the rematch, never a mutation of this
    # one -- which is how the ledger stays balanced (C-7).
    DeliveryStatus.PARTIALLY_ACCEPTED: frozenset({DeliveryStatus.COMPLETED}),
    DeliveryStatus.COMPLETED: frozenset(),
    DeliveryStatus.REJECTED: frozenset(),
}

# Ordered path from creation to arrival, used to advance a delivery that the
# demo drove straight to the confirmation screen without stepping through the
# intermediate states one click at a time.
ARRIVAL_PATH: tuple[DeliveryStatus, ...] = (
    DeliveryStatus.CREATED,
    DeliveryStatus.DRIVER_ASSIGNED,
    DeliveryStatus.IN_TRANSIT,
    DeliveryStatus.ARRIVED,
)


def can_transition(current: DeliveryStatus, target: DeliveryStatus) -> bool:
    return target in _ALLOWED[current]


def assert_can_transition(current: DeliveryStatus, target: DeliveryStatus) -> None:
    if not can_transition(current, target):
        raise StateTransitionError(
            ErrorCode.INVALID_STATE_TRANSITION,
            f"A delivery cannot move from {current.value} to {target.value}",
        )


def transition(order: DeliveryOrder, target: DeliveryStatus) -> DeliveryOrder:
    """Return the order in its new state, or raise a typed error."""
    assert_can_transition(order.status, target)
    return order.model_copy(update={"status": target})


def steps_to_arrival(current: DeliveryStatus) -> tuple[DeliveryStatus, ...]:
    """The remaining legal states between `current` and ARRIVED.

    Empty if the order has already arrived; raises if it can never arrive.
    """
    if current is DeliveryStatus.ARRIVED:
        return ()
    if current not in ARRIVAL_PATH:
        raise StateTransitionError(
            ErrorCode.INVALID_STATE_TRANSITION,
            f"A delivery in {current.value} can no longer arrive",
        )
    index = ARRIVAL_PATH.index(current)
    return ARRIVAL_PATH[index + 1 :]
