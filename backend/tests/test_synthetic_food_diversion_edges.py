from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.models import (
    Allocation,
    DeliveryStatusEvent,
    DeliveryStop,
    MatchCandidate,
    MatchDecision,
    MatchRun,
    RouteInputSnapshot,
    RoutePlanningRun,
    RouteProposal,
    confirmed_allocation_statement,
    current_recipient_availability_statement,
)
from backend.tests.fixtures.synthetic_food_diversion import (
    build_listed_scenario,
    complete_successful_delivery,
    confirm_barcode_item_allocation,
)


def test_phase10d_rejects_decision_value_that_does_not_match_decision_type(
    postgres_session: Session,
) -> None:
    listed = build_listed_scenario(postgres_session)
    confirmed = confirm_barcode_item_allocation(postgres_session, listed)
    postgres_session.add(
        MatchDecision(
            id=uuid4(),
            match_candidate_id=confirmed.recipient_b_candidate.id,
            decision_type="driver_confirmation",
            decision="approved",
            actor_user_id=listed.driver.id,
            decided_at=listed.now,
        )
    )

    with pytest.raises(IntegrityError):
        postgres_session.commit()
    postgres_session.rollback()


def test_phase10d_rejects_allocation_candidate_recipient_mismatch(
    postgres_session: Session,
) -> None:
    listed = build_listed_scenario(postgres_session)
    confirmed = confirm_barcode_item_allocation(postgres_session, listed)
    confirmed.allocation.status = "fulfilled"
    confirmed.allocation.fulfilled_at = listed.now + timedelta(minutes=7)
    postgres_session.commit()

    postgres_session.add(
        Allocation(
            id=uuid4(),
            donation_item_id=listed.barcode_item.id,
            recipient_site_id=listed.recipient_b_site.id,
            match_candidate_id=confirmed.recipient_a_candidate.id,
            allocated_quantity=Decimal("10.000"),
            quantity_unit="kg",
            status="reserved",
            reserved_by_user_id=listed.driver.id,
            reserved_at=listed.now + timedelta(minutes=8),
        )
    )

    with pytest.raises(IntegrityError):
        postgres_session.commit()
    postgres_session.rollback()


def test_phase10d_rejects_route_snapshot_with_empty_validity_window(
    postgres_session: Session,
) -> None:
    listed = build_listed_scenario(postgres_session)
    confirmed = confirm_barcode_item_allocation(postgres_session, listed)
    route_run = RoutePlanningRun(
        id=uuid4(),
        driver_user_id=listed.driver.id,
        planning_horizon_start=listed.now,
        planning_horizon_end=listed.now + timedelta(hours=4),
        planned_departure_at=listed.now + timedelta(minutes=20),
        policy_version="synthetic-route-edge-v1",
        status="started",
    )
    postgres_session.add(route_run)
    postgres_session.flush()
    postgres_session.add(
        RouteInputSnapshot(
            id=uuid4(),
            route_planning_run_id=route_run.id,
            input_kind="traffic",
            provider="synthetic_fixture",
            coverage_reference="invalid-window",
            observed_at=listed.now,
            valid_from=listed.now,
            valid_until=listed.now,
            payload={"delay_seconds": 0},
        )
    )
    assert confirmed.allocation.status == "confirmed"

    with pytest.raises(IntegrityError):
        postgres_session.commit()
    postgres_session.rollback()


def test_phase10d_rejects_duplicate_proposal_version_in_one_run(
    postgres_session: Session,
) -> None:
    listed = build_listed_scenario(postgres_session)
    confirm_barcode_item_allocation(postgres_session, listed)
    route_run = RoutePlanningRun(
        id=uuid4(),
        driver_user_id=listed.driver.id,
        planning_horizon_start=listed.now,
        planning_horizon_end=listed.now + timedelta(hours=4),
        planned_departure_at=listed.now + timedelta(minutes=20),
        policy_version="synthetic-route-edge-v1",
        status="proposal_ready",
    )
    postgres_session.add(route_run)
    postgres_session.flush()
    postgres_session.add_all(
        [
            RouteProposal(
                id=uuid4(),
                route_planning_run_id=route_run.id,
                version=1,
                proposal_status="draft",
                proposal_payload={"stops": []},
                priority_reasons={"distance": "tie_breaker_only"},
                cost_components={},
            ),
            RouteProposal(
                id=uuid4(),
                route_planning_run_id=route_run.id,
                version=1,
                proposal_status="draft",
                proposal_payload={"stops": []},
                priority_reasons={"distance": "tie_breaker_only"},
                cost_components={},
            ),
        ]
    )

    with pytest.raises(IntegrityError):
        postgres_session.commit()
    postgres_session.rollback()


