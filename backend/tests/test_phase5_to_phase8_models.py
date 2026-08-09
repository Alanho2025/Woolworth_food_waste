from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.models import (
    Allocation,
    AllocationStatusEvent,
    Delivery,
    DeliveryAllocation,
    DeliveryStatusEvent,
    DeliveryStop,
    Donation,
    DonationItem,
    DonationStatusEvent,
    FoodConditionObservation,
    FoodProduct,
    MatchCandidate,
    MatchDecision,
    MatchRun,
    Organisation,
    RecipientAvailabilitySnapshot,
    RecipientCapability,
    RecipientNeed,
    RouteDecision,
    RouteInputSnapshot,
    RoutePlanningRun,
    RouteProposal,
    Site,
    SiteLocation,
    User,
    confirmed_allocation_statement,
    current_recipient_availability_statement,
    public_recipient_availability_statement,
)


def _create_core_graph(
    postgres_session: Session,
) -> tuple[
    Organisation,
    Site,
    Site,
    User,
    User,
    User,
]:
    organisation = Organisation(name="KiwiHarvest test organisation")
    donor_site = Site(name="Donor site", site_type="store")
    recipient_site = Site(name="Recipient site", site_type="service_site")
    organisation.sites.extend([donor_site, recipient_site])
    donor_user = User(display_name="Donor operator")
    driver = User(display_name="Driver")
    recipient_user = User(display_name="Recipient responder")
    postgres_session.add_all([organisation, donor_user, driver, recipient_user])
    postgres_session.flush()
    return organisation, donor_site, recipient_site, donor_user, driver, recipient_user


def _create_donation(
    postgres_session: Session,
    *,
    donor_site: Site,
    donor_user: User,
    product_id=None,
    quantity: Decimal = Decimal("25.000"),
    gtin_snapshot: str | None = "01234567890128",
) -> tuple[Donation, DonationItem]:
    now = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)
    donation = Donation(
        source_site_id=donor_site.id,
        created_by_user_id=donor_user.id,
        pickup_window_start=now,
        pickup_window_end=now + timedelta(hours=2),
        safe_deadline=now + timedelta(hours=6),
        status="listed",
    )
    item = DonationItem(
        line_number=1,
        food_product_id=product_id,
        product_name_snapshot="Example chilled yoghurt",
        brand_snapshot="Example Brand",
        variant_snapshot="Plain",
        gtin_snapshot=gtin_snapshot,
        lot_code="LOT-001",
        quantity=quantity,
        quantity_unit="kg",
        storage_class="chilled",
        date_mark_type="use_by",
        date_mark=datetime(2026, 8, 11, tzinfo=UTC).date(),
        packaging_condition="sealed",
        recall_status="not_recalled",
    )
    donation.items.append(item)
    postgres_session.add(donation)
    postgres_session.flush()
    return donation, item


def _create_match_candidate(
    postgres_session: Session,
    *,
    item: DonationItem,
    recipient_site: Site,
    status: str = "feasible",
    reason_code: str = "eligible",
) -> tuple[MatchRun, MatchCandidate]:
    run = MatchRun(
        donation_item_id=item.id,
        policy_version="matching-v1",
        status="completed",
        completed_at=datetime(2026, 8, 9, 12, 30, tzinfo=UTC),
    )
    postgres_session.add(run)
    postgres_session.flush()
    candidate = MatchCandidate(
        match_run_id=run.id,
        recipient_site_id=recipient_site.id,
        feasibility_status=status,
        reason_code=reason_code,
        reason_components={"capacity_kg": 15, "required_kg": 25},
        agent_rank=1 if status == "feasible" else None,
        priority_score=Decimal("0.850000") if status == "feasible" else None,
    )
    postgres_session.add(candidate)
    postgres_session.flush()
    return run, candidate


def _add_operational_locations(
    donor_site: Site,
    recipient_site: Site,
    now: datetime,
) -> tuple[SiteLocation, SiteLocation]:
    pickup_location = SiteLocation(
        location_type="pickup_point",
        precision_level="exact",
        verification_status="operator_confirmed",
        visibility="operational",
        latitude=Decimal("-36.848500"),
        longitude=Decimal("174.763300"),
        valid_from=now - timedelta(hours=1),
        verified_at=now - timedelta(hours=2),
    )
    receiving_location = SiteLocation(
        location_type="receiving_point",
        precision_level="exact",
        verification_status="operator_confirmed",
        visibility="operational",
        latitude=Decimal("-36.858500"),
        longitude=Decimal("174.773300"),
        valid_from=now - timedelta(hours=1),
        verified_at=now - timedelta(hours=2),
    )
    donor_site.locations.append(pickup_location)
    recipient_site.locations.append(receiving_location)
    return pickup_location, receiving_location


