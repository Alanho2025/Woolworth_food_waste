"""The demo world, built from `backend.app.contracts.core` only.

This is a *test* world, not the seed. `backend/app/seed/` is owned by another
worker and is exercised by the integration suite; the unit suite must stay pure
and must not depend on a database.

Every number here comes from Requirement.md section 1:

  donation   60 kg fresh vegetables, ambient, pickup 16:00-17:00, deadline 19:00
  Community A  urgently needs vegetables, can accept 60 kg, open
  Community B  does not accept fresh vegetables
  Community C  accepts vegetables, only 10 kg remaining capacity
  Community D  accepts vegetables, 30 kg remaining capacity, open

Auckland local times are constructed through ZoneInfo("Pacific/Auckland") and
never through a literal +12:00 offset (domain/clock.py, assumption_audit C-1).
"""

from __future__ import annotations

from datetime import datetime, timedelta

from backend.app.contracts.core import (
    CommunityNeed,
    CommunityOrganisation,
    DonationInventory,
    DonationRequest,
    Driver,
    FoodCategory,
    FoodItem,
    Location,
    NeedLevel,
    RouteLeg,
    StorageType,
    TimeWindow,
)
from backend.app.domain.clock import AUCKLAND

DEMO_DATE = (2026, 8, 8)

STORE_LOCATION = Location(name="Woolworths Mount Eden", latitude=-36.8776, longitude=174.7615)

COMMUNITY_A_ID = "COM-A"
COMMUNITY_B_ID = "COM-B"
COMMUNITY_C_ID = "COM-C"
COMMUNITY_D_ID = "COM-D"

DONATION_ID = "DON-001"
DONATION_TOTAL_KG = 60
ACCEPTED_KG = 35
REMAINING_KG = 25


def auckland(hour: int, minute: int = 0) -> datetime:
    """An instant on the demo date, in Auckland local time."""
    year, month, day = DEMO_DATE
    return datetime(year, month, day, hour, minute, tzinfo=AUCKLAND)


def pickup_window() -> TimeWindow:
    return TimeWindow(start=auckland(16, 0), end=auckland(17, 0))


def delivery_deadline() -> datetime:
    return auckland(19, 0)


def vegetables_item(quantity_kg: int = DONATION_TOTAL_KG) -> FoodItem:
    return FoodItem(
        item_name="Fresh vegetables",
        category=FoodCategory.VEGETABLES,
        quantity=quantity_kg,
        unit="kg",
        storage_type=StorageType.AMBIENT,
        delivery_deadline=delivery_deadline(),
    )


def donation(quantity_kg: int = DONATION_TOTAL_KG) -> DonationRequest:
    return DonationRequest(
        donation_id=DONATION_ID,
        store_id="WW-MT-EDEN",
        store_location=STORE_LOCATION,
        pickup_window=pickup_window(),
        items=[vegetables_item(quantity_kg)],
        handling_notes="Keep out of direct sun.",
    )


def fresh_inventory(total_kg: int = DONATION_TOTAL_KG) -> DonationInventory:
    return DonationInventory(
        donation_id=DONATION_ID,
        total_kg=total_kg,
        available_kg=total_kg,
        reserved_kg=0,
        in_transit_kg=0,
        delivered_kg=0,
    )


def _window(open_hour: int, close_hour: int) -> TimeWindow:
    return TimeWindow(start=auckland(open_hour, 0), end=auckland(close_hour, 0))


def community_a(remaining_capacity_kg: int = 60) -> CommunityOrganisation:
    """Urgent vegetable need, capacity for the whole donation, open."""
    return CommunityOrganisation(
        community_id=COMMUNITY_A_ID,
        name="Auckland City Mission",
        location=Location(name="Auckland City Mission", latitude=-36.8570, longitude=174.7620),
        accepted_categories=[FoodCategory.VEGETABLES, FoodCategory.FRUIT, FoodCategory.BAKERY],
        supported_storage=[StorageType.AMBIENT, StorageType.CHILLED],
        needs=[CommunityNeed(category=FoodCategory.VEGETABLES, level=NeedLevel.URGENT)],
        declared_capacity_kg=remaining_capacity_kg,
        remaining_capacity_kg=remaining_capacity_kg,
        receiving_window=_window(9, 19),
        is_open=True,
    )


