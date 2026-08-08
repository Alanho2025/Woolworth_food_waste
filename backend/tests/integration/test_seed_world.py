"""P2 seed reproducibility and demo-world completeness over real SQLite."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from hashlib import sha256
from pathlib import Path

from sqlalchemy import select

from backend.app.contracts.core import DeliveryStatus
from backend.app.domain.clock import AUCKLAND
from backend.app.infrastructure.db.models import DeliveryOrderRow
from backend.app.seed.data import (
    COMMUNITIES,
    COMMUNITY_A,
    COMMUNITY_D,
    DEMO_INVENTORY,
    DONATION_ID,
    ROUTE_POLYLINES,
    STORE_LOCATION,
)
from backend.app.seed.seed import seed

from .conftest import DatabaseHarness


def canonical_dump_hash(path: Path) -> str:
    """Hash SQLite's logical dump, excluding storage-header counters."""
    with sqlite3.connect(path) as connection:
        dump = "\n".join(connection.iterdump()).encode()
    return sha256(dump).hexdigest()


def test_running_seed_twice_produces_identical_canonical_database_state(tmp_path: Path) -> None:
    """FRESH DB -> seed twice -> canonical schema and ordered domain rows do not drift."""
    path = tmp_path / "repeatable.db"
    url = f"sqlite:///{path}"
    seed(url)
    first = canonical_dump_hash(path)

    seed(url)
    second = canonical_dump_hash(path)

    assert second == first


def test_seed_persists_complete_geography_times_capacity_and_driver_world(
    database: DatabaseHarness,
) -> None:
    """SEEDED SQLITE -> hydrate contracts -> four Auckland orgs and three distinct drivers."""
    with database.uow() as uow:
        communities = uow.communities.list_all()
        drivers = [uow.drivers.get(driver_id) for driver_id in ("DRV-1", "DRV-2", "DRV-3")]
        donation = uow.donations.get(DONATION_ID)
        inventory = uow.donations.get_inventory(DONATION_ID)

    assert donation is not None
    assert inventory == DEMO_INVENTORY
    assert len(communities) == 4
    assert {community.community_id for community in communities} == {
        community.community_id for community in COMMUNITIES
    }
    for community in communities:
        assert -37.1 < community.location.latitude < -36.7
        assert 174.6 < community.location.longitude < 175.0
        assert community.location.name
        assert community.receiving_window.start.tzinfo is not None
        assert community.receiving_window.end.tzinfo is not None
        assert community.receiving_window.start < community.receiving_window.end
        assert community.declared_capacity_kg >= community.remaining_capacity_kg
        assert community.accepted_categories
        assert community.supported_storage
        assert community.needs
    assert donation.pickup_window.start.tzinfo is not None
    assert donation.pickup_window.start < donation.pickup_window.end
    assert donation.items[0].delivery_deadline.tzinfo is not None
    assert all(driver is not None for driver in drivers)
    assert {driver.vehicle_capacity_kg for driver in drivers if driver is not None} == {40, 80, 120}


def test_every_displayed_route_pair_has_a_hand_traced_polyline_with_real_endpoints() -> None:
    """STORE->A/B/C/D AND A->D -> inspect seed -> road-shaped multi-point geometry."""
    required_pairs = {(STORE_LOCATION.name, community.location.name) for community in COMMUNITIES}
    required_pairs.add((COMMUNITY_A.location.name, COMMUNITY_D.location.name))

    assert required_pairs <= ROUTE_POLYLINES.keys()
    locations = {STORE_LOCATION.name: STORE_LOCATION}
    locations.update({community.location.name: community.location for community in COMMUNITIES})
    for origin_name, destination_name in required_pairs:
        points = ROUTE_POLYLINES[(origin_name, destination_name)]
        origin = locations[origin_name]
        destination = locations[destination_name]
        assert len(points) >= 3, (origin_name, destination_name)
        assert points[0] == (origin.latitude, origin.longitude)
        assert points[-1] == (destination.latitude, destination.longitude)


def test_seed_contains_three_completed_and_one_in_flight_historical_delivery_but_demo_is_clean(
    database: DatabaseHarness,
) -> None:
    """SEEDED SQLITE -> historical orders 3 completed/1 in transit; DON-001 has none."""
    with database.uow() as uow:
        demo_orders = uow.deliveries.list_for_donation(DONATION_ID)
        rows = list(uow.session.scalars(select(DeliveryOrderRow)))
        statuses = [DeliveryStatus(row.status) for row in rows]

    assert demo_orders == []
    assert statuses.count(DeliveryStatus.COMPLETED) == 3
    assert statuses.count(DeliveryStatus.IN_TRANSIT) == 1
    assert len(rows) == 4


def test_sqlite_round_trip_restores_aware_instants_not_naive_machine_local_time(
    database: DatabaseHarness,
) -> None:
    """NZ SEEDED TIMES -> SQLite -> timezone-aware UTC instants preserving the same moments."""
    with database.uow() as uow:
        donation = uow.donations.get(DONATION_ID)
        community = uow.communities.get(COMMUNITY_A.community_id)
    assert donation is not None
    assert community is not None
    for instant in (
        donation.pickup_window.start,
        donation.pickup_window.end,
        donation.items[0].delivery_deadline,
        community.receiving_window.start,
        community.receiving_window.end,
    ):
        assert isinstance(instant, datetime)
        assert instant.tzinfo is not None
        assert instant.astimezone(AUCKLAND).utcoffset() is not None