def test_phase5_schema_preserves_item_snapshot_and_condition_history(
    postgres_session: Session,
) -> None:
    _, donor_site, _, donor_user, _, _ = _create_core_graph(postgres_session)
    product = FoodProduct(
        gtin="01234567890128",
        product_name="Current yoghurt name",
    )
    postgres_session.add(product)
    postgres_session.flush()
    donation, item = _create_donation(
        postgres_session,
        donor_site=donor_site,
        donor_user=donor_user,
        product_id=product.id,
    )
    observed_at = datetime(2026, 8, 9, 12, 15, tzinfo=UTC)
    postgres_session.add_all(
        [
            FoodConditionObservation(
                donation_item_id=item.id,
                observed_by_user_id=donor_user.id,
                checkpoint="listing",
                condition_status="acceptable",
                temperature_celsius=Decimal("4.00"),
                observed_at=observed_at,
            ),
            DonationStatusEvent(
                donation_id=donation.id,
                event_type="listed",
                actor_type="user",
                actor_user_id=donor_user.id,
                occurred_at=observed_at,
            ),
        ]
    )
    postgres_session.commit()

    product.product_name = "Renamed product master"
    postgres_session.commit()
    postgres_session.refresh(item)

    assert item.product_name_snapshot == "Example chilled yoghurt"
    assert len(item.condition_observations) == 1
    assert donation.status_events[0].event_type == "listed"


def test_phase5_no_barcode_item_is_valid_but_nonpositive_quantity_is_not(
    postgres_session: Session,
) -> None:
    _, donor_site, _, donor_user, _, _ = _create_core_graph(postgres_session)
    _, item = _create_donation(
        postgres_session,
        donor_site=donor_site,
        donor_user=donor_user,
        product_id=None,
        gtin_snapshot=None,
    )
    postgres_session.commit()
    assert item.food_product_id is None
    assert item.gtin_snapshot is None

    with pytest.raises(IntegrityError):
        _create_donation(
            postgres_session,
            donor_site=donor_site,
            donor_user=donor_user,
            quantity=Decimal("0"),
        )
        postgres_session.commit()


def test_phase6_separates_capability_need_and_fresh_capacity(
    postgres_session: Session,
) -> None:
    _, _, recipient_site, _, _, recipient_user = _create_core_graph(postgres_session)
    now = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)
    postgres_session.add_all(
        [
            RecipientCapability(
                site_id=recipient_site.id,
                food_category="dairy",
                storage_class="chilled",
                updated_by_user_id=recipient_user.id,
                valid_from=now - timedelta(days=1),
            ),
            RecipientNeed(
                site_id=recipient_site.id,
                food_category="dairy",
                storage_class="chilled",
                quantity=Decimal("20.000"),
                quantity_unit="kg",
                priority=5,
                receiving_window_start=now,
                receiving_window_end=now + timedelta(hours=4),
                valid_from=now - timedelta(hours=1),
                updated_by_user_id=recipient_user.id,
            ),
            RecipientAvailabilitySnapshot(
                site_id=recipient_site.id,
                food_category="dairy",
                storage_class="chilled",
                capacity_status="known",
                available_quantity=Decimal("10.000"),
                quantity_unit="kg",
                receiving_window_start=now,
                receiving_window_end=now + timedelta(hours=4),
                observed_at=now - timedelta(hours=3),
                valid_from=now - timedelta(hours=3),
                valid_until=now - timedelta(hours=1),
                updated_by_user_id=recipient_user.id,
            ),
            RecipientAvailabilitySnapshot(
                site_id=recipient_site.id,
                food_category="dairy",
                storage_class="chilled",
                capacity_status="known",
                available_quantity=Decimal("15.000"),
                quantity_unit="kg",
                receiving_window_start=now,
                receiving_window_end=now + timedelta(hours=4),
                observed_at=now - timedelta(minutes=10),
                valid_from=now - timedelta(hours=1),
                valid_until=now + timedelta(hours=1),
                updated_by_user_id=recipient_user.id,
            ),
        ]
    )
    postgres_session.commit()

    current = postgres_session.scalars(current_recipient_availability_statement(as_of=now)).all()

    assert len(current) == 1
    assert current[0].available_quantity == Decimal("15.000")


