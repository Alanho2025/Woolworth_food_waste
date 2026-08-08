"""Driver hard constraints.

Availability and vehicle capacity are separate facts. A large vehicle that is
already assigned is not feasible; an available vehicle that is too small is not
feasible either. Application services and Agent tools delegate here instead of
reimplementing either rule.
"""

from __future__ import annotations

from backend.app.contracts.core import Driver
from backend.app.domain.errors import EligibilityError, ErrorCode
from backend.app.domain.quantity import require_kilograms


def validate_driver_capacity(driver: Driver, required_kg: int) -> None:
    """Raise a typed eligibility error unless ``driver`` can take the load."""
    required_kg = require_kilograms(required_kg, name="required_kg", positive=True)
    if not driver.is_available:
        raise EligibilityError(
            ErrorCode.DRIVER_UNAVAILABLE,
            f"{driver.name} is not currently available",
        )
    validate_vehicle_capacity(driver, required_kg)


def validate_vehicle_capacity(driver: Driver, required_kg: int) -> None:
    """Raise unless the vehicle fits the load, independent of assignment state."""
    required_kg = require_kilograms(required_kg, name="required_kg", positive=True)
    if driver.vehicle_capacity_kg < required_kg:
        raise EligibilityError(
            ErrorCode.DRIVER_CAPACITY_EXCEEDED,
            f"{driver.name}'s vehicle carries {driver.vehicle_capacity_kg} kg, "
            f"less than the {required_kg} kg required",
        )
