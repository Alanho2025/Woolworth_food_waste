"""P2 35/25 acceptance and rematch journey through real services and SQLite."""

from __future__ import annotations

from backend.app.application.allocate_donation import AllocationCommand
from backend.app.application.record_acceptance import RecordAcceptance
from backend.app.application.rematch import RematchRemaining
from backend.app.domain.clock import DEMO_NOW, PinnedClock
from backend.app.domain.errors import ErrorCode
from backend.app.seed.data import (
    COMMUNITY_A,
    COMMUNITY_C,
    COMMUNITY_D,
    DONATION_ID,
    DRIVER_1,
    STORE_LOCATION,
)

from .conftest import DatabaseHarness


def services(database: DatabaseHarness):
    clock = PinnedClock(DEMO_NOW)
    allocator = database.allocator(clock)
    acceptance = RecordAcceptance(database.uow(), clock)
    rematch = RematchRemaining(database.uow(), allocator)
    return allocator, acceptance, rematch


def test_partial_acceptance_then_rematch_persists_exact_35_25_without_duplication(
    database: DatabaseHarness,
) -> None:
    """A GETS 60, ACCEPTS 35, D GETS 25 -> two real orders and balanced ledger."""
    allocator, acceptance, rematch = services(database)
    first_order = allocator.execute(
        AllocationCommand(
            donation_id=DONATION_ID,
            community_id=COMMUNITY_A.community_id,
            quantity_kg=60,
            driver_id=DRIVER_1.driver_id,
            origin=STORE_LOCATION,
        )
    )

    accepted = acceptance.execute(first_order.order_id, 35, "Capacity corrected on arrival")
    context = rematch.context_for(first_order.order_id, accepted.outcome.remaining_kg)
    proposal = rematch.propose(context)
    second_order = rematch.execute(context, COMMUNITY_D.community_id)

    assert accepted.outcome.accepted_kg == 35
    assert accepted.outcome.remaining_kg == 25
    assert proposal.plan.is_split is False
    assert proposal.plan.primary_community_id == COMMUNITY_D.community_id
    candidates = {item.community.community_id: item for item in proposal.candidates}
    assert ErrorCode.RECIPIENT_DECLINED_THIS_DONATION in {
        reason.code for reason in candidates[COMMUNITY_A.community_id].exclusions
    }
    assert ErrorCode.RECIPIENT_CAPACITY_EXCEEDED in {
        reason.code for reason in candidates[COMMUNITY_C.community_id].exclusions
    }
    assert second_order.quantity_kg == 25
    assert second_order.origin == COMMUNITY_A.location
    assert second_order.route.origin == COMMUNITY_A.location
    assert second_order.destination_community_id == COMMUNITY_D.community_id
    assert second_order.driver_id == first_order.driver_id == DRIVER_1.driver_id
    assert second_order.is_rematch is True

    with database.uow() as uow:
        inventory = uow.donations.get_inventory(DONATION_ID)
        a = uow.communities.get(COMMUNITY_A.community_id)
        d = uow.communities.get(COMMUNITY_D.community_id)
        orders = uow.deliveries.list_for_donation(DONATION_ID)
        assert inventory is not None
        assert a is not None
        assert d is not None
        assert (inventory.available_kg, inventory.reserved_kg) == (0, 25)
        assert (inventory.in_transit_kg, inventory.delivered_kg) == (0, 35)
        assert inventory.is_balanced is True
        assert a.declared_capacity_kg == 35
        assert a.remaining_capacity_kg == 0
        assert d.declared_capacity_kg == 30
        assert d.remaining_capacity_kg == 5
        assert len(orders) == 2
        assert sorted(order.quantity_kg for order in orders) == [25, 60]


def test_repeating_partial_confirmation_after_rematch_reservation_returns_original_35_25(
    database: DatabaseHarness,
) -> None:
    """25 ALREADY RESERVED TO D -> retry A confirmation -> original outcome, no mutation."""
    allocator, acceptance, rematch = services(database)
    first_order = allocator.execute(
        AllocationCommand(
            donation_id=DONATION_ID,
            community_id=COMMUNITY_A.community_id,
            quantity_kg=60,
            driver_id=DRIVER_1.driver_id,
            origin=STORE_LOCATION,
        )
    )
    first_result = acceptance.execute(first_order.order_id, 35)
    context = rematch.context_for(first_order.order_id, first_result.outcome.remaining_kg)
    second_order = rematch.execute(context, COMMUNITY_D.community_id)

    retried = acceptance.execute(first_order.order_id, 35)

    assert retried.outcome.accepted_kg == 35
    assert retried.outcome.remaining_kg == 25
    with database.uow() as uow:
        inventory = uow.donations.get_inventory(DONATION_ID)
        orders = uow.deliveries.list_for_donation(DONATION_ID)
        assert inventory is not None
        assert (inventory.available_kg, inventory.reserved_kg) == (0, 25)
        assert (inventory.in_transit_kg, inventory.delivered_kg) == (0, 35)
        assert inventory.is_balanced is True
        assert {order.order_id for order in orders} == {first_order.order_id, second_order.order_id}


def test_rematch_retry_is_idempotent_and_does_not_reserve_the_twenty_five_twice(
    database: DatabaseHarness,
) -> None:
    """SAME D REMATCH TWICE -> same order, one 25 kg reservation."""
    allocator, acceptance, rematch = services(database)
    first_order = allocator.execute(
        AllocationCommand(
            donation_id=DONATION_ID,
            community_id=COMMUNITY_A.community_id,
            quantity_kg=60,
            driver_id=DRIVER_1.driver_id,
            origin=STORE_LOCATION,
        )
    )
    result = acceptance.execute(first_order.order_id, 35)
    context = rematch.context_for(first_order.order_id, result.outcome.remaining_kg)

    first_rematch = rematch.execute(context, COMMUNITY_D.community_id)
    second_rematch = rematch.execute(context, COMMUNITY_D.community_id)

    assert second_rematch.order_id == first_rematch.order_id
    with database.uow() as uow:
        inventory = uow.donations.get_inventory(DONATION_ID)
        assert inventory is not None
        assert inventory.reserved_kg == 25
        assert inventory.delivered_kg == 35
        assert len(uow.deliveries.list_for_donation(DONATION_ID)) == 2