def test_phase6_unknown_capacity_is_not_zero_and_protected_state_is_hidden(
    postgres_session: Session,
) -> None:
    _, _, recipient_site, _, _, recipient_user = _create_core_graph(postgres_session)
    now = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)
    postgres_session.add_all(
        [
            RecipientAvailabilitySnapshot(
                site_id=recipient_site.id,
                food_category="ambient",
                storage_class="ambient",
                capacity_status="unknown",
                available_quantity=None,
                quantity_unit="kg",
                receiving_window_start=now,
                receiving_window_end=now + timedelta(hours=4),
                observed_at=now,
                valid_from=now - timedelta(minutes=1),
                valid_until=now + timedelta(hours=1),
                updated_by_user_id=recipient_user.id,
                visibility="operational",
            ),
            RecipientAvailabilitySnapshot(
                site_id=recipient_site.id,
                food_category="protected_food",
                storage_class="ambient",
                capacity_status="known",
                available_quantity=Decimal("5.000"),
                quantity_unit="kg",
                receiving_window_start=now,
                receiving_window_end=now + timedelta(hours=4),
                observed_at=now,
                valid_from=now - timedelta(minutes=1),
                valid_until=now + timedelta(hours=1),
                updated_by_user_id=recipient_user.id,
                visibility="protected",
            ),
        ]
    )
    postgres_session.commit()

    public_rows = postgres_session.scalars(public_recipient_availability_statement(as_of=now)).all()

    assert len(public_rows) == 1
    assert public_rows[0].capacity_status == "unknown"
    assert public_rows[0].available_quantity is None


def test_phase7_keeps_exclusion_reason_decisions_and_confirmed_allocation(
    postgres_session: Session,
) -> None:
    _, donor_site, recipient_site, donor_user, driver, recipient_user = _create_core_graph(
        postgres_session
    )
    _, item = _create_donation(
        postgres_session,
        donor_site=donor_site,
        donor_user=donor_user,
    )
    _, candidate = _create_match_candidate(
        postgres_session,
        item=item,
        recipient_site=recipient_site,
    )
    postgres_session.add_all(
        [
            MatchDecision(
                match_candidate_id=candidate.id,
                decision_type="driver_confirmation",
                decision="confirmed",
                actor_user_id=driver.id,
            ),
            MatchDecision(
                match_candidate_id=candidate.id,
                decision_type="recipient_acceptance",
                decision="accepted",
                actor_user_id=recipient_user.id,
            ),
        ]
    )
    allocation = Allocation(
        donation_item_id=item.id,
        recipient_site_id=recipient_site.id,
        match_candidate_id=candidate.id,
        allocated_quantity=Decimal("25.000"),
        quantity_unit="kg",
        status="confirmed",
        reserved_by_user_id=driver.id,
        confirmed_by_user_id=recipient_user.id,
        confirmed_at=datetime(2026, 8, 9, 13, 0, tzinfo=UTC),
    )
    postgres_session.add(allocation)
    postgres_session.flush()
    postgres_session.add(
        AllocationStatusEvent(
            allocation_id=allocation.id,
            event_type="confirmed",
            actor_type="user",
            actor_user_id=recipient_user.id,
            occurred_at=datetime(2026, 8, 9, 13, 0, tzinfo=UTC),
        )
    )
    postgres_session.commit()

    confirmed = postgres_session.scalars(confirmed_allocation_statement()).all()
    assert confirmed == [allocation]
    assert candidate.reason_components["required_kg"] == 25


def test_phase7_only_one_active_allocation_can_use_an_item(
    postgres_session: Session,
) -> None:
    organisation, donor_site, recipient_site, donor_user, driver, recipient_user = (
        _create_core_graph(postgres_session)
    )
    _, item = _create_donation(
        postgres_session,
        donor_site=donor_site,
        donor_user=donor_user,
    )
    _, first_candidate = _create_match_candidate(
        postgres_session,
        item=item,
        recipient_site=recipient_site,
    )
    first_allocation = Allocation(
        donation_item_id=item.id,
        recipient_site_id=recipient_site.id,
        match_candidate_id=first_candidate.id,
        allocated_quantity=Decimal("25.000"),
        quantity_unit="kg",
        reserved_by_user_id=driver.id,
    )
    postgres_session.add(first_allocation)
    postgres_session.commit()

    second_site = Site(name="Second recipient site", site_type="service_site")
    organisation.sites.append(second_site)
    postgres_session.flush()
    _, second_candidate = _create_match_candidate(
        postgres_session,
        item=item,
        recipient_site=second_site,
    )
    postgres_session.add(
        Allocation(
            donation_item_id=item.id,
            recipient_site_id=second_site.id,
            match_candidate_id=second_candidate.id,
            allocated_quantity=Decimal("25.000"),
            quantity_unit="kg",
            reserved_by_user_id=recipient_user.id,
        )
    )

    with pytest.raises(IntegrityError):
        postgres_session.commit()


