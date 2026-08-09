"""Deterministic listed-stage fixture for the KiwiHarvest food-diversion flow."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid5

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
    ImportBatch,
    MatchCandidate,
    MatchDecision,
    MatchRun,
    Organisation,
    OrganisationMembership,
    OrganisationRole,
    RecipientAvailabilitySnapshot,
    RecipientCapability,
    RecipientNeed,
    RouteDecision,
    RouteInputSnapshot,
    RoutePlanningRun,
    RouteProposal,
    Site,
    SiteLocation,
    SourceRecord,
    User,
)

SCENARIO_NOW = datetime(2026, 8, 10, tzinfo=UTC)
SYNTHETIC_GTIN14 = "00012345600012"
FIXTURE_NAMESPACE = UUID("5bbf5d95-79ce-49b2-a0f3-d9dc4b2fdb71")


def _fixture_id(scenario_key: str, entity_key: str) -> UUID:
    return uuid5(FIXTURE_NAMESPACE, f"{scenario_key}:{entity_key}")


@dataclass(frozen=True)
class ListedFoodDiversionScenario:
    """References to every row created by the listed-stage fixture."""

    scenario_key: str
    now: datetime
    woolworths: Organisation
    kiwiharvest: Organisation
    recipient_a: Organisation
    recipient_b: Organisation
    woolworths_store: Site
    kiwiharvest_hub: Site
    recipient_a_site: Site
    recipient_b_site: Site
    woolworths_location: SiteLocation
    kiwiharvest_location: SiteLocation
    recipient_a_location: SiteLocation
    recipient_b_location: SiteLocation
    driver: User
    recipient_a_responder: User
    driver_membership: OrganisationMembership
    recipient_a_membership: OrganisationMembership
    import_batch: ImportBatch
    product_source_record: SourceRecord
    donation_source_record: SourceRecord
    product: FoodProduct
    donation: Donation
    barcode_item: DonationItem
    no_barcode_item: DonationItem
    listing_condition: FoodConditionObservation
    recipient_a_capacity: RecipientAvailabilitySnapshot
    recipient_b_capacity: RecipientAvailabilitySnapshot


@dataclass(frozen=True)
class ConfirmedFoodDiversionScenario:
    """Listed scenario plus the confirmed allocation checkpoint."""

    listed: ListedFoodDiversionScenario
    match_run: MatchRun
    recipient_a_candidate: MatchCandidate
    recipient_b_candidate: MatchCandidate
    driver_confirmation: MatchDecision
    recipient_acceptance: MatchDecision
    allocation: Allocation


@dataclass(frozen=True)
class CompletedFoodDiversionScenario:
    """Confirmed scenario plus a successful selected-item delivery."""

    confirmed: ConfirmedFoodDiversionScenario
    route_run: RoutePlanningRun
    route_snapshots: tuple[RouteInputSnapshot, ...]
    route_proposal: RouteProposal
    route_decision: RouteDecision
    delivery: Delivery
    pickup_stop: DeliveryStop
    delivery_stop: DeliveryStop
    delivery_allocation: DeliveryAllocation
    pickup_condition: FoodConditionObservation
    delivery_condition: FoodConditionObservation


def _location(
    *,
    location_id: UUID,
    site_id: UUID,
    address_line1: str,
    latitude: str,
    longitude: str,
    location_type: str,
    now: datetime,
) -> SiteLocation:
    return SiteLocation(
        id=location_id,
        site_id=site_id,
        location_type=location_type,
        precision_level="exact",
        verification_status="operator_confirmed",
        visibility="operational",
        address_line1=address_line1,
        suburb="Synthetic Auckland",
        city="Auckland",
        region="Auckland",
        postal_code="0000",
        country_code="NZ",
        latitude=Decimal(latitude),
        longitude=Decimal(longitude),
        valid_from=now - timedelta(days=1),
        verified_at=now - timedelta(days=1),
    )


def build_listed_scenario(
    session: Session,
    *,
    scenario_key: str = "success-path",
    now: datetime = SCENARIO_NOW,
) -> ListedFoodDiversionScenario:
    """Create the deterministic listed checkpoint used by later phase builders.

    This function deliberately stops before matching. It creates the two donation
    lines, but only later phases may create candidates, allocations, or deliveries.
    """

    woolworths = Organisation(
        id=_fixture_id(scenario_key, "organisation:woolworths"),
        name="Woolworths NZ — SYNTHETIC TEST DONOR",
    )
    kiwiharvest = Organisation(
        id=_fixture_id(scenario_key, "organisation:kiwiharvest"),
        name="KiwiHarvest — SYNTHETIC TEST OPERATOR",
    )
    recipient_a = Organisation(
        id=_fixture_id(scenario_key, "organisation:recipient-a"),
        name="Recipient A — KNOWN CAPACITY",
    )
    recipient_b = Organisation(
        id=_fixture_id(scenario_key, "organisation:recipient-b"),
        name="Recipient B — UNKNOWN CAPACITY",
    )
    organisations = [woolworths, kiwiharvest, recipient_a, recipient_b]

    organisation_roles = [
        OrganisationRole(
            id=_fixture_id(scenario_key, "role:woolworths-donor"),
            organisation_id=woolworths.id,
            role_type="donor",
            valid_from=now - timedelta(days=30),
        ),
        OrganisationRole(
            id=_fixture_id(scenario_key, "role:kiwiharvest-operator"),
            organisation_id=kiwiharvest.id,
            role_type="food_rescue_operator",
            valid_from=now - timedelta(days=30),
        ),
        OrganisationRole(
            id=_fixture_id(scenario_key, "role:recipient-a"),
            organisation_id=recipient_a.id,
            role_type="recipient",
            valid_from=now - timedelta(days=30),
        ),
        OrganisationRole(
            id=_fixture_id(scenario_key, "role:recipient-b"),
            organisation_id=recipient_b.id,
            role_type="recipient",
            valid_from=now - timedelta(days=30),
        ),
    ]

    woolworths_store = Site(
        id=_fixture_id(scenario_key, "site:woolworths-store"),
        organisation_id=woolworths.id,
        name="Woolworths synthetic store",
        site_type="store",
    )
    kiwiharvest_hub = Site(
        id=_fixture_id(scenario_key, "site:kiwiharvest-hub"),
        organisation_id=kiwiharvest.id,
        name="KiwiHarvest synthetic hub",
        site_type="warehouse",
    )
    recipient_a_site = Site(
        id=_fixture_id(scenario_key, "site:recipient-a"),
        organisation_id=recipient_a.id,
        name="Recipient A synthetic service site",
        site_type="service_site",
    )
    recipient_b_site = Site(
        id=_fixture_id(scenario_key, "site:recipient-b"),
        organisation_id=recipient_b.id,
        name="Recipient B synthetic service site",
        site_type="service_site",
    )
    sites = [woolworths_store, kiwiharvest_hub, recipient_a_site, recipient_b_site]

    session.add_all([*organisations, *organisation_roles, *sites])
    session.flush()

    woolworths_location = _location(
        location_id=_fixture_id(scenario_key, "location:woolworths-pickup"),
        site_id=woolworths_store.id,
        address_line1="SYNTHETIC TEST ONLY — Woolworths pickup point",
        latitude="-36.900000",
        longitude="174.800000",
        location_type="pickup_point",
        now=now,
    )
    kiwiharvest_location = _location(
        location_id=_fixture_id(scenario_key, "location:kiwiharvest-origin"),
        site_id=kiwiharvest_hub.id,
        address_line1="SYNTHETIC TEST ONLY — KiwiHarvest origin",
        latitude="-36.940000",
        longitude="174.860000",
        location_type="pickup_point",
        now=now,
    )
    recipient_a_location = _location(
        location_id=_fixture_id(scenario_key, "location:recipient-a-receiving"),
        site_id=recipient_a_site.id,
        address_line1="SYNTHETIC TEST ONLY — Recipient A receiving point",
        latitude="-36.880000",
        longitude="174.825000",
        location_type="receiving_point",
        now=now,
    )
    recipient_b_location = _location(
        location_id=_fixture_id(scenario_key, "location:recipient-b-receiving"),
        site_id=recipient_b_site.id,
        address_line1="SYNTHETIC TEST ONLY — Recipient B receiving point",
        latitude="-36.845000",
        longitude="174.760000",
        location_type="receiving_point",
        now=now,
    )
    locations = [
        woolworths_location,
        kiwiharvest_location,
        recipient_a_location,
        recipient_b_location,
    ]
    session.add_all(locations)
    session.flush()

    driver = User(
        id=_fixture_id(scenario_key, "user:driver"),
        display_name="Synthetic Driver",
        email="driver.synthetic@example.invalid",
        status="active",
    )
    recipient_a_responder = User(
        id=_fixture_id(scenario_key, "user:recipient-a-responder"),
        display_name="Synthetic Recipient A Responder",
        email="recipient-a.synthetic@example.invalid",
        status="active",
    )
    session.add_all([driver, recipient_a_responder])
    session.flush()

    driver_membership = OrganisationMembership(
        id=_fixture_id(scenario_key, "membership:driver"),
        user_id=driver.id,
        organisation_id=kiwiharvest.id,
        scope_type="organisation",
        membership_role="driver",
        valid_from=now - timedelta(days=30),
    )
    recipient_a_membership = OrganisationMembership(
        id=_fixture_id(scenario_key, "membership:recipient-a-responder"),
        user_id=recipient_a_responder.id,
        organisation_id=recipient_a.id,
        site_id=recipient_a_site.id,
        scope_type="site",
        membership_role="recipient_responder",
        valid_from=now - timedelta(days=30),
    )
    session.add_all([driver_membership, recipient_a_membership])
    session.flush()

    import_batch = ImportBatch(
        id=_fixture_id(scenario_key, "import:batch"),
        source_system="synthetic_fixture",
        source_format="structured_form",
        idempotency_key=f"{scenario_key}-v1",
        external_batch_id=f"{scenario_key}-batch",
        status="completed",
        received_at=now - timedelta(minutes=20),
        completed_at=now - timedelta(minutes=19),
    )
    session.add(import_batch)
    session.flush()

    product_source_record = SourceRecord(
        id=_fixture_id(scenario_key, "source:product"),
        import_batch_id=import_batch.id,
        source_system="synthetic_fixture",
        source_record_type="product",
        external_record_id=f"{scenario_key}-product-001",
        observed_at=now - timedelta(minutes=20),
        raw_reference="synthetic://product/yoghurt-001",
        raw_payload={"gtin": SYNTHETIC_GTIN14, "synthetic": True},
        ingest_status="accepted",
    )
    donation_source_record = SourceRecord(
        id=_fixture_id(scenario_key, "source:donation"),
        import_batch_id=import_batch.id,
        source_system="synthetic_fixture",
        source_record_type="donation_listing",
        external_record_id=f"{scenario_key}-donation-001",
        observed_at=now - timedelta(minutes=10),
        raw_reference="synthetic://donation/listing-001",
        raw_payload={"line_count": 2, "synthetic": True},
        ingest_status="accepted",
    )
    session.add_all([product_source_record, donation_source_record])
    session.flush()

    product = FoodProduct(
        id=_fixture_id(scenario_key, "food-product:yoghurt"),
        gtin=SYNTHETIC_GTIN14,
        product_name="Synthetic Chilled Yoghurt",
        brand="Synthetic Brand",
        variant="Plain",
        source_record_id=product_source_record.id,
    )
    session.add(product)
    session.flush()

    donation = Donation(
        id=_fixture_id(scenario_key, "donation:001"),
        source_site_id=woolworths_store.id,
        created_by_user_id=driver.id,
        source_record_id=donation_source_record.id,
        pickup_window_start=now + timedelta(minutes=45),
        pickup_window_end=now + timedelta(minutes=90),
        safe_deadline=now + timedelta(hours=3, minutes=30),
        status="listed",
        created_at=now - timedelta(minutes=10),
        updated_at=now - timedelta(minutes=10),
    )
    barcode_item = DonationItem(
        id=_fixture_id(scenario_key, "donation-item:barcode-chilled"),
        line_number=1,
        food_product_id=product.id,
        product_name_snapshot="Synthetic Chilled Yoghurt",
        brand_snapshot="Synthetic Brand",
        variant_snapshot="Plain",
        gtin_snapshot=SYNTHETIC_GTIN14,
        lot_code="SYNTHETIC-LOT-001",
        quantity=Decimal("10.000"),
        quantity_unit="kg",
        storage_class="chilled",
        date_mark_type="use_by",
        date_mark=(now + timedelta(days=2)).date(),
        packaging_condition="sealed",
        recall_status="not_recalled",
        created_at=now - timedelta(minutes=10),
    )
    no_barcode_item = DonationItem(
        id=_fixture_id(scenario_key, "donation-item:no-barcode-ambient"),
        line_number=2,
        food_product_id=None,
        product_name_snapshot="Synthetic Loose Apples",
        brand_snapshot=None,
        variant_snapshot=None,
        gtin_snapshot=None,
        lot_code=None,
        quantity=Decimal("8.000"),
        quantity_unit="kg",
        storage_class="ambient",
        date_mark_type="none",
        date_mark=None,
        packaging_condition="opened",
        recall_status="not_checked",
        created_at=now - timedelta(minutes=10),
    )
    donation.items.extend([barcode_item, no_barcode_item])
    session.add(donation)
    session.flush()

    listing_condition = FoodConditionObservation(
        id=_fixture_id(scenario_key, "condition:listing"),
        donation_item_id=barcode_item.id,
        observed_by_user_id=driver.id,
        checkpoint="listing",
        condition_status="acceptable",
        temperature_celsius=Decimal("4.00"),
        notes="Synthetic listing observation; not a live food-safety assessment.",
        observed_at=now - timedelta(minutes=8),
    )
    session.add(listing_condition)
    session.add_all(
        [
            DonationStatusEvent(
                id=_fixture_id(scenario_key, "donation-event:created"),
                donation_id=donation.id,
                event_type="created",
                actor_type="user",
                actor_user_id=driver.id,
                occurred_at=now - timedelta(minutes=10),
            ),
            DonationStatusEvent(
                id=_fixture_id(scenario_key, "donation-event:listed"),
                donation_id=donation.id,
                event_type="listed",
                actor_type="user",
                actor_user_id=driver.id,
                occurred_at=now - timedelta(minutes=9),
            ),
        ]
    )

    recipient_a_capability = RecipientCapability(
        id=_fixture_id(scenario_key, "capability:recipient-a"),
        site_id=recipient_a_site.id,
        food_category="dairy",
        storage_class="chilled",
        valid_from=now - timedelta(days=1),
        valid_until=now + timedelta(days=1),
        updated_by_user_id=driver.id,
        notes="Synthetic capability record.",
    )
    recipient_b_capability = RecipientCapability(
        id=_fixture_id(scenario_key, "capability:recipient-b"),
        site_id=recipient_b_site.id,
        food_category="dairy",
        storage_class="chilled",
        valid_from=now - timedelta(days=1),
        valid_until=now + timedelta(days=1),
        updated_by_user_id=driver.id,
        notes="Synthetic capability record.",
    )
    session.add_all([recipient_a_capability, recipient_b_capability])
    session.flush()

    session.add(
        RecipientNeed(
            id=_fixture_id(scenario_key, "need:recipient-a"),
            site_id=recipient_a_site.id,
            food_category="dairy",
            storage_class="chilled",
            quantity=Decimal("20.000"),
            quantity_unit="kg",
            priority=5,
            receiving_window_start=now + timedelta(hours=1),
            receiving_window_end=now + timedelta(hours=3),
            valid_from=now - timedelta(hours=1),
            valid_until=now + timedelta(days=1),
            updated_by_user_id=driver.id,
        )
    )
    observed_at = now - timedelta(minutes=5)
    recipient_a_capacity = RecipientAvailabilitySnapshot(
        id=_fixture_id(scenario_key, "capacity:recipient-a"),
        site_id=recipient_a_site.id,
        food_category="dairy",
        storage_class="chilled",
        capacity_status="known",
        available_quantity=Decimal("30.000"),
        quantity_unit="kg",
        receiving_window_start=now + timedelta(hours=1),
        receiving_window_end=now + timedelta(hours=3),
        observed_at=observed_at,
        recorded_at=observed_at,
        valid_from=observed_at,
        valid_until=now + timedelta(hours=2),
        updated_by_user_id=driver.id,
    )
    recipient_b_capacity = RecipientAvailabilitySnapshot(
        id=_fixture_id(scenario_key, "capacity:recipient-b"),
        site_id=recipient_b_site.id,
        food_category="dairy",
        storage_class="chilled",
        capacity_status="unknown",
        available_quantity=None,
        quantity_unit="kg",
        receiving_window_start=now + timedelta(hours=1),
        receiving_window_end=now + timedelta(hours=3),
        observed_at=observed_at,
        recorded_at=observed_at,
        valid_from=observed_at,
        valid_until=now + timedelta(hours=2),
        updated_by_user_id=driver.id,
    )
    session.add_all([recipient_a_capacity, recipient_b_capacity])
    session.flush()

    return ListedFoodDiversionScenario(
        scenario_key=scenario_key,
        now=now,
        woolworths=woolworths,
        kiwiharvest=kiwiharvest,
        recipient_a=recipient_a,
        recipient_b=recipient_b,
        woolworths_store=woolworths_store,
        kiwiharvest_hub=kiwiharvest_hub,
        recipient_a_site=recipient_a_site,
        recipient_b_site=recipient_b_site,
        woolworths_location=woolworths_location,
        kiwiharvest_location=kiwiharvest_location,
        recipient_a_location=recipient_a_location,
        recipient_b_location=recipient_b_location,
        driver=driver,
        recipient_a_responder=recipient_a_responder,
        driver_membership=driver_membership,
        recipient_a_membership=recipient_a_membership,
        import_batch=import_batch,
        product_source_record=product_source_record,
        donation_source_record=donation_source_record,
        product=product,
        donation=donation,
        barcode_item=barcode_item,
        no_barcode_item=no_barcode_item,
        listing_condition=listing_condition,
        recipient_a_capacity=recipient_a_capacity,
        recipient_b_capacity=recipient_b_capacity,
    )


def confirm_barcode_item_allocation(
    session: Session,
    listed: ListedFoodDiversionScenario,
) -> ConfirmedFoodDiversionScenario:
    """Create the matching and human-confirmed allocation checkpoint."""

    now = listed.now
    scenario_key = listed.scenario_key
    match_run = MatchRun(
        id=_fixture_id(scenario_key, "match-run:barcode-item"),
        donation_item_id=listed.barcode_item.id,
        requested_by_user_id=listed.driver.id,
        policy_version="synthetic-match-v1",
        model_identifier="synthetic-matching-agent",
        status="completed",
        started_at=now + timedelta(minutes=1),
        completed_at=now + timedelta(minutes=2),
    )
    recipient_a_candidate = MatchCandidate(
        id=_fixture_id(scenario_key, "candidate:recipient-a"),
        match_run_id=match_run.id,
        recipient_site_id=listed.recipient_a_site.id,
        feasibility_status="feasible",
        reason_code="known_capacity_and_need",
        reason_components={
            "classified_food_category": "dairy",
            "capacity_status": "known",
            "available_quantity": "30.000",
            "required_quantity": "10.000",
            "quantity_unit": "kg",
            "need_priority": 5,
            "safe_deadline_feasible": True,
        },
        agent_rank=1,
        priority_score=Decimal("0.920000"),
        evaluated_at=now + timedelta(minutes=2),
    )
    recipient_b_candidate = MatchCandidate(
        id=_fixture_id(scenario_key, "candidate:recipient-b"),
        match_run_id=match_run.id,
        recipient_site_id=listed.recipient_b_site.id,
        feasibility_status="manual_review",
        reason_code="unknown_capacity",
        reason_components={
            "classified_food_category": "dairy",
            "capacity_status": "unknown",
            "available_quantity": None,
            "required_quantity": "10.000",
            "quantity_unit": "kg",
        },
        agent_rank=None,
        priority_score=None,
        evaluated_at=now + timedelta(minutes=2),
    )
    session.add_all([match_run, recipient_a_candidate, recipient_b_candidate])
    session.flush()

    driver_confirmation = MatchDecision(
        id=_fixture_id(scenario_key, "match-decision:driver-confirmation"),
        match_candidate_id=recipient_a_candidate.id,
        decision_type="driver_confirmation",
        decision="confirmed",
        actor_user_id=listed.driver.id,
        decided_at=now + timedelta(minutes=3),
        comment="Synthetic driver confirmation.",
    )
    recipient_acceptance = MatchDecision(
        id=_fixture_id(scenario_key, "match-decision:recipient-acceptance"),
        match_candidate_id=recipient_a_candidate.id,
        decision_type="recipient_acceptance",
        decision="accepted",
        actor_user_id=listed.recipient_a_responder.id,
        decided_at=now + timedelta(minutes=4),
        comment="Synthetic recipient acceptance.",
    )
    session.add_all([driver_confirmation, recipient_acceptance])
    session.flush()

    allocation = Allocation(
        id=_fixture_id(scenario_key, "allocation:barcode-item"),
        donation_item_id=listed.barcode_item.id,
        recipient_site_id=listed.recipient_a_site.id,
        match_candidate_id=recipient_a_candidate.id,
        allocated_quantity=Decimal("10.000"),
        quantity_unit="kg",
        status="reserved",
        reserved_by_user_id=listed.driver.id,
        reserved_at=now + timedelta(minutes=5),
    )
    session.add(allocation)
    session.flush()
    session.add(
        AllocationStatusEvent(
            id=_fixture_id(scenario_key, "allocation-event:reserved"),
            allocation_id=allocation.id,
            event_type="reserved",
            actor_type="user",
            actor_user_id=listed.driver.id,
            occurred_at=now + timedelta(minutes=5),
            recorded_at=now + timedelta(minutes=5),
        )
    )
    session.flush()

    allocation.status = "confirmed"
    allocation.confirmed_by_user_id = listed.recipient_a_responder.id
    allocation.confirmed_at = now + timedelta(minutes=6)
    session.add(
        AllocationStatusEvent(
            id=_fixture_id(scenario_key, "allocation-event:confirmed"),
            allocation_id=allocation.id,
            event_type="confirmed",
            actor_type="user",
            actor_user_id=listed.recipient_a_responder.id,
            occurred_at=now + timedelta(minutes=6),
            recorded_at=now + timedelta(minutes=6),
        )
    )
    session.flush()

    return ConfirmedFoodDiversionScenario(
        listed=listed,
        match_run=match_run,
        recipient_a_candidate=recipient_a_candidate,
        recipient_b_candidate=recipient_b_candidate,
        driver_confirmation=driver_confirmation,
        recipient_acceptance=recipient_acceptance,
        allocation=allocation,
    )


def complete_successful_delivery(
    session: Session,
    confirmed: ConfirmedFoodDiversionScenario,
) -> CompletedFoodDiversionScenario:
    """Complete the selected barcode item without closing the whole donation."""

    if confirmed.allocation.status != "confirmed":
        raise ValueError("successful delivery requires a confirmed allocation")

    listed = confirmed.listed
    now = listed.now
    scenario_key = listed.scenario_key
    planned_departure = now + timedelta(minutes=20)
    snapshot_valid_from = now - timedelta(minutes=5)
    snapshot_valid_until = now + timedelta(hours=2)

    route_run = RoutePlanningRun(
        id=_fixture_id(scenario_key, "route-run:success"),
        driver_user_id=listed.driver.id,
        planning_horizon_start=now,
        planning_horizon_end=now + timedelta(hours=4),
        planned_departure_at=planned_departure,
        policy_version="synthetic-route-v1",
        model_identifier="synthetic-routing-agent",
        status="started",
        created_at=now + timedelta(minutes=7),
    )
    session.add(route_run)
    session.flush()

    route_snapshots = [
        RouteInputSnapshot(
            id=_fixture_id(scenario_key, "route-input:traffic"),
            route_planning_run_id=route_run.id,
            input_kind="traffic",
            provider="synthetic_fixture",
            coverage_reference="synthetic-kiwiharvest-to-woolworths-to-recipient-a",
            observed_at=now + timedelta(minutes=10),
            recorded_at=now + timedelta(minutes=10),
            valid_from=snapshot_valid_from,
            valid_until=snapshot_valid_until,
            payload={
                "congestion": "moderate",
                "delay_seconds": 420,
                "legs": ["origin_to_pickup"],
            },
        ),
        RouteInputSnapshot(
            id=_fixture_id(scenario_key, "route-input:weather"),
            route_planning_run_id=route_run.id,
            input_kind="weather",
            provider="synthetic_fixture",
            coverage_reference="synthetic-auckland-route",
            observed_at=now + timedelta(minutes=10),
            recorded_at=now + timedelta(minutes=10),
            valid_from=snapshot_valid_from,
            valid_until=snapshot_valid_until,
            payload={
                "condition": "heavy_rain",
                "risk": "moderate",
                "delay_seconds": 120,
            },
        ),
        RouteInputSnapshot(
            id=_fixture_id(scenario_key, "route-input:road"),
            route_planning_run_id=route_run.id,
            input_kind="road",
            provider="synthetic_fixture",
            coverage_reference="synthetic-auckland-route",
            observed_at=now + timedelta(minutes=10),
            recorded_at=now + timedelta(minutes=10),
            valid_from=snapshot_valid_from,
            valid_until=snapshot_valid_until,
            payload={"closures": [], "surface": "wet", "passable": True},
        ),
        RouteInputSnapshot(
            id=_fixture_id(scenario_key, "route-input:eta"),
            route_planning_run_id=route_run.id,
            input_kind="eta",
            provider="synthetic_fixture",
            coverage_reference="synthetic-route-legs",
            observed_at=now + timedelta(minutes=10),
            recorded_at=now + timedelta(minutes=10),
            valid_from=snapshot_valid_from,
            valid_until=snapshot_valid_until,
            payload={
                "legs": [
                    {"from": "kiwiharvest_origin", "to": "woolworths_pickup", "seconds": 1800},
                    {"from": "woolworths_pickup", "to": "recipient_a", "seconds": 2100},
                ],
                "total_seconds": 3900,
            },
        ),
        RouteInputSnapshot(
            id=_fixture_id(scenario_key, "route-input:allocation"),
            route_planning_run_id=route_run.id,
            input_kind="allocation",
            provider="synthetic_fixture",
            coverage_reference=str(confirmed.allocation.id),
            observed_at=now + timedelta(minutes=10),
            recorded_at=now + timedelta(minutes=10),
            valid_from=snapshot_valid_from,
            valid_until=snapshot_valid_until,
            payload={"allocation_id": str(confirmed.allocation.id), "status": "confirmed"},
        ),
        RouteInputSnapshot(
            id=_fixture_id(scenario_key, "route-input:condition"),
            route_planning_run_id=route_run.id,
            input_kind="condition",
            provider="synthetic_fixture",
            coverage_reference=str(listed.barcode_item.id),
            observed_at=now + timedelta(minutes=10),
            recorded_at=now + timedelta(minutes=10),
            valid_from=snapshot_valid_from,
            valid_until=snapshot_valid_until,
            payload={
                "donation_item_id": str(listed.barcode_item.id),
                "temperature_celsius": "4.00",
            },
        ),
        RouteInputSnapshot(
            id=_fixture_id(scenario_key, "route-input:capacity"),
            route_planning_run_id=route_run.id,
            input_kind="capacity",
            provider="synthetic_fixture",
            coverage_reference=str(listed.recipient_a_site.id),
            observed_at=now + timedelta(minutes=10),
            recorded_at=now + timedelta(minutes=10),
            valid_from=snapshot_valid_from,
            valid_until=snapshot_valid_until,
            payload={
                "availability_id": str(listed.recipient_a_capacity.id),
                "capacity_status": "known",
                "available_quantity": "30.000",
                "quantity_unit": "kg",
            },
        ),
        RouteInputSnapshot(
            id=_fixture_id(scenario_key, "route-input:location"),
            route_planning_run_id=route_run.id,
            input_kind="location",
            provider="synthetic_fixture",
            coverage_reference="kiwiharvest,woolworths,recipient-a",
            observed_at=now + timedelta(minutes=10),
            recorded_at=now + timedelta(minutes=10),
            valid_from=snapshot_valid_from,
            valid_until=snapshot_valid_until,
            payload={
                "origin_location_id": str(listed.kiwiharvest_location.id),
                "pickup_location_id": str(listed.woolworths_location.id),
                "delivery_location_id": str(listed.recipient_a_location.id),
            },
        ),
    ]
    session.add_all(route_snapshots)
    session.flush()
    route_run.status = "proposal_ready"

    route_proposal = RouteProposal(
        id=_fixture_id(scenario_key, "route-proposal:success-v1"),
        route_planning_run_id=route_run.id,
        version=1,
        proposal_status="selected",
        proposal_payload={
            "origin": str(listed.kiwiharvest_location.id),
            "stops": [
                {"type": "pickup", "location_id": str(listed.woolworths_location.id)},
                {"type": "delivery", "location_id": str(listed.recipient_a_location.id)},
            ],
        },
        priority_reasons={
            "feasibility": "pass",
            "safe_deadline": "pass",
            "condition": "acceptable_chilled",
            "recipient_need_priority": 5,
            "known_capacity": True,
            "traffic_weather_road": "included",
            "distance": "tie_breaker_only",
        },
        cost_components={
            "traffic_delay_seconds": 420,
            "weather_delay_seconds": 120,
            "travel_seconds": 3900,
        },
        total_travel_seconds=Decimal("3900.00"),
        total_distance_meters=Decimal("18000.00"),
        created_at=now + timedelta(minutes=11),
    )
    session.add(route_proposal)
    session.flush()

    route_decision = RouteDecision(
        id=_fixture_id(scenario_key, "route-decision:driver-approved"),
        route_proposal_id=route_proposal.id,
        decision_type="driver_confirmation",
        decision="approved",
        actor_user_id=listed.driver.id,
        decided_at=now + timedelta(minutes=12),
        comment="Synthetic driver route approval.",
    )
    session.add(route_decision)
    session.flush()
    route_run.status = "approved"

    delivery = Delivery(
        id=_fixture_id(scenario_key, "delivery:success"),
        route_decision_id=route_decision.id,
        driver_user_id=listed.driver.id,
        planned_departure_at=planned_departure,
        committed_at=now + timedelta(minutes=13),
        status="assigned",
    )
    pickup_arrival = now + timedelta(minutes=50)
    pickup_departure = now + timedelta(minutes=58)
    delivery_arrival = now + timedelta(minutes=95)
    delivery_departure = now + timedelta(minutes=103)
    pickup_stop = DeliveryStop(
        id=_fixture_id(scenario_key, "delivery-stop:pickup"),
        delivery_id=delivery.id,
        stop_sequence=1,
        actual_sequence=1,
        stop_type="pickup",
        site_id=listed.woolworths_store.id,
        site_location_id=listed.woolworths_location.id,
        window_start=listed.donation.pickup_window_start,
        window_end=listed.donation.pickup_window_end,
        planned_arrival_at=pickup_arrival,
        planned_departure_at=pickup_departure,
        actual_arrival_at=pickup_arrival,
        actual_departure_at=pickup_departure,
        status="completed",
        result_note="Synthetic pickup completed.",
    )
    delivery_stop = DeliveryStop(
        id=_fixture_id(scenario_key, "delivery-stop:recipient-a"),
        delivery_id=delivery.id,
        stop_sequence=2,
        actual_sequence=2,
        stop_type="delivery",
        site_id=listed.recipient_a_site.id,
        site_location_id=listed.recipient_a_location.id,
        window_start=now + timedelta(hours=1),
        window_end=now + timedelta(hours=3),
        planned_arrival_at=delivery_arrival,
        planned_departure_at=delivery_departure,
        actual_arrival_at=delivery_arrival,
        actual_departure_at=delivery_departure,
        status="completed",
        result_note="Synthetic recipient handoff completed.",
    )
    delivery.stops.extend([pickup_stop, delivery_stop])
    session.add(delivery)
    session.flush()

    delivery_allocation = DeliveryAllocation(
        id=_fixture_id(scenario_key, "delivery-allocation:barcode-item"),
        delivery_id=delivery.id,
        allocation_id=confirmed.allocation.id,
        pickup_stop_id=pickup_stop.id,
        delivery_stop_id=delivery_stop.id,
    )
    session.add(delivery_allocation)
    session.add(
        DeliveryStatusEvent(
            id=_fixture_id(scenario_key, "delivery-event:assigned"),
            delivery_id=delivery.id,
            stop_id=None,
            event_type="assigned",
            actor_type="user",
            actor_user_id=listed.driver.id,
            occurred_at=now + timedelta(minutes=13),
            recorded_at=now + timedelta(minutes=13),
        )
    )
    session.flush()

    delivery.status = "started"
    delivery.started_at = planned_departure
    session.add(
        DeliveryStatusEvent(
            id=_fixture_id(scenario_key, "delivery-event:started"),
            delivery_id=delivery.id,
            stop_id=None,
            event_type="started",
            actor_type="user",
            actor_user_id=listed.driver.id,
            occurred_at=planned_departure,
            recorded_at=planned_departure,
        )
    )
    pickup_condition = FoodConditionObservation(
        id=_fixture_id(scenario_key, "condition:pickup"),
        donation_item_id=listed.barcode_item.id,
        observed_by_user_id=listed.driver.id,
        checkpoint="pickup",
        condition_status="acceptable",
        temperature_celsius=Decimal("4.30"),
        notes="Synthetic pickup condition observation.",
        observed_at=pickup_arrival,
    )
    delivery_condition = FoodConditionObservation(
        id=_fixture_id(scenario_key, "condition:delivery"),
        donation_item_id=listed.barcode_item.id,
        observed_by_user_id=listed.driver.id,
        checkpoint="delivery",
        condition_status="acceptable",
        temperature_celsius=Decimal("4.70"),
        notes="Synthetic delivery condition observation.",
        observed_at=delivery_arrival,
    )
    session.add_all([pickup_condition, delivery_condition])
    session.add_all(
        [
            DeliveryStatusEvent(
                id=_fixture_id(scenario_key, "delivery-event:pickup-arrived"),
                delivery_id=delivery.id,
                stop_id=pickup_stop.id,
                event_type="arrived",
                actor_type="user",
                actor_user_id=listed.driver.id,
                occurred_at=pickup_arrival,
                recorded_at=pickup_arrival,
            ),
            DeliveryStatusEvent(
                id=_fixture_id(scenario_key, "delivery-event:collected"),
                delivery_id=delivery.id,
                stop_id=pickup_stop.id,
                event_type="collected",
                actor_type="user",
                actor_user_id=listed.driver.id,
                occurred_at=pickup_departure,
                recorded_at=pickup_departure,
            ),
            DeliveryStatusEvent(
                id=_fixture_id(scenario_key, "delivery-event:delivery-arrived"),
                delivery_id=delivery.id,
                stop_id=delivery_stop.id,
                event_type="arrived",
                actor_type="user",
                actor_user_id=listed.driver.id,
                occurred_at=delivery_arrival,
                recorded_at=delivery_arrival,
            ),
            DeliveryStatusEvent(
                id=_fixture_id(scenario_key, "delivery-event:delivered"),
                delivery_id=delivery.id,
                stop_id=delivery_stop.id,
                event_type="delivered",
                actor_type="user",
                actor_user_id=listed.driver.id,
                occurred_at=delivery_arrival + timedelta(minutes=5),
                recorded_at=delivery_arrival + timedelta(minutes=5),
            ),
        ]
    )
    session.flush()

    delivery.status = "completed"
    delivery.completed_at = delivery_departure
    route_run.status = "committed"
    confirmed.allocation.status = "fulfilled"
    confirmed.allocation.fulfilled_at = delivery_departure
    session.add(
        AllocationStatusEvent(
            id=_fixture_id(scenario_key, "allocation-event:fulfilled"),
            allocation_id=confirmed.allocation.id,
            event_type="fulfilled",
            actor_type="user",
            actor_user_id=listed.driver.id,
            occurred_at=delivery_departure,
            recorded_at=delivery_departure,
        )
    )
    session.add(
        DeliveryStatusEvent(
            id=_fixture_id(scenario_key, "delivery-event:completed"),
            delivery_id=delivery.id,
            stop_id=None,
            event_type="completed",
            actor_type="user",
            actor_user_id=listed.driver.id,
            occurred_at=delivery_departure,
            recorded_at=delivery_departure,
        )
    )
    session.flush()

    return CompletedFoodDiversionScenario(
        confirmed=confirmed,
        route_run=route_run,
        route_snapshots=tuple(route_snapshots),
        route_proposal=route_proposal,
        route_decision=route_decision,
        delivery=delivery,
        pickup_stop=pickup_stop,
        delivery_stop=delivery_stop,
        delivery_allocation=delivery_allocation,
        pickup_condition=pickup_condition,
        delivery_condition=delivery_condition,
    )
