"""The quantity invariant.

    available + reserved + in_transit + delivered == total

AGENTS_FoodFlow.md 8.4 calls quantity integrity blocker-level. Requirement.md
16.7 states it as a test -- "the remaining 25 kg is not duplicated" -- but a
test proves one path and an invariant proves all of them. Every ledger movement
in the system goes through one of the functions below, and each of them asserts
the invariant BEFORE and AFTER the move.

Every quantity is an integer number of kilograms. With IEEE-754 floats the
invariant is not reliably decidable: the reserve / release / re-reserve cycle
can leave a residue that makes an exactly-correct system report a violation.
See docs/assumption_audit.md C-7 and docs/phase_review_findings.md R-17.
"""

from __future__ import annotations

from backend.app.contracts.core import DonationInventory
from backend.app.domain.errors import ErrorCode, QuantityIntegrityError
from backend.app.domain.quantity import require_kilograms


def assert_balanced(inventory: DonationInventory, *, at: str = "quantity_integrity") -> None:
    """Raise unless the four components sum to the donation total.

    `at` names the transition, so a violation identifies its own cause instead
    of surfacing as a mismatched number three screens later.
    """
    if not inventory.is_balanced:
        total = (
            inventory.available_kg
            + inventory.reserved_kg
            + inventory.in_transit_kg
            + inventory.delivered_kg
        )
        raise QuantityIntegrityError(
            ErrorCode.QUANTITY_INTEGRITY_VIOLATION,
            f"{at}: donation {inventory.donation_id} components sum to {total} kg "
            f"but the total is {inventory.total_kg} kg "
            f"(available={inventory.available_kg}, reserved={inventory.reserved_kg}, "
            f"in_transit={inventory.in_transit_kg}, delivered={inventory.delivered_kg})",
        )


def reserve(inventory: DonationInventory, quantity_kg: int) -> DonationInventory:
    """available -> reserved. Step 3 of the allocation transaction."""
    return _move(inventory, quantity_kg, "available_kg", "reserved_kg", at="reserve")


def release_reservation(inventory: DonationInventory, quantity_kg: int) -> DonationInventory:
    """reserved -> available. Undoes a reservation whose order never shipped."""
    return _move(inventory, quantity_kg, "reserved_kg", "available_kg", at="release_reservation")


def dispatch(inventory: DonationInventory, quantity_kg: int) -> DonationInventory:
    """reserved -> in_transit. The driver has the food."""
    return _move(inventory, quantity_kg, "reserved_kg", "in_transit_kg", at="dispatch")


def deliver(inventory: DonationInventory, quantity_kg: int) -> DonationInventory:
    """in_transit -> delivered. The accepted quantity, preserved."""
    return _move(inventory, quantity_kg, "in_transit_kg", "delivered_kg", at="deliver")


def return_to_available(inventory: DonationInventory, quantity_kg: int) -> DonationInventory:
    """in_transit -> available. ONLY the rejected quantity returns to the network.

    This is the movement that Requirement.md 16.7 watches: it must not create a
    kilogram, and the accepted quantity must not be recreated alongside it.
    """
    return _move(inventory, quantity_kg, "in_transit_kg", "available_kg", at="return_to_available")


def _move(
    inventory: DonationInventory,
    quantity_kg: int,
    source: str,
    destination: str,
    *,
    at: str,
) -> DonationInventory:
    assert_balanced(inventory, at=f"{at}:before")
    try:
        quantity_kg = require_kilograms(quantity_kg, name="quantity_kg")
    except (TypeError, ValueError) as error:
        raise QuantityIntegrityError(
            ErrorCode.QUANTITY_INTEGRITY_VIOLATION,
            f"{at}: {error}",
        ) from error
    if quantity_kg == 0:
        return inventory

    held: int = getattr(inventory, source)
    if held < quantity_kg:
        raise QuantityIntegrityError(
            ErrorCode.INSUFFICIENT_INVENTORY,
            f"{at}: donation {inventory.donation_id} holds {held} kg in {source}, "
            f"which is less than the {quantity_kg} kg requested",
        )

    moved = inventory.model_copy(
        update={
            source: held - quantity_kg,
            destination: getattr(inventory, destination) + quantity_kg,
        }
    )
    assert_balanced(moved, at=f"{at}:after")
    return moved
