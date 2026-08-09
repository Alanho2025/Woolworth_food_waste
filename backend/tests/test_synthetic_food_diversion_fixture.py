from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import (
    DonationItem,
    FoodConditionObservation,
    RecipientAvailabilitySnapshot,
    active_membership_statement,
    current_recipient_availability_statement,
    navigation_location_statement,
    source_record_identity_statement,
)
from backend.tests.fixtures.synthetic_food_diversion import (
    SCENARIO_NOW,
    SYNTHETIC_GTIN14,
    build_listed_scenario,
)


def _is_valid_gtin14(value: str) -> bool:
    if len(value) != 14 or not value.isdecimal():
        return False

    body = value[:-1]
    weighted_sum = sum(
        int(digit) * (3 if offset % 2 == 0 else 1)
        for offset, digit in enumerate(reversed(body))
    )
    return (10 - weighted_sum % 10) % 10 == int(value[-1])


def test_phase10a_builds_the_complete_listed_fixture_graph(postgres_session: Session) -> None:
    scenario = build_listed_scenario(postgres_session)
    postgres_session.commit()

    assert scenario.now == SCENARIO_NOW
    assert scenario.woolworths_store.organisation_id == scenario.woolworths.id
    assert scenario.kiwiharvest_hub.organisation_id == scenario.kiwiharvest.id
    assert scenario.recipient_a_site.organisation_id == scenario.recipient_a.id
    assert scenario.recipient_b_site.organisation_id == scenario.recipient_b.id

    assert scenario.barcode_item.food_product_id == scenario.product.id
    assert scenario.barcode_item.gtin_snapshot == SYNTHETIC_GTIN14
    assert scenario.no_barcode_item.food_product_id is None
    assert scenario.no_barcode_item.gtin_snapshot is None
    assert scenario.donation.status == "listed"
    assert {item.line_number for item in scenario.donation.items} == {1, 2}

    assert scenario.listing_condition.checkpoint == "listing"
    assert scenario.listing_condition.condition_status == "acceptable"
    assert scenario.listing_condition.temperature_celsius == Decimal("4.00")

    source_record = postgres_session.scalars(
        source_record_identity_statement(
            source_system="synthetic_fixture",
            source_record_type="product",
            external_record_id="success-path-product-001",
        )
    ).one()
    assert source_record.id == scenario.product_source_record.id
    assert scenario.product.source_record_id == source_record.id


def test_phase10a_fixture_gtin_is_check_digit_valid() -> None:
    assert _is_valid_gtin14(SYNTHETIC_GTIN14)


def test_phase10a_locations_and_memberships_are_current_and_operational(
    postgres_session: Session,
) -> None:
    scenario = build_listed_scenario(postgres_session)
    postgres_session.commit()

    navigation_locations = postgres_session.scalars(
        navigation_location_statement(as_of=SCENARIO_NOW)
    ).all()
    assert {location.id for location in navigation_locations} == {
        scenario.woolworths_location.id,
        scenario.kiwiharvest_location.id,
        scenario.recipient_a_location.id,
        scenario.recipient_b_location.id,
    }
    assert all(location.visibility == "operational" for location in navigation_locations)
    assert all(
        location.verification_status == "operator_confirmed"
        for location in navigation_locations
    )

    active_memberships = postgres_session.scalars(
        active_membership_statement(as_of=SCENARIO_NOW)
    ).all()
    assert {membership.id for membership in active_memberships} == {
        scenario.driver_membership.id,
        scenario.recipient_a_membership.id,
    }
    assert scenario.driver_membership.membership_role == "driver"
    assert scenario.recipient_a_membership.membership_role == "recipient_responder"
    assert scenario.recipient_a_membership.site_id == scenario.recipient_a_site.id


def test_phase10a_capacity_query_keeps_known_and_unknown_distinct(
    postgres_session: Session,
) -> None:
    scenario = build_listed_scenario(postgres_session)
    postgres_session.commit()

    current_capacity = postgres_session.scalars(
        current_recipient_availability_statement(as_of=SCENARIO_NOW)
    ).all()
    by_site = {snapshot.site_id: snapshot for snapshot in current_capacity}

    assert by_site[scenario.recipient_a_site.id].capacity_status == "known"
    assert by_site[scenario.recipient_a_site.id].available_quantity == Decimal("30.000")
    assert by_site[scenario.recipient_b_site.id].capacity_status == "unknown"
    assert by_site[scenario.recipient_b_site.id].available_quantity is None


def test_phase10a_product_master_changes_do_not_change_item_snapshot(
    postgres_session: Session,
) -> None:
    scenario = build_listed_scenario(postgres_session)
    postgres_session.commit()

    scenario.product.product_name = "Changed synthetic product master name"
    postgres_session.commit()

    stored_item = postgres_session.scalars(
        select(DonationItem).where(DonationItem.id == scenario.barcode_item.id)
    ).one()
    assert stored_item.product_name_snapshot == "Synthetic Chilled Yoghurt"


def test_phase10a_listing_observation_is_linked_to_the_barcode_item(
    postgres_session: Session,
) -> None:
    scenario = build_listed_scenario(postgres_session)
    postgres_session.commit()

    observations = postgres_session.scalars(
        select(FoodConditionObservation).where(
            FoodConditionObservation.donation_item_id == scenario.barcode_item.id
        )
    ).all()
    assert observations == [scenario.listing_condition]
    assert observations[0].observed_by_user_id == scenario.driver.id


def test_phase10a_scenario_times_are_timezone_aware_and_bounded(
    postgres_session: Session,
) -> None:
    scenario = build_listed_scenario(postgres_session)
    postgres_session.commit()

    assert scenario.donation.pickup_window_start == datetime(
        2026, 8, 10, 0, 45, tzinfo=UTC
    )
    assert scenario.donation.pickup_window_end == datetime(
        2026, 8, 10, 1, 30, tzinfo=UTC
    )
    assert scenario.donation.safe_deadline == datetime(2026, 8, 10, 3, 30, tzinfo=UTC)
    assert scenario.donation.safe_deadline > scenario.donation.pickup_window_end

    availability = postgres_session.get(
        RecipientAvailabilitySnapshot,
        scenario.recipient_a_capacity.id,
    )
    assert availability is not None
    assert availability.valid_from <= SCENARIO_NOW < availability.valid_until