def test_phase10d_rejects_stop_location_from_another_site(
    postgres_session: Session,
) -> None:
    listed = build_listed_scenario(postgres_session)
    confirmed = confirm_barcode_item_allocation(postgres_session, listed)
    completed = complete_successful_delivery(postgres_session, confirmed)
    postgres_session.commit()

    postgres_session.add(
        DeliveryStop(
            id=uuid4(),
            delivery_id=completed.delivery.id,
            stop_sequence=3,
            stop_type="delivery",
            site_id=listed.recipient_b_site.id,
            site_location_id=listed.recipient_a_location.id,
            status="planned",
        )
    )

    with pytest.raises(IntegrityError):
        postgres_session.commit()
    postgres_session.rollback()


def test_phase10d_rejects_system_event_with_user_actor(
    postgres_session: Session,
) -> None:
    listed = build_listed_scenario(postgres_session)
    confirmed = confirm_barcode_item_allocation(postgres_session, listed)
    completed = complete_successful_delivery(postgres_session, confirmed)
    postgres_session.commit()

    postgres_session.add(
        DeliveryStatusEvent(
            id=uuid4(),
            delivery_id=completed.delivery.id,
            stop_id=None,
            event_type="completed",
            actor_type="system",
            actor_user_id=listed.driver.id,
            occurred_at=completed.delivery.completed_at,
        )
    )

    with pytest.raises(IntegrityError):
        postgres_session.commit()
    postgres_session.rollback()


def test_phase10d_no_barcode_item_can_still_have_match_evidence(
    postgres_session: Session,
) -> None:
    listed = build_listed_scenario(postgres_session)
    match_run = MatchRun(
        id=uuid4(),
        donation_item_id=listed.no_barcode_item.id,
        requested_by_user_id=listed.driver.id,
        policy_version="synthetic-match-no-barcode-v1",
        status="completed",
        started_at=listed.now,
        completed_at=listed.now + timedelta(minutes=1),
    )
    candidate = MatchCandidate(
        id=uuid4(),
        match_run_id=match_run.id,
        recipient_site_id=listed.recipient_a_site.id,
        feasibility_status="manual_review",
        reason_code="classification_requires_review",
        reason_components={
            "classified_food_category": "produce",
            "barcode_present": False,
        },
        agent_rank=None,
        evaluated_at=listed.now + timedelta(minutes=1),
    )
    postgres_session.add_all([match_run, candidate])
    postgres_session.commit()

    stored_candidate = postgres_session.scalars(
        select(MatchCandidate).where(MatchCandidate.id == candidate.id)
    ).one()
    assert stored_candidate.match_run.donation_item_id == listed.no_barcode_item.id
    assert listed.no_barcode_item.food_product_id is None


def test_phase10d_current_capacity_query_excludes_expired_snapshot(
    postgres_session: Session,
) -> None:
    listed = build_listed_scenario(postgres_session)
    listed.recipient_a_capacity.valid_until = listed.now - timedelta(minutes=1)
    postgres_session.commit()

    current = postgres_session.scalars(
        current_recipient_availability_statement(as_of=listed.now)
    ).all()
    assert {snapshot.site_id for snapshot in current} == {listed.recipient_b_site.id}


def test_phase10d_completed_allocation_is_not_route_eligible_as_confirmed(
    postgres_session: Session,
) -> None:
    listed = build_listed_scenario(postgres_session)
    confirmed = confirm_barcode_item_allocation(postgres_session, listed)
    completed = complete_successful_delivery(postgres_session, confirmed)
    postgres_session.commit()

    assert completed.confirmed.allocation.status == "fulfilled"
    assert postgres_session.scalars(confirmed_allocation_statement()).all() == []
