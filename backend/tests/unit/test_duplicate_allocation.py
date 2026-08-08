"""Duplicate-allocation prevention and the blocker-level quantity invariant."""

from __future__ import annotations

import pytest

from backend.app.contracts.core import DonationInventory
from backend.app.domain.errors import ErrorCode, QuantityIntegrityError
from backend.app.domain.policies.quantity_integrity import (
    assert_balanced,
    deliver,
    dispatch,
    reserve,
    return_to_available,
)


def inventory() -> DonationInventory:
    return DonationInventory(
        donation_id="DON-DUP",
        total_kg=60,
        available_kg=60,
        reserved_kg=0,
        in_transit_kg=0,
        delivered_kg=0,
    )


def test_reserving_the_same_sixty_kilograms_twice_is_rejected_without_mutating_first_result() -> (
    None
):
    """60 ALREADY RESERVED -> reserve another 60 -> typed insufficient-inventory error."""
    first = reserve(inventory(), 60)

    with pytest.raises(QuantityIntegrityError) as raised:
        reserve(first, 60)

    assert raised.value.code is ErrorCode.INSUFFICIENT_INVENTORY
    assert first.available_kg == 0
    assert first.reserved_kg == 60
    assert first.is_balanced is True


def test_returning_the_same_twenty_five_kilograms_twice_is_rejected() -> None:
    """25 ALREADY RETURNED -> return it again -> no duplicate inventory is created."""
    dispatched = dispatch(reserve(inventory(), 60), 60)
    settled = return_to_available(deliver(dispatched, 35), 25)

    with pytest.raises(QuantityIntegrityError) as raised:
        return_to_available(settled, 25)

    assert raised.value.code is ErrorCode.INSUFFICIENT_INVENTORY
    assert settled.available_kg == 25
    assert settled.delivered_kg == 35
    assert settled.is_balanced is True


def test_deliberately_duplicated_ledger_raises_the_quantity_integrity_invariant() -> None:
    """60 RESERVED + DUPLICATED 25 IN TRANSIT -> assert invariant -> blocker error."""
    corrupted = DonationInventory.model_construct(
        donation_id="DON-DUP",
        total_kg=60,
        available_kg=0,
        reserved_kg=60,
        in_transit_kg=25,
        delivered_kg=0,
    )

    with pytest.raises(QuantityIntegrityError) as raised:
        assert_balanced(corrupted, at="deliberate duplicate")

    assert raised.value.code is ErrorCode.QUANTITY_INTEGRITY_VIOLATION
    assert "deliberate duplicate" in raised.value.detail
