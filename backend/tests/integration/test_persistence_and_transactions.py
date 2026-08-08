"""P2 transaction, persistence, and hard-constraint tests over real SQLite."""

from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import func, select

from backend.app.application.allocate_donation import AllocationCommand
from backend.app.application.record_acceptance import RecordAcceptance
from backend.app.contracts.core import (
    DeliveryOrder,
    DeliveryStatus,
    DonationInventory,
    StorageType,
)
from backend.app.domain.clock import DEMO_NOW, PinnedClock
from backend.app.domain.errors import EligibilityError, ErrorCode, QuantityIntegrityError
from backend.app.infrastructure.db.models import AuditEventRow
from backend.app.seed.data import (
    COMMUNITY_A,
    COMMUNITY_B,
    COMMUNITY_C,
    COMMUNITY_D,
    DONATION_ID,
    DRIVER_1,
    DRIVER_2,
    STORE_LOCATION,
)

from .conftest import DatabaseHarness


def allocate_a(database: DatabaseHarness):
    return database.allocator().execute(
        AllocationCommand(
            donation_id=DONATION_ID,
            community_id=COMMUNITY_A.community_id,
            quantity_kg=60,
            driver_id=DRIVER_1.driver_id,
            origin=STORE_LOCATION,
        )
    )


def donation_orders(database: DatabaseHarness) -> list[DeliveryOrder]:
    with database.uow() as uow:
        return uow.deliveries.list_for_donation(DONATION_ID)


def failure_audits(
    database: DatabaseHarness, action: str = "allocation_failed"
) -> list[AuditEventRow]:
    with database.sessions() as session:
        return list(
            session.scalars(
                select(AuditEventRow)
                .where(AuditEventRow.donation_id == DONATION_ID)
                .where(AuditEventRow.action == action)
                .order_by(AuditEventRow.event_id)
            )
        )


def assert_unallocated_demo_state(database: DatabaseHarness, community_id: str) -> None:
    with database.uow() as uow:
        inventory = uow.donations.get_inventory(DONATION_ID)
        community = uow.communities.get(community_id)
        assert inventory is not None
        assert community is not None
        assert inventory == DonationInventory(
            donation_id=DONATION_ID,
            total_kg=60,
            available_kg=60,
            reserved_kg=0,
            in_transit_kg=0,
            delivered_kg=0,
        )
        assert community.remaining_capacity_kg in {
            COMMUNITY_A.remaining_capacity_kg,
            COMMUNITY_B.remaining_capacity_kg,
            COMMUNITY_C.remaining_capacity_kg,
        }
        assert uow.deliveries.list_for_donation(DONATION_ID) == []


def assert_one_durable_failure(
    database: DatabaseHarness, expected_code: ErrorCode, *, action: str = "allocation_failed"
) -> None:
    audits = failure_audits(database, action)
    assert len(audits) == 1
    assert audits[0].succeeded is False
    assert expected_code.value in audits[0].detail


def test_declared_and_remaining_capacity_round_trip_independently_through_real_repository(
    database: DatabaseHarness,
) -> None:
    """A 60/60 -> persist correction 35/0 -> new UoW reads both distinct values."""
    with database.uow() as uow:
        original = uow.communities.get(COMMUNITY_A.community_id)
        assert original is not None
        assert original.declared_capacity_kg == 60
        assert original.remaining_capacity_kg == 60
        uow.communities.save(
            original.model_copy(update={"declared_capacity_kg": 35, "remaining_capacity_kg": 0})
        )
        uow.commit()

    with database.uow() as uow:
        persisted = uow.communities.get(COMMUNITY_A.community_id)
        assert persisted is not None
        assert persisted.declared_capacity_kg == 35
        assert persisted.remaining_capacity_kg == 0


def test_successful_allocation_reserves_inventory_and_only_remaining_recipient_capacity(
    database: DatabaseHarness,
) -> None:
    """REAL ALLOCATION A/60 -> one order, inventory reserved, declared capacity preserved."""
    order = allocate_a(database)

    with database.uow() as uow:
        inventory = uow.donations.get_inventory(DONATION_ID)
        community = uow.communities.get(COMMUNITY_A.community_id)
        orders = uow.deliveries.list_for_donation(DONATION_ID)
        assert inventory is not None
        assert community is not None
        assert inventory.available_kg == 0
        assert inventory.reserved_kg == 60
        assert inventory.is_balanced is True
        assert community.declared_capacity_kg == 60
        assert community.remaining_capacity_kg == 0
        assert orders == [order]


