from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import (
    AllocationStatusEvent,
    DeliveryStatusEvent,
    DonationStatusEvent,
    FoodConditionObservation,
    RouteInputSnapshot,
    confirmed_allocation_statement,
    confirmed_delivery_statement,
)
from backend.tests.fixtures.synthetic_food_diversion import (
    build_listed_scenario,
    complete_successful_delivery,
    confirm_barcode_item_allocation,
)


def test_phase10c_builds_frozen_route_and_successful_selected_item_delivery(
    postgres_session: Session,
) -> None:
    listed = build_listed_scenario(postgres_session)
    confirmed = confirm_barcode_item_allocation(postgres_session, listed)
    completed = complete_successful_delivery(postgres_session, confirmed)
    postgres_session.commit()

    assert completed.route_run.status == "committed"
    assert completed.route_run.planned_departure_at < completed.delivery.completed_at
    assert completed.route_decision.decision_type == "driver_confirmation"
    assert completed.route_decision.decision == "approved"
    assert completed.route_decision.actor_user_id == listed.driver.id
    assert completed.route_proposal.proposal_status == "selected"
    assert completed.route_proposal.priority_reasons["distance"] == "tie_breaker_only"
    assert completed.route_proposal.priority_reasons["traffic_weather_road"] == "included"

    snapshot_kinds = {snapshot.input_kind for snapshot in completed.route_snapshots}
    assert snapshot_kinds == {
        "traffic",
        "weather",
        "road",
        "eta",
        "allocation",
        "condition",
        "capacity",
        "location",
    }
    assert all(
        snapshot.valid_from <= completed.route_run.planned_departure_at < snapshot.valid_until
        for snapshot in completed.route_snapshots
    )

    location_snapshot = next(
        snapshot for snapshot in completed.route_snapshots if snapshot.input_kind == "location"
    )
    assert location_snapshot.payload == {
        "origin_location_id": str(listed.kiwiharvest_location.id),
        "pickup_location_id": str(listed.woolworths_location.id),
        "delivery_location_id": str(listed.recipient_a_location.id),
    }
    assert completed.route_proposal.proposal_payload["origin"] == str(
        listed.kiwiharvest_location.id
    )

    assert completed.delivery.status == "completed"
    assert completed.delivery.started_at is not None
    assert completed.delivery.completed_at is not None
    assert completed.pickup_stop.stop_type == "pickup"
    assert completed.pickup_stop.site_id == listed.woolworths_store.id
    assert completed.pickup_stop.site_location_id == listed.woolworths_location.id
    assert completed.delivery_stop.stop_type == "delivery"
    assert completed.delivery_stop.site_id == listed.recipient_a_site.id
    assert completed.delivery_stop.site_location_id == listed.recipient_a_location.id
    assert completed.delivery_allocation.pickup_stop_id == completed.pickup_stop.id
    assert completed.delivery_allocation.delivery_stop_id == completed.delivery_stop.id

    delivery_events = postgres_session.scalars(
        select(DeliveryStatusEvent)
        .where(DeliveryStatusEvent.delivery_id == completed.delivery.id)
        .order_by(DeliveryStatusEvent.occurred_at)
    ).all()
    assert [event.event_type for event in delivery_events] == [
        "assigned",
        "started",
        "arrived",
        "collected",
        "arrived",
        "delivered",
        "completed",
    ]
    assert delivery_events[2].stop_id == completed.pickup_stop.id
    assert delivery_events[3].stop_id == completed.pickup_stop.id
    assert delivery_events[4].stop_id == completed.delivery_stop.id
    assert delivery_events[5].stop_id == completed.delivery_stop.id

    allocation_events = postgres_session.scalars(
        select(AllocationStatusEvent)
        .where(AllocationStatusEvent.allocation_id == confirmed.allocation.id)
        .order_by(AllocationStatusEvent.occurred_at)
    ).all()
    assert [event.event_type for event in allocation_events] == [
        "reserved",
        "confirmed",
        "fulfilled",
    ]
    assert confirmed.allocation.status == "fulfilled"
    assert confirmed.allocation.fulfilled_at == completed.delivery.completed_at
    assert postgres_session.scalars(confirmed_allocation_statement()).all() == []
    assert postgres_session.scalars(confirmed_delivery_statement()).all() == [completed.delivery]


def test_phase10c_records_condition_history_for_selected_chilled_item(
    postgres_session: Session,
) -> None:
    listed = build_listed_scenario(postgres_session)
    confirmed = confirm_barcode_item_allocation(postgres_session, listed)
    completed = complete_successful_delivery(postgres_session, confirmed)
    postgres_session.commit()

    conditions = postgres_session.scalars(
        select(FoodConditionObservation)
        .where(FoodConditionObservation.donation_item_id == listed.barcode_item.id)
        .order_by(FoodConditionObservation.observed_at)
    ).all()
    assert [condition.checkpoint for condition in conditions] == [
        "listing",
        "pickup",
        "delivery",
    ]
    assert [condition.temperature_celsius for condition in conditions] == [
        Decimal("4.00"),
        Decimal("4.30"),
        Decimal("4.70"),
    ]
    assert completed.pickup_condition.id == conditions[1].id
    assert completed.delivery_condition.id == conditions[2].id


def test_phase10c_preserves_route_input_payload_and_does_not_close_partial_donation(
    postgres_session: Session,
) -> None:
    listed = build_listed_scenario(postgres_session)
    confirmed = confirm_barcode_item_allocation(postgres_session, listed)
    completed = complete_successful_delivery(postgres_session, confirmed)
    expected_payloads = {
        snapshot.id: dict(snapshot.payload) for snapshot in completed.route_snapshots
    }
    postgres_session.commit()

    stored_snapshots = postgres_session.scalars(
        select(RouteInputSnapshot)
        .where(RouteInputSnapshot.route_planning_run_id == completed.route_run.id)
    ).all()
    assert {
        snapshot.id: dict(snapshot.payload) for snapshot in stored_snapshots
    } == expected_payloads
    assert listed.donation.status == "listed"

    donation_events = postgres_session.scalars(
        select(DonationStatusEvent)
        .where(DonationStatusEvent.donation_id == listed.donation.id)
        .order_by(DonationStatusEvent.occurred_at)
    ).all()
    assert [event.event_type for event in donation_events] == ["created", "listed"]
