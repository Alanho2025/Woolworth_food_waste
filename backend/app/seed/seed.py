"""Idempotent seed runner.

    python -m backend.app.seed.seed

Running it twice produces byte-identical database state, which is what makes
`scripts/reset_demo.sh` trustworthy between rehearsals and between judging
sessions. Idempotency is achieved by deleting every row and re-inserting in a
fixed order rather than by upserting selectively: it is simpler, it removes rows
a previous run left behind, and — because no table uses AUTOINCREMENT — it
reproduces the same rowids, so even `sqlite3 foodflow.db .dump` is identical.

This module owns the *wiring* of the demo world. The world itself lives in
`data.py`, which imports no infrastructure.
"""

from __future__ import annotations

import logging

from sqlalchemy import delete, inspect

from backend.app.contracts.core import DeliveryOrder, DeliveryStatus, DonationInventory
from backend.app.domain.clock import PinnedClock
from backend.app.infrastructure.db.models import DELETE_ORDER
from backend.app.infrastructure.db.session import (
    create_all,
    create_db_engine,
    create_session_factory,
    reset_all,
)
from backend.app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from backend.app.infrastructure.route_simulator import SimulatedRouteSimulator
from backend.app.seed.data import (
    COMMUNITIES,
    DEMO_DONATION,
    DEMO_INVENTORY,
    DRIVERS,
    HISTORICAL_KG_RESCUED,
    HISTORY,
    ROUTE_POLYLINES,
    SEEDED_DELIVERIES,
    STORE_LOCATION,
    HistoricalDelivery,
)

logger = logging.getLogger(__name__)


def _build_historical_order(history: HistoricalDelivery) -> DeliveryOrder:
    """Build one completed delivery, routed from its own historical departure.

    The route is timed with a clock pinned to `departed_at` rather than to the
    demo clock, so a delivery that finished two days ago does not carry an ETA
    in the demo's future.
    """
    route_key = (STORE_LOCATION.name, history.destination.location.name)
    if route_key not in ROUTE_POLYLINES:
        # Falling back here would silently draw a straight line across Auckland
        # on the Dashboard map. Fail the seed instead. See R-19.
        raise ValueError(f"no hand-traced polyline seeded for {route_key}")

    simulator = SimulatedRouteSimulator(PinnedClock(history.departed_at), ROUTE_POLYLINES)
    route = simulator.route(STORE_LOCATION, history.destination.location)
    deadline = history.donation.items[0].delivery_deadline
    return DeliveryOrder(
        order_id=history.order_id,
        donation_id=history.donation.donation_id,
        origin=STORE_LOCATION,
        destination_community_id=history.destination.community_id,
        quantity_kg=history.quantity_kg,
        driver_id=history.driver.driver_id,
        route=route,
        status=history.status,
        deadline=deadline,
        is_rematch=False,
    )


def _historical_inventory(history: HistoricalDelivery) -> DonationInventory:
    """A balanced ledger matching the seeded delivery's operational state."""
    in_transit_kg = history.quantity_kg if history.status is DeliveryStatus.IN_TRANSIT else 0
    delivered_kg = history.quantity_kg if history.status is DeliveryStatus.COMPLETED else 0
    return DonationInventory(
        donation_id=history.donation.donation_id,
        total_kg=history.quantity_kg,
        available_kg=0,
        reserved_kg=0,
        in_transit_kg=in_transit_kg,
        delivered_kg=delivered_kg,
    )


def seed(database_url: str | None = None) -> None:
    """Reset the database to the demo world. Safe to run repeatedly."""
    rescued = sum(history.quantity_kg for history in HISTORY)
    if rescued != HISTORICAL_KG_RESCUED:
        raise ValueError(
            f"HISTORICAL_KG_RESCUED is {HISTORICAL_KG_RESCUED} but the seeded "
            f"history totals {rescued} kg; the Dashboard figure would be wrong"
        )

    engine = create_db_engine(database_url)
    schema = inspect(engine)
    community_columns = (
        {column["name"] for column in schema.get_columns("communities")}
        if schema.has_table("communities")
        else set()
    )
    if community_columns and "declared_capacity_kg" not in community_columns:
        # One-time compatibility for the pre-P2 developer DB. Normal reseeds do
        # not rebuild the schema: doing so increments SQLite's file-header change
        # counter and violates the byte-identical seed requirement.
        reset_all(engine)
    else:
        create_all(engine)
    session_factory = create_session_factory(engine)

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        for model in DELETE_ORDER:
            uow.session.execute(delete(model))
        uow.session.flush()

        for community in COMMUNITIES:
            uow.communities.save(community)
        for driver in DRIVERS:
            uow.drivers.save(driver)

        # The demo donation. No delivery order and no agent run: the Agent
        # creates those live on stage, and pre-seeding them would make the
        # journey a replay of itself.
        uow.donations.add(DEMO_DONATION)
        uow.donations.save_inventory(DEMO_INVENTORY)

        for history in SEEDED_DELIVERIES:
            uow.donations.add(history.donation)
            uow.donations.save_inventory(_historical_inventory(history))
            uow.deliveries.add(_build_historical_order(history))

        uow.commit()

    engine.dispose()

    logger.info(
        "Seeded %d communities, %d drivers, donation %s (%d kg), "
        "%d completed historical deliveries totalling %d kg rescued, and %d in flight.",
        len(COMMUNITIES),
        len(DRIVERS),
        DEMO_DONATION.donation_id,
        DEMO_INVENTORY.total_kg,
        len(HISTORY),
        rescued,
        sum(delivery.status is DeliveryStatus.IN_TRANSIT for delivery in SEEDED_DELIVERIES),
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    seed()


if __name__ == "__main__":
    main()