def community_b(remaining_capacity_kg: int = 80) -> CommunityOrganisation:
    """Does not accept fresh vegetables. Its need is real, and it is not vegetables.

    Requirement.md section 5 puts B's Need on screen, so B must want *something*
    (docs/assumption_audit.md C-5). Chilled-only storage additionally makes the
    storage-compatibility policy observable in this world even though the demo
    excludes B on category first (C-6).
    """
    return CommunityOrganisation(
        community_id=COMMUNITY_B_ID,
        name="Northshore Family Kitchen",
        location=Location(name="Northshore Family Kitchen", latitude=-36.7950, longitude=174.7480),
        accepted_categories=[FoodCategory.DAIRY, FoodCategory.MEAT],
        supported_storage=[StorageType.CHILLED, StorageType.FROZEN],
        needs=[CommunityNeed(category=FoodCategory.DAIRY, level=NeedLevel.HIGH)],
        declared_capacity_kg=remaining_capacity_kg,
        remaining_capacity_kg=remaining_capacity_kg,
        receiving_window=_window(8, 18),
        is_open=True,
    )


def community_c(remaining_capacity_kg: int = 10) -> CommunityOrganisation:
    """Accepts vegetables; 10 kg remaining capacity — insufficient on its own."""
    return CommunityOrganisation(
        community_id=COMMUNITY_C_ID,
        name="Onehunga Community Pantry",
        location=Location(name="Onehunga Community Pantry", latitude=-36.9230, longitude=174.7840),
        accepted_categories=[FoodCategory.VEGETABLES, FoodCategory.AMBIENT_GROCERY],
        supported_storage=[StorageType.AMBIENT],
        needs=[CommunityNeed(category=FoodCategory.VEGETABLES, level=NeedLevel.MEDIUM)],
        declared_capacity_kg=remaining_capacity_kg,
        remaining_capacity_kg=remaining_capacity_kg,
        receiving_window=_window(10, 18),
        is_open=True,
    )


def community_d(remaining_capacity_kg: int = 30) -> CommunityOrganisation:
    """Accepts vegetables, 30 kg remaining capacity, open. The rematch target."""
    return CommunityOrganisation(
        community_id=COMMUNITY_D_ID,
        name="Glen Innes Food Hub",
        location=Location(name="Glen Innes Food Hub", latitude=-36.8760, longitude=174.8530),
        accepted_categories=[FoodCategory.VEGETABLES, FoodCategory.FRUIT],
        supported_storage=[StorageType.AMBIENT],
        needs=[CommunityNeed(category=FoodCategory.VEGETABLES, level=NeedLevel.HIGH)],
        declared_capacity_kg=remaining_capacity_kg,
        remaining_capacity_kg=remaining_capacity_kg,
        receiving_window=_window(12, 19),
        is_open=True,
    )


def all_communities() -> list[CommunityOrganisation]:
    return [community_a(), community_b(), community_c(), community_d()]


def driver_with_capacity(
    driver_id: str = "DRV-001",
    capacity_kg: int = 100,
    *,
    is_available: bool = True,
) -> Driver:
    return Driver(
        driver_id=driver_id,
        name=f"Driver {driver_id}",
        start_location=STORE_LOCATION,
        vehicle_capacity_kg=capacity_kg,
        is_available=is_available,
    )


def all_drivers() -> list[Driver]:
    """Three drivers, at least one genuinely infeasible for 60 kg (C-5)."""
    return [
        driver_with_capacity("DRV-001", 100),
        driver_with_capacity("DRV-002", 40),
        driver_with_capacity("DRV-003", 80, is_available=False),
    ]


def simulated_route(
    origin: Location,
    destination: Location,
    *,
    departure: datetime,
    duration_minutes: int = 18,
    distance_km: float = 6.4,
) -> RouteLeg:
    """A stand-in RouteLeg for tests that need a candidate to *carry* a route.

    Deliberately trivial. Tests that assert on routing behaviour resolve the
    real routing policy through `domain_api`; this only fills a required field.
    """
    return RouteLeg(
        origin=origin,
        destination=destination,
        polyline=[
            (origin.latitude, origin.longitude),
            (destination.latitude, destination.longitude),
        ],
        distance_km=distance_km,
        duration_minutes=duration_minutes,
        eta=departure + timedelta(minutes=duration_minutes),
        simulated=True,
    )
