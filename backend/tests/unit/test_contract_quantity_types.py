"""Strict whole-kilogram validation at the real Pydantic contract boundary."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from backend.app.contracts.core import (
    CommunityOrganisation,
    DeliveryOrder,
    DeliveryStatus,
    DonationInventory,
    Driver,
    FoodCategory,
    FoodItem,
    Location,
    RouteLeg,
    StorageType,
    TimeWindow,
)

AUCKLAND = ZoneInfo("Pacific/Auckland")
NOW = datetime(2026, 8, 8, 15, 45, tzinfo=AUCKLAND)
LOCATION = Location(name="Origin", latitude=-36.87, longitude=174.76)


@pytest.mark.parametrize("invalid", [25.0, True, "25"])
def test_food_item_quantity_rejects_float_bool_and_numeric_string(invalid: object) -> None:
    """NON-INTEGER-RUNTIME QUANTITY -> validate FoodItem -> ValidationError."""
    with pytest.raises(ValidationError):
        FoodItem.model_validate(
            {
                "item_name": "Vegetables",
                "category": "vegetables",
                "quantity": invalid,
                "unit": "kg",
                "storage_type": "ambient",
                "delivery_deadline": NOW,
            }
        )


@pytest.mark.parametrize("invalid", [25.0, True, "25"])
def test_inventory_component_rejects_float_bool_and_numeric_string(invalid: object) -> None:
    """NON-INTEGER-RUNTIME LEDGER VALUE -> validate inventory -> ValidationError."""
    with pytest.raises(ValidationError):
        DonationInventory.model_validate(
            {
                "donation_id": "DON-STRICT",
                "total_kg": 60,
                "available_kg": invalid,
                "reserved_kg": 35,
                "in_transit_kg": 0,
                "delivered_kg": 0,
            }
        )


@pytest.mark.parametrize("field", ["declared_capacity_kg", "remaining_capacity_kg"])
@pytest.mark.parametrize("invalid", [25.0, True, "25"])
def test_community_capacity_fields_reject_float_bool_and_numeric_string(
    field: str, invalid: object
) -> None:
    """NON-INTEGER-RUNTIME COMMUNITY CAPACITY -> validate -> ValidationError."""
    payload: dict[str, object] = {
        "community_id": "C",
        "name": "Community C",
        "location": LOCATION,
        "accepted_categories": [FoodCategory.VEGETABLES],
        "supported_storage": [StorageType.AMBIENT],
        "needs": [],
        "declared_capacity_kg": 25,
        "remaining_capacity_kg": 25,
        "receiving_window": TimeWindow(start=NOW, end=NOW.replace(hour=20)),
        "is_open": True,
    }
    payload[field] = invalid
    with pytest.raises(ValidationError):
        CommunityOrganisation.model_validate(payload)


@pytest.mark.parametrize("invalid", [60.0, True, "60"])
def test_driver_capacity_rejects_float_bool_and_numeric_string(invalid: object) -> None:
    """NON-INTEGER-RUNTIME VEHICLE CAPACITY -> validate Driver -> ValidationError."""
    with pytest.raises(ValidationError):
        Driver.model_validate(
            {
                "driver_id": "DRV-STRICT",
                "name": "Driver",
                "start_location": LOCATION,
                "vehicle_capacity_kg": invalid,
                "is_available": True,
            }
        )


@pytest.mark.parametrize("invalid", [25.0, True, "25"])
def test_delivery_order_quantity_rejects_float_bool_and_numeric_string(invalid: object) -> None:
    """NON-INTEGER-RUNTIME ORDER QUANTITY -> validate DeliveryOrder -> ValidationError."""
    destination = Location(name="Destination", latitude=-36.90, longitude=174.80)
    route = RouteLeg(
        origin=LOCATION,
        destination=destination,
        polyline=[(-36.87, 174.76), (-36.90, 174.80)],
        distance_km=5.0,
        duration_minutes=10,
        eta=NOW.replace(hour=16),
        simulated=True,
    )
    with pytest.raises(ValidationError):
        DeliveryOrder.model_validate(
            {
                "order_id": "DO-STRICT",
                "donation_id": "DON-STRICT",
                "origin": LOCATION,
                "destination_community_id": "D",
                "quantity_kg": invalid,
                "driver_id": "DRV-1",
                "route": route,
                "status": DeliveryStatus.CREATED,
                "deadline": NOW.replace(hour=19),
                "is_rematch": True,
            }
        )


@pytest.mark.parametrize("invalid", [0, -1])
def test_positive_donation_quantity_rejects_zero_and_negative_values(invalid: int) -> None:
    """ZERO/NEGATIVE DONATION QUANTITY -> validate FoodItem -> ValidationError."""
    with pytest.raises(ValidationError):
        FoodItem(
            item_name="Vegetables",
            category=FoodCategory.VEGETABLES,
            quantity=invalid,
            storage_type=StorageType.AMBIENT,
            delivery_deadline=NOW,
        )
