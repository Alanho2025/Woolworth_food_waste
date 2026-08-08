"""The deterministic demo world.

Requirement.md 1 fixes the *story* — 60 kg of vegetables from Woolworths Mount
Eden, four communities, A accepts only 35 kg, the remainder rematches to D — but
leaves most of the *world* undefined. Everything it left open is decided here,
once, so that no other module has to guess:

* real Auckland coordinates for the store and all four communities;
* a receiving window for **all four** communities, not only A's, each one open
  at the pinned 15:45 NZ clock and still open past the 19:00 deadline;
* a genuine, non-vegetable need profile for Community B — Screen 3 must display
  B's Need, and it cannot be the category B rejects
  (docs/phase_review_findings.md R-18, R-26);
* three drivers with different vehicle capacities, one of them genuinely too
  small for 60 kg, so `validate_driver_capacity` is a real check rather than
  decoration;
* hand-traced road-shaped polylines for every route the demo draws
  (docs/phase_review_findings.md R-19);
* pre-existing completed deliveries, so the opening Dashboard reads as an active
  coordination system rather than an empty report
  (Requirement.md 3, docs/phase_review_findings.md R-21/R-26).

This module is **data only**. It imports contracts and the clock, and nothing
else — in particular it does not import the route simulator, because the
simulator reads `ROUTE_POLYLINES` from here. `seed.py` owns the wiring.

Geography note: all four communities sit south or west of the store, on the
isthmus. No route crosses the Waitematā Harbour, which is what lets a hand-
traced polyline stay plausible without becoming a motorway modelling exercise.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from backend.app.contracts.core import (
    CommunityNeed,
    CommunityOrganisation,
    DeliveryStatus,
    DonationInventory,
    DonationRequest,
    Driver,
    FoodCategory,
    FoodItem,
    Location,
    NeedLevel,
    StorageType,
    TimeWindow,
)
from backend.app.domain.clock import AUCKLAND

Coordinate = tuple[float, float]


def _nz(year: int, month: int, day: int, hour: int, minute: int) -> datetime:
    """An Auckland-local instant.

    Resolved through the `Pacific/Auckland` zone, never a literal +12:00: New
    Zealand moves to NZDT on 2026-09-27 and a hardcoded offset would silently
    shift every window by an hour. See docs/assumption_audit.md C-1.
    """
    return datetime(year, month, day, hour, minute, tzinfo=AUCKLAND)


# --------------------------------------------------------------------------
# Store and donation — the fixed demo scenario
# --------------------------------------------------------------------------

STORE_ID = "WW-MT-EDEN"
STORE_LOCATION = Location(
    name="Woolworths Mount Eden",
    latitude=-36.8770,
    longitude=174.7645,
)

DONATION_ID = "DON-001"
DEMO_DELIVERY_DEADLINE = _nz(2026, 8, 8, 19, 0)

DEMO_DONATION = DonationRequest(
    donation_id=DONATION_ID,
    store_id=STORE_ID,
    store_location=STORE_LOCATION,
    pickup_window=TimeWindow(start=_nz(2026, 8, 8, 16, 0), end=_nz(2026, 8, 8, 17, 0)),
    items=[
        FoodItem(
            item_name="Fresh vegetables (mixed)",
            category=FoodCategory.VEGETABLES,
            quantity=60,
            unit="kg",
            storage_type=StorageType.AMBIENT,
            delivery_deadline=DEMO_DELIVERY_DEADLINE,
        )
    ],
    handling_notes="Loose produce in 20 kg crates. Keep out of direct sun; no chiller required.",
)

# The ledger opens with the whole donation available and nothing committed.
# available + reserved + in_transit + delivered == total_kg, always.
DEMO_INVENTORY = DonationInventory(
    donation_id=DONATION_ID,
    total_kg=60,
    available_kg=60,
    reserved_kg=0,
    in_transit_kg=0,
    delivered_kg=0,
)


# --------------------------------------------------------------------------
# Communities
# --------------------------------------------------------------------------
#
# Capacity vs need is the product's central distinction, so read each entry as
# two independent facts: `accepted_categories`/`supported_storage`/
# `declared_capacity_kg`/`remaining_capacity_kg` say what the organisation CAN
# take; `needs` says what
# it WANTS. B wants dairy badly and can take 80 kg — and is still ineligible
# for the 60 kg vegetable donation on category alone.

COMMUNITY_A = CommunityOrganisation(
    community_id="COM-A",
    name="Community A — Mount Roskill Community Kitchen",
    location=Location(
        name="Mount Roskill Community Kitchen",
        latitude=-36.9082,
        longitude=174.7387,
    ),
    accepted_categories=[FoodCategory.VEGETABLES, FoodCategory.FRUIT, FoodCategory.BAKERY],
    supported_storage=[StorageType.AMBIENT, StorageType.CHILLED],
    needs=[
        CommunityNeed(category=FoodCategory.VEGETABLES, level=NeedLevel.URGENT),
        CommunityNeed(category=FoodCategory.FRUIT, level=NeedLevel.MEDIUM),
    ],
    # Resolves R-25: this is REMAINING capacity, matching every other community,
    # so the 60 kg allocation consumes all of it and the later correction to
    # 35 kg is a reduction of the same quantity, not of a different one.
    declared_capacity_kg=60,
    remaining_capacity_kg=60,
    receiving_window=TimeWindow(start=_nz(2026, 8, 8, 8, 0), end=_nz(2026, 8, 8, 20, 0)),
    is_open=True,
)

# B is the "wants it, cannot take it" card. Its need is real and specific and
# deliberately NOT vegetables — Screen 3 renders every community's Need, and a
# blank or vegetable-shaped need on the card excluded for rejecting vegetables
# is the kind of detail a judge notices. Ambient storage is supported so that B
# is excluded on category ALONE; storage compatibility stays implemented and
# unit-tested but unexercised by the demo (docs/assumption_audit.md C-6).
COMMUNITY_B = CommunityOrganisation(
    community_id="COM-B",
    name="Community B — Ponsonby Family Support Centre",
    location=Location(
        name="Ponsonby Family Support Centre",
        latitude=-36.8555,
        longitude=174.7460,
    ),
    accepted_categories=[FoodCategory.DAIRY, FoodCategory.BAKERY, FoodCategory.MEAT],
    supported_storage=[StorageType.AMBIENT, StorageType.CHILLED],
    needs=[
        CommunityNeed(category=FoodCategory.DAIRY, level=NeedLevel.HIGH),
        CommunityNeed(category=FoodCategory.BAKERY, level=NeedLevel.MEDIUM),
    ],
    # Declared 100 kg; 20 kg is already occupied by DON-000D in flight below.
    declared_capacity_kg=100,
    remaining_capacity_kg=80,
    receiving_window=TimeWindow(start=_nz(2026, 8, 8, 9, 0), end=_nz(2026, 8, 8, 19, 30)),
    is_open=True,
)

# C wants vegetables and is open — and still cannot take the 25 kg remainder.
# The exclusion wording is "insufficient for a single-destination allocation",
# because C genuinely could take 10 of the 25 (docs/assumption_audit.md C-2).
COMMUNITY_C = CommunityOrganisation(
    community_id="COM-C",
    name="Community C — Onehunga Foodbank",
    location=Location(
        name="Onehunga Foodbank",
        latitude=-36.9230,
        longitude=174.7830,
    ),
    accepted_categories=[FoodCategory.VEGETABLES, FoodCategory.FRUIT],
    supported_storage=[StorageType.AMBIENT, StorageType.CHILLED],
    needs=[
        CommunityNeed(category=FoodCategory.VEGETABLES, level=NeedLevel.HIGH),
        CommunityNeed(category=FoodCategory.FRUIT, level=NeedLevel.LOW),
    ],
    declared_capacity_kg=10,
    remaining_capacity_kg=10,
    receiving_window=TimeWindow(start=_nz(2026, 8, 8, 10, 0), end=_nz(2026, 8, 8, 20, 0)),
    is_open=True,
)

# D is the rematch destination: 30 kg of capacity against a 25 kg remainder, so
# the whole remainder fits one destination and no split is needed (C-2).
COMMUNITY_D = CommunityOrganisation(
    community_id="COM-D",
    name="Community D — Ellerslie Community Pantry",
    location=Location(
        name="Ellerslie Community Pantry",
        latitude=-36.8985,
        longitude=174.8090,
    ),
    accepted_categories=[
        FoodCategory.VEGETABLES,
        FoodCategory.FRUIT,
        FoodCategory.BAKERY,
        FoodCategory.AMBIENT_GROCERY,
    ],
    supported_storage=[StorageType.AMBIENT],
    needs=[
        CommunityNeed(category=FoodCategory.VEGETABLES, level=NeedLevel.MEDIUM),
        CommunityNeed(category=FoodCategory.AMBIENT_GROCERY, level=NeedLevel.HIGH),
    ],
    declared_capacity_kg=30,
    remaining_capacity_kg=30,
    receiving_window=TimeWindow(start=_nz(2026, 8, 8, 7, 30), end=_nz(2026, 8, 8, 21, 0)),
    is_open=True,
)

COMMUNITIES: tuple[CommunityOrganisation, ...] = (
    COMMUNITY_A,
    COMMUNITY_B,
    COMMUNITY_C,
    COMMUNITY_D,
)


# --------------------------------------------------------------------------
# Drivers
# --------------------------------------------------------------------------
#
# Three, with different vehicle capacities and one that genuinely cannot carry
# 60 kg. With a single driver, `get_available_drivers` and
# `validate_driver_capacity` would both be decorative and Requirement.md 10's
# "choose from feasible drivers" would be untrue.

DRIVER_1 = Driver(
    driver_id="DRV-1",
    name="Aroha Ngata",
    start_location=Location(name="Newmarket Depot", latitude=-36.8700, longitude=174.7770),
    vehicle_capacity_kg=80,
    is_available=True,
)

# The infeasible one. A 40 kg scooter box cannot take the 60 kg allocation, so
# the capacity check has to actually reject something on stage.
DRIVER_2 = Driver(
    driver_id="DRV-2",
    name="Sam Patel",
    start_location=Location(name="Kingsland Yard", latitude=-36.8730, longitude=174.7480),
    vehicle_capacity_kg=40,
    is_available=True,
)

DRIVER_3 = Driver(
    driver_id="DRV-3",
    name="Mere Tuilagi",
    start_location=Location(name="Penrose Depot", latitude=-36.9110, longitude=174.8130),
    vehicle_capacity_kg=120,
    # Carrying the independent in-flight seed delivery below.
    is_available=False,
)

DRIVERS: tuple[Driver, ...] = (DRIVER_1, DRIVER_2, DRIVER_3)


# --------------------------------------------------------------------------
# Hand-traced route polylines
# --------------------------------------------------------------------------
#
# Keyed by (origin location name, destination location name). Each one follows
# real Auckland arterials — Mt Eden Road, Dominion Road, Balmoral Road, Manukau
# Road, Great South Road — rather than a geodesic, so the line on the map bends
# where a van would bend. Distance for the ETA is the summed length of these
# points, which is also a more honest driving distance than crow-flies.
# See docs/phase_review_findings.md R-19.

ROUTE_POLYLINES: dict[tuple[str, str], tuple[Coordinate, ...]] = {
    # Mt Eden Rd south -> Balmoral Rd west -> Dominion Rd south -> Mt Albert Rd
    # -> White Swan Rd -> Stoddard Rd. The primary demo leg.
    ("Woolworths Mount Eden", "Mount Roskill Community Kitchen"): (
        (-36.8770, 174.7645),
        (-36.8815, 174.7628),
        (-36.8845, 174.7605),
        (-36.8848, 174.7530),
        (-36.8852, 174.7462),
        (-36.8925, 174.7440),
        (-36.8990, 174.7425),
        (-36.9040, 174.7405),
        (-36.9082, 174.7387),
    ),
    # Mt Eden Rd north -> Symonds St -> Newton Rd -> Karangahape Rd -> Ponsonby Rd.
    ("Woolworths Mount Eden", "Ponsonby Family Support Centre"): (
        (-36.8770, 174.7645),
        (-36.8722, 174.7638),
        (-36.8680, 174.7625),
        (-36.8640, 174.7602),
        (-36.8615, 174.7570),
        (-36.8598, 174.7520),
        (-36.8588, 174.7482),
        (-36.8570, 174.7470),
        (-36.8555, 174.7460),
    ),
    # Mt Eden Rd -> Grange Rd -> Manukau Rd -> Royal Oak roundabout -> Onehunga Mall.
    ("Woolworths Mount Eden", "Onehunga Foodbank"): (
        (-36.8770, 174.7645),
        (-36.8820, 174.7660),
        (-36.8862, 174.7700),
        (-36.8900, 174.7770),
        (-36.8960, 174.7808),
        (-36.9035, 174.7830),
        (-36.9107, 174.7793),
        (-36.9160, 174.7828),
        (-36.9230, 174.7830),
    ),
    # Mt Eden Rd -> Grange Rd -> Greenlane West -> Greenlane East -> Great South Rd.
    ("Woolworths Mount Eden", "Ellerslie Community Pantry"): (
        (-36.8770, 174.7645),
        (-36.8815, 174.7662),
        (-36.8858, 174.7712),
        (-36.8895, 174.7790),
        (-36.8918, 174.7880),
        (-36.8938, 174.7960),
        (-36.8958, 174.8030),
        (-36.8985, 174.8090),
    ),
    # THE REMATCH LEG. Departs Community A, where the driver is already standing
    # after the partial acceptance — it does not return to Mount Eden first
    # (docs/assumption_audit.md C-4). Stoddard Rd -> Mt Albert Rd east -> Royal
    # Oak roundabout -> Campbell Rd -> Great South Rd.
    ("Mount Roskill Community Kitchen", "Ellerslie Community Pantry"): (
        (-36.9082, 174.7387),
        (-36.9060, 174.7440),
        (-36.9058, 174.7530),
        (-36.9070, 174.7640),
        (-36.9092, 174.7740),
        (-36.9105, 174.7795),
        (-36.9058, 174.7900),
        (-36.9020, 174.7990),
        (-36.8985, 174.8090),
    ),
}


# --------------------------------------------------------------------------
# Pre-existing history
# --------------------------------------------------------------------------
#
# Requirement.md 3 says the Dashboard must read as an active coordination
# system, not a reporting page. With only DON-001 seeded, "kilograms rescued"
# reads 0 kg at the exact moment the pitch opens — the worst possible number on
# the opening slide (docs/phase_review_findings.md R-21).
#
# These three deliveries are COMPLETED, belong to their own donations, and are
# dated before the demo day. Nothing here touches DON-001, so the 60 kg
# integrity display stays unambiguous: scope that widget to DON-001 and these
# rows are invisible to it, sum `delivered_kg` across all donations and they are
# the 155 kg of credible history.


@dataclass(frozen=True)
class HistoricalDelivery:
    """One completed delivery from before the demo, with its own donation.

    `departed_at` is what the route is timed from, so a historical leg gets a
    historical ETA instead of one anchored to the pinned demo clock.
    """

    donation: DonationRequest
    order_id: str
    destination: CommunityOrganisation
    driver: Driver
    quantity_kg: int
    departed_at: datetime
    status: DeliveryStatus = DeliveryStatus.COMPLETED


def _historical_donation(
    donation_id: str,
    item_name: str,
    category: FoodCategory,
    quantity_kg: int,
    deadline: datetime,
    pickup_start: datetime,
) -> DonationRequest:
    return DonationRequest(
        donation_id=donation_id,
        store_id=STORE_ID,
        store_location=STORE_LOCATION,
        pickup_window=TimeWindow(start=pickup_start, end=deadline),
        items=[
            FoodItem(
                item_name=item_name,
                category=category,
                quantity=quantity_kg,
                unit="kg",
                storage_type=StorageType.AMBIENT,
                delivery_deadline=deadline,
            )
        ],
        handling_notes="Completed before the demo window. Retained for impact reporting.",
    )


HISTORY: tuple[HistoricalDelivery, ...] = (
    HistoricalDelivery(
        donation=_historical_donation(
            donation_id="DON-000A",
            item_name="Fresh vegetables (mixed)",
            category=FoodCategory.VEGETABLES,
            quantity_kg=45,
            deadline=_nz(2026, 8, 6, 19, 0),
            pickup_start=_nz(2026, 8, 6, 15, 0),
        ),
        order_id="DO-000A-1",
        destination=COMMUNITY_A,
        driver=DRIVER_1,
        quantity_kg=45,
        departed_at=_nz(2026, 8, 6, 15, 30),
    ),
    HistoricalDelivery(
        donation=_historical_donation(
            donation_id="DON-000B",
            item_name="Bakery surplus",
            category=FoodCategory.BAKERY,
            quantity_kg=80,
            deadline=_nz(2026, 8, 7, 13, 0),
            pickup_start=_nz(2026, 8, 7, 9, 0),
        ),
        order_id="DO-000B-1",
        destination=COMMUNITY_D,
        driver=DRIVER_3,
        quantity_kg=80,
        departed_at=_nz(2026, 8, 7, 9, 15),
    ),
    HistoricalDelivery(
        donation=_historical_donation(
            donation_id="DON-000C",
            item_name="Seasonal fruit",
            category=FoodCategory.FRUIT,
            quantity_kg=30,
            deadline=_nz(2026, 8, 7, 19, 0),
            pickup_start=_nz(2026, 8, 7, 16, 0),
        ),
        order_id="DO-000C-1",
        destination=COMMUNITY_C,
        driver=DRIVER_1,
        quantity_kg=30,
        departed_at=_nz(2026, 8, 7, 16, 10),
    ),
)

# One independent active delivery makes the opening Dashboard operationally
# alive without touching DON-001 or muddying its 60 kg integrity ledger.
IN_FLIGHT_DELIVERY = HistoricalDelivery(
    donation=_historical_donation(
        donation_id="DON-000D",
        item_name="Chilled dairy surplus",
        category=FoodCategory.DAIRY,
        quantity_kg=20,
        deadline=_nz(2026, 8, 8, 19, 0),
        pickup_start=_nz(2026, 8, 8, 15, 0),
    ),
    order_id="DO-000D-1",
    destination=COMMUNITY_B,
    driver=DRIVER_3,
    quantity_kg=20,
    departed_at=_nz(2026, 8, 8, 15, 20),
    status=DeliveryStatus.IN_TRANSIT,
)

SEEDED_DELIVERIES: tuple[HistoricalDelivery, ...] = (*HISTORY, IN_FLIGHT_DELIVERY)

# 45 + 80 + 30. Asserted in seed.py so the figure on the opening slide can never
# drift away from the rows that produce it.
HISTORICAL_KG_RESCUED = 155
