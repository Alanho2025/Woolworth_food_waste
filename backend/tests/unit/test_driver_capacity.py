"""Driver-capacity hard constraints through the real P1 policy."""

from __future__ import annotations

import pytest

from backend.app.contracts.core import Driver, Location
from backend.app.domain.errors import EligibilityError, ErrorCode
from backend.app.domain.policies.driver import validate_driver_capacity


def driver(*, capacity_kg: int, is_available: bool = True) -> Driver:
    return Driver(
        driver_id="DRV-EDGE",
        name="P1 Driver",
        start_location=Location(name="Depot", latitude=-36.87, longitude=174.77),
        vehicle_capacity_kg=capacity_kg,
        is_available=is_available,
    )


def test_available_driver_with_capacity_exactly_equal_to_order_is_valid() -> None:
    """AVAILABLE 60 KG DRIVER + 60 KG ORDER -> validate -> no error."""
    validate_driver_capacity(driver(capacity_kg=60), required_kg=60)


def test_available_driver_below_required_capacity_raises_typed_capacity_error() -> None:
    """AVAILABLE 59 KG DRIVER + 60 KG ORDER -> validate -> DRIVER_CAPACITY_EXCEEDED."""
    with pytest.raises(EligibilityError) as raised:
        validate_driver_capacity(driver(capacity_kg=59), required_kg=60)
    assert raised.value.code is ErrorCode.DRIVER_CAPACITY_EXCEEDED


def test_unavailable_driver_is_rejected_before_its_other_constraints() -> None:
    """UNAVAILABLE UNDERSIZED DRIVER -> validate -> DRIVER_UNAVAILABLE first."""
    with pytest.raises(EligibilityError) as raised:
        validate_driver_capacity(driver(capacity_kg=40, is_available=False), required_kg=60)
    assert raised.value.code is ErrorCode.DRIVER_UNAVAILABLE
