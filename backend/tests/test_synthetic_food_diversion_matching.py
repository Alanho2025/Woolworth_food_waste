from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import (
    AllocationStatusEvent,
    DonationItem,
    MatchDecision,
    confirmed_allocation_statement,
)
from backend.tests.fixtures.synthetic_food_diversion import (
    build_listed_scenario,
    confirm_barcode_item_allocation,
)


def test_phase10b_builds_candidates_decisions_and_confirmed_allocation(
    postgres_session: Session,
) -> None:
    listed = build_listed_scenario(postgres_session)
    confirmed = confirm_barcode_item_allocation(postgres_session, listed)
    postgres_session.commit()

    assert confirmed.match_run.donation_item_id == listed.barcode_item.id
    assert confirmed.match_run.status == "completed"
    assert confirmed.recipient_a_candidate.feasibility_status == "feasible"
    assert confirmed.recipient_a_candidate.agent_rank == 1
    assert confirmed.recipient_a_candidate.reason_components == {
        "classified_food_category": "dairy",
        "capacity_status": "known",
        "available_quantity": "30.000",
        "required_quantity": "10.000",
        "quantity_unit": "kg",
        "need_priority": 5,
        "safe_deadline_feasible": True,
    }
    assert confirmed.recipient_b_candidate.feasibility_status == "manual_review"
    assert confirmed.recipient_b_candidate.agent_rank is None
    assert confirmed.recipient_b_candidate.reason_code == "unknown_capacity"

    decisions = postgres_session.scalars(
        select(MatchDecision).where(
            MatchDecision.match_candidate_id == confirmed.recipient_a_candidate.id
        )
    ).all()
    assert {(decision.decision_type, decision.decision) for decision in decisions} == {
        ("driver_confirmation", "confirmed"),
        ("recipient_acceptance", "accepted"),
    }
    assert confirmed.driver_confirmation.actor_user_id == listed.driver.id
    assert confirmed.recipient_acceptance.actor_user_id == listed.recipient_a_responder.id

    allocation = confirmed.allocation
    assert allocation.status == "confirmed"
    assert allocation.donation_item_id == listed.barcode_item.id
    assert allocation.recipient_site_id == listed.recipient_a_site.id
    assert allocation.allocated_quantity == 10
    assert allocation.quantity_unit == listed.barcode_item.quantity_unit
    assert allocation.confirmed_by_user_id == listed.recipient_a_responder.id

    confirmed_rows = postgres_session.scalars(confirmed_allocation_statement()).all()
    assert [row.id for row in confirmed_rows] == [allocation.id]

    allocation_events = postgres_session.scalars(
        select(AllocationStatusEvent)
        .where(AllocationStatusEvent.allocation_id == allocation.id)
        .order_by(AllocationStatusEvent.occurred_at)
    ).all()
    assert [event.event_type for event in allocation_events] == ["reserved", "confirmed"]


def test_phase10b_no_barcode_item_remains_unallocated_at_confirmed_checkpoint(
    postgres_session: Session,
) -> None:
    listed = build_listed_scenario(postgres_session)
    confirmed = confirm_barcode_item_allocation(postgres_session, listed)
    postgres_session.commit()

    allocated_items = postgres_session.scalars(
        select(DonationItem).where(
            DonationItem.id == confirmed.allocation.donation_item_id
        )
    ).all()
    assert [item.id for item in allocated_items] == [listed.barcode_item.id]
    assert listed.no_barcode_item.id != confirmed.allocation.donation_item_id