def test_retrying_successful_allocation_returns_same_order_without_second_reservation(
    database: DatabaseHarness,
) -> None:
    """SAME REAL COMMAND TWICE -> one persisted order and one 60 kg reservation."""
    command = AllocationCommand(
        donation_id=DONATION_ID,
        community_id=COMMUNITY_A.community_id,
        quantity_kg=60,
        driver_id=DRIVER_1.driver_id,
        origin=STORE_LOCATION,
    )
    allocator = database.allocator()

    first = allocator.execute(command)
    second = allocator.execute(command)

    assert second.order_id == first.order_id
    with database.uow() as uow:
        inventory = uow.donations.get_inventory(DONATION_ID)
        assert inventory is not None
        assert inventory.reserved_kg == 60
        assert len(uow.deliveries.list_for_donation(DONATION_ID)) == 1
    with database.sessions() as session:
        success_count = session.scalar(
            select(func.count())
            .select_from(AuditEventRow)
            .where(AuditEventRow.donation_id == DONATION_ID)
            .where(AuditEventRow.action == "allocated")
        )
        assert success_count == 1


def test_category_invalid_b_is_rejected_with_no_partial_writes_and_durable_failure_audit(
    database: DatabaseHarness,
) -> None:
    """VEGETABLES -> B -> typed category failure, unchanged DB, durable audit."""
    with pytest.raises(EligibilityError) as raised:
        database.allocator().execute(
            AllocationCommand(
                donation_id=DONATION_ID,
                community_id=COMMUNITY_B.community_id,
                quantity_kg=25,
                driver_id=DRIVER_1.driver_id,
                origin=STORE_LOCATION,
            )
        )
    assert raised.value.code is ErrorCode.RECIPIENT_CATEGORY_UNSUPPORTED
    assert_unallocated_demo_state(database, COMMUNITY_B.community_id)
    assert_one_durable_failure(database, ErrorCode.RECIPIENT_CATEGORY_UNSUPPORTED)


def test_capacity_invalid_c_is_rejected_with_no_partial_writes_and_durable_failure_audit(
    database: DatabaseHarness,
) -> None:
    """25 KG -> C CAPACITY 10 -> typed capacity failure, unchanged DB, durable audit."""
    with pytest.raises(EligibilityError) as raised:
        database.allocator().execute(
            AllocationCommand(
                donation_id=DONATION_ID,
                community_id=COMMUNITY_C.community_id,
                quantity_kg=25,
                driver_id=DRIVER_1.driver_id,
                origin=STORE_LOCATION,
            )
        )
    assert raised.value.code is ErrorCode.RECIPIENT_CAPACITY_EXCEEDED
    assert_unallocated_demo_state(database, COMMUNITY_C.community_id)
    assert_one_durable_failure(database, ErrorCode.RECIPIENT_CAPACITY_EXCEEDED)


def test_storage_invalid_recipient_is_rejected_with_no_partial_writes_and_durable_failure_audit(
    database: DatabaseHarness,
) -> None:
    """VEGETABLE-COMPATIBLE D MADE FROZEN-ONLY -> typed storage failure and rollback."""
    with database.uow() as uow:
        community = uow.communities.get(COMMUNITY_D.community_id)
        assert community is not None
        uow.communities.save(
            community.model_copy(update={"supported_storage": [StorageType.FROZEN]})
        )
        uow.commit()

    with pytest.raises(EligibilityError) as raised:
        database.allocator().execute(
            AllocationCommand(
                donation_id=DONATION_ID,
                community_id=COMMUNITY_D.community_id,
                quantity_kg=25,
                driver_id=DRIVER_1.driver_id,
                origin=STORE_LOCATION,
            )
        )

    assert raised.value.code is ErrorCode.STORAGE_INCOMPATIBLE
    with database.uow() as uow:
        inventory = uow.donations.get_inventory(DONATION_ID)
        persisted = uow.communities.get(COMMUNITY_D.community_id)
        assert inventory is not None
        assert persisted is not None
        assert inventory.available_kg == 60
        assert inventory.reserved_kg == 0
        assert persisted.declared_capacity_kg == 30
        assert persisted.remaining_capacity_kg == 30
        assert uow.deliveries.list_for_donation(DONATION_ID) == []
    assert_one_durable_failure(database, ErrorCode.STORAGE_INCOMPATIBLE)