def test_phase8_preserves_inputs_proposal_decision_and_actual_stop_order(
    postgres_session: Session,
) -> None:
    _, donor_site, recipient_site, donor_user, driver, recipient_user = _create_core_graph(
        postgres_session
    )
    now = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)
    pickup_location, receiving_location = _add_operational_locations(
        donor_site,
        recipient_site,
        now,
    )
    _, item = _create_donation(
        postgres_session,
        donor_site=donor_site,
        donor_user=donor_user,
    )
    _, candidate = _create_match_candidate(
        postgres_session,
        item=item,
        recipient_site=recipient_site,
    )
    allocation = Allocation(
        donation_item_id=item.id,
        recipient_site_id=recipient_site.id,
        match_candidate_id=candidate.id,
        allocated_quantity=Decimal("25.000"),
        quantity_unit="kg",
        status="confirmed",
        reserved_by_user_id=driver.id,
        confirmed_by_user_id=recipient_user.id,
        confirmed_at=now,
    )
    postgres_session.add(allocation)
    postgres_session.flush()

    run = RoutePlanningRun(
        driver_user_id=driver.id,
        planning_horizon_start=now,
        planning_horizon_end=now + timedelta(hours=8),
        planned_departure_at=now + timedelta(minutes=15),
        policy_version="route-v1",
        model_identifier="test-agent",
        status="proposal_ready",
    )
    postgres_session.add(run)
    postgres_session.flush()
    postgres_session.add_all(
        [
            RouteInputSnapshot(
                route_planning_run_id=run.id,
                input_kind="traffic",
                provider="test-traffic",
                coverage_reference="Auckland-test-route",
                observed_at=now,
                valid_from=now,
                valid_until=now + timedelta(minutes=15),
                payload={"eta_seconds": 1800},
            ),
            RouteInputSnapshot(
                route_planning_run_id=run.id,
                input_kind="weather",
                provider="test-weather",
                coverage_reference="Auckland",
                observed_at=now,
                valid_from=now,
                valid_until=now + timedelta(hours=1),
                payload={"warning": "none"},
            ),
        ]
    )
    proposal = RouteProposal(
        route_planning_run_id=run.id,
        version=1,
        proposal_status="selected",
        proposal_payload={
            "stops": [str(pickup_location.id), str(receiving_location.id)],
        },
        priority_reasons={"feasibility": "pass", "distance": "tie_breaker"},
        cost_components={"traffic_eta_seconds": 1800},
        total_travel_seconds=Decimal("1800"),
        total_distance_meters=Decimal("12000"),
    )
    postgres_session.add(proposal)
    postgres_session.flush()
    postgres_session.add(
        RouteDecision(
            route_proposal_id=proposal.id,
            decision_type="driver_confirmation",
            decision="approved",
            actor_user_id=driver.id,
            decided_at=now + timedelta(minutes=1),
        )
    )
    postgres_session.flush()
    route_decision = postgres_session.scalars(select(RouteDecision)).one()
    delivery = Delivery(
        route_decision_id=route_decision.id,
        driver_user_id=driver.id,
        planned_departure_at=now + timedelta(minutes=15),
    )
    delivery.stops.extend(
        [
            DeliveryStop(
                stop_sequence=1,
                actual_sequence=2,
                stop_type="pickup",
                site_id=donor_site.id,
                site_location_id=pickup_location.id,
                status="completed",
                planned_arrival_at=now + timedelta(minutes=30),
                actual_arrival_at=now + timedelta(minutes=35),
                actual_departure_at=now + timedelta(minutes=45),
            ),
            DeliveryStop(
                stop_sequence=2,
                actual_sequence=1,
                stop_type="delivery",
                site_id=recipient_site.id,
                site_location_id=receiving_location.id,
                status="completed",
                planned_arrival_at=now + timedelta(hours=1),
                actual_arrival_at=now + timedelta(minutes=55),
                actual_departure_at=now + timedelta(hours=1, minutes=5),
            ),
        ]
    )
    postgres_session.add(delivery)
    postgres_session.flush()
    postgres_session.add(
        DeliveryAllocation(
            delivery_id=delivery.id,
            allocation_id=allocation.id,
            pickup_stop_id=delivery.stops[0].id,
            delivery_stop_id=delivery.stops[1].id,
        )
    )
    postgres_session.add(
        DeliveryStatusEvent(
            delivery_id=delivery.id,
            stop_id=delivery.stops[1].id,
            event_type="delivered",
            actor_type="user",
            actor_user_id=driver.id,
            occurred_at=now + timedelta(hours=1),
        )
    )
    postgres_session.commit()

    stored_delivery = postgres_session.get(Delivery, delivery.id)
    assert stored_delivery is not None
    planned_sequences = sorted(stop.stop_sequence for stop in stored_delivery.stops)
    actual_by_planned = {stop.stop_sequence: stop.actual_sequence for stop in stored_delivery.stops}
    assert planned_sequences == [1, 2]
    assert actual_by_planned == {1: 2, 2: 1}
    assert proposal.priority_reasons["distance"] == "tie_breaker"
