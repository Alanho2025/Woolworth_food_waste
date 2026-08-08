"""Remaining-inventory arithmetic through the real quantity transitions."""

from __future__ import annotations

from backend.app.contracts.core import DonationInventory
from backend.app.domain.policies.quantity_integrity import (
    deliver,
    dispatch,
    reserve,
    return_to_available,
)


def fresh_inventory() -> DonationInventory:
    return DonationInventory(
        donation_id="DON-EDGE",
        total_kg=60,
        available_kg=60,
        reserved_kg=0,
        in_transit_kg=0,
        delivered_kg=0,
    )


def test_accepting_thirty_five_returns_only_twenty_five_to_available_inventory() -> None:
    """60 DISPATCHED, 35 DELIVERED, 25 RETURNED -> ledger is 25/0/0/35."""
    dispatched = dispatch(reserve(fresh_inventory(), 60), 60)
    accepted = deliver(dispatched, 35)
    final = return_to_available(accepted, 25)

    assert final.model_dump(
        include={
            "available_kg",
            "reserved_kg",
            "in_transit_kg",
            "delivered_kg",
        }
    ) == {
        "available_kg": 25,
        "reserved_kg": 0,
        "in_transit_kg": 0,
        "delivered_kg": 35,
    }
    assert final.is_balanced is True


def test_returned_twenty_five_can_be_reserved_once_for_the_rematch_without_recreating_sixty() -> (
    None
):
    """35 DELIVERED + 25 AVAILABLE -> reserve rematch -> 25 reserved, total still 60."""
    dispatched = dispatch(reserve(fresh_inventory(), 60), 60)
    after_acceptance = return_to_available(deliver(dispatched, 35), 25)

    rematched = reserve(after_acceptance, 25)

    assert rematched.available_kg == 0
    assert rematched.reserved_kg == 25
    assert rematched.in_transit_kg == 0
    assert rematched.delivered_kg == 35
    assert rematched.is_balanced is True