def test_unavailable_driver_is_rejected_with_no_partial_writes_and_durable_failure_audit(
    database: DatabaseHarness,
) -> None:
    """UNAVAILABLE DRIVER -> allocation -> typed availability failure and atomic rollback."""
    with database.uow() as uow:
        driver = uow.drivers.get(DRIVER_1.driver_id)
        assert driver is not None
        uow.drivers.save(driver.model_copy(update={"is_available": False}))
        uow.commit()

    with pytest.raises(EligibilityError) as raised:
        allocate_a(database)

    assert raised.value.code is ErrorCode.DRIVER_UNAVAILABLE
    assert_unallocated_demo_state(database, COMMUNITY_A.community_id)
    assert_one_durable_failure(database, ErrorCode.DRIVER_UNAVAILABLE)


def test_small_driver_is_rejected_with_no_partial_writes_and_durable_failure_audit(
    database: DatabaseHarness,
) -> None:
    """40 KG DRIVER -> 60 KG allocation -> typed capacity failure and atomic rollback."""
    with pytest.raises(EligibilityError) as raised:
        database.allocator().execute(
            AllocationCommand(
                donation_id=DONATION_ID,
                community_id=COMMUNITY_A.community_id,
                quantity_kg=60,
                driver_id=DRIVER_2.driver_id,
                origin=STORE_LOCATION,
            )
        )
    assert raised.value.code is ErrorCode.DRIVER_CAPACITY_EXCEEDED
    assert_unallocated_demo_state(database, COMMUNITY_A.community_id)
    assert_one_durable_failure(database, ErrorCode.DRIVER_CAPACITY_EXCEEDED)


def test_closed_recipient_is_rejected_with_no_partial_writes_and_durable_failure_audit(
    database: DatabaseHarness,
) -> None:
    """A FLAGGED CLOSED -> allocation -> typed window failure and atomic rollback."""
    with database.uow() as uow:
        community = uow.communities.get(COMMUNITY_A.community_id)
        assert community is not None
        uow.communities.save(community.model_copy(update={"is_open": False}))
        uow.commit()

    with pytest.raises(EligibilityError) as raised:
        allocate_a(database)

    assert raised.value.code is ErrorCode.RECEIVING_WINDOW_CLOSED
    assert_unallocated_demo_state(database, COMMUNITY_A.community_id)
    assert_one_durable_failure(database, ErrorCode.RECEIVING_WINDOW_CLOSED)


def test_route_after_deadline_is_rejected_with_no_partial_writes_and_durable_failure_audit(
    database: DatabaseHarness,
) -> None:
    """ETA AFTER DONATION DEADLINE -> allocation -> typed deadline failure and rollback."""
    with database.uow() as uow:
        donation = uow.donations.get(DONATION_ID)
        assert donation is not None
        item = donation.items[0].model_copy(
            update={"delivery_deadline": DEMO_NOW + timedelta(minutes=1)}
        )
        uow.donations.add(donation.model_copy(update={"items": [item]}))
        uow.commit()

    with pytest.raises(EligibilityError) as raised:
        allocate_a(database)

    assert raised.value.code is ErrorCode.DELIVERY_DEADLINE_MISSED
    assert_unallocated_demo_state(database, COMMUNITY_A.community_id)
    assert_one_durable_failure(database, ErrorCode.DELIVERY_DEADLINE_MISSED)


def test_mid_acceptance_inventory_failure_rolls_back_every_change_but_failure_audit_survives(
    database: DatabaseHarness,
) -> None:
    """ORDER 60 BUT ONLY 59 RESERVED -> confirm -> zero partial writes, durable failure audit."""
    order = allocate_a(database)
    with database.uow() as uow:
        inventory = uow.donations.get_inventory(DONATION_ID)
        assert inventory is not None
        uow.donations.save_inventory(
            inventory.model_copy(update={"available_kg": 1, "reserved_kg": 59})
        )
        uow.commit()

    with pytest.raises(QuantityIntegrityError) as raised:
        RecordAcceptance(database.uow(), PinnedClock(DEMO_NOW)).execute(
            order.order_id, 35, "integration constraint failure"
        )

    assert raised.value.code is ErrorCode.INSUFFICIENT_INVENTORY
    with database.uow() as uow:
        persisted_order = uow.deliveries.get(order.order_id)
        inventory = uow.donations.get_inventory(DONATION_ID)
        community = uow.communities.get(COMMUNITY_A.community_id)
        assert persisted_order is not None
        assert inventory is not None
        assert community is not None
        assert persisted_order.status is DeliveryStatus.CREATED
        assert (inventory.available_kg, inventory.reserved_kg) == (1, 59)
        assert community.declared_capacity_kg == 60
        assert community.remaining_capacity_kg == 0
    assert_one_durable_failure(
        database, ErrorCode.INSUFFICIENT_INVENTORY, action="partial_acceptance_failed"
    )
