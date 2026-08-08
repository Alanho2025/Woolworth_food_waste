"""Delivery state and explicit-origin edges through real contracts and policies."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from backend.app.contracts.core import DeliveryOrder, DeliveryStatus, Location, RouteLeg
from backend.app.domain.delivery_state import steps_to_arrival, transition
from backend.app.domain.errors import ErrorCode, StateTransitionError

AUCKLAND = ZoneInfo("Pacific/Auckland")
NOW = datetime(2026, 8, 8, 15, 45, tzinfo=AUCKLAND)
STORE = Location(name="Woolworths Mount Eden", latitude=-36.877, longitude=174.7645)
COMMUNITY_A = Location(name="Community A", latitude=-36.9082, longitude=174.7387)
COMMUNITY_D = Location(name="Community D", latitude=-36.8985, longitude=174.809)


def rematch_order(status: DeliveryStatus = DeliveryStatus.CREATED) -> DeliveryOrder:
    route = RouteLeg(
        origin=COMMUNITY_A,
        destination=COMMUNITY_D,
        polyline=[
            (COMMUNITY_A.latitude, COMMUNITY_A.longitude),
            (COMMUNITY_D.latitude, COMMUNITY_D.longitude),
        ],
        distance_km=8.0,
        duration_minutes=16,
        eta=NOW.replace(hour=16, minute=1),
        simulated=True,
    )
    return DeliveryOrder(
        order_id="DO-REMATCH",
        donation_id="DON-1",
        origin=COMMUNITY_A,
        destination_community_id="D",
        quantity_kg=25,
        driver_id="DRV-1",
        route=route,
        status=status,
        deadline=NOW.replace(hour=19),
        is_rematch=True,
    )


def test_rematch_delivery_origin_is_explicit_community_a_and_not_the_donating_store() -> None:
    """REMATCH ORDER -> inspect origin -> Community A, with no phantom store return."""
    order = rematch_order()
    assert order.origin == COMMUNITY_A
    assert order.origin != STORE
    assert order.route.origin == COMMUNITY_A


def test_delivery_order_without_explicit_origin_is_rejected_at_contract_boundary() -> None:
    """ORDER PAYLOAD WITHOUT ORIGIN -> validate -> ValidationError."""
    payload = rematch_order().model_dump()
    payload.pop("origin")
    with pytest.raises(ValidationError):
        DeliveryOrder.model_validate(payload)


def test_created_delivery_follows_every_real_legal_transition_to_completion() -> None:
    """CREATED ORDER -> legal transition path -> COMPLETED."""
    order = rematch_order()
    for target in (
        DeliveryStatus.DRIVER_ASSIGNED,
        DeliveryStatus.IN_TRANSIT,
        DeliveryStatus.ARRIVED,
        DeliveryStatus.PARTIALLY_ACCEPTED,
        DeliveryStatus.COMPLETED,
    ):
        order = transition(order, target)
    assert order.status is DeliveryStatus.COMPLETED


def test_skipping_from_created_directly_to_completed_raises_typed_state_error() -> None:
    """CREATED ORDER -> transition directly to COMPLETED -> INVALID_STATE_TRANSITION."""
    with pytest.raises(StateTransitionError) as raised:
        transition(rematch_order(), DeliveryStatus.COMPLETED)
    assert raised.value.code is ErrorCode.INVALID_STATE_TRANSITION


def test_terminal_completed_delivery_cannot_be_arrived_or_confirmed_again() -> None:
    """COMPLETED ORDER -> move backward -> INVALID_STATE_TRANSITION."""
    completed = rematch_order(DeliveryStatus.COMPLETED)
    with pytest.raises(StateTransitionError) as raised:
        transition(completed, DeliveryStatus.ARRIVED)
    assert raised.value.code is ErrorCode.INVALID_STATE_TRANSITION
    with pytest.raises(StateTransitionError):
        steps_to_arrival(completed.status)
