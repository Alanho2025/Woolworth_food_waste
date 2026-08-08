"""P1 eligibility and allocation edges through the real domain implementation.

No allocation, eligibility, clock, or route policy is mocked. The only inputs
are immutable contracts, a pinned clock, and the deterministic route adapter.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from backend.app.contracts.core import (
    CandidateAssessment,
    CandidateStatus,
    CommunityNeed,
    CommunityOrganisation,
    FoodCategory,
    Location,
    NeedLevel,
    StorageType,
    TimeWindow,
)
from backend.app.domain.clock import PinnedClock
from backend.app.domain.errors import ErrorCode
from backend.app.domain.policies.allocation import AllocationLeg, plan_allocation
from backend.app.domain.policies.eligibility import AssessmentRequest, assess_candidates
from backend.app.domain.routing import DeterministicRouteSimulator

AUCKLAND = ZoneInfo("Pacific/Auckland")
DEMO_NOW = datetime(2026, 8, 8, 15, 45, tzinfo=AUCKLAND)
DEADLINE = datetime(2026, 8, 8, 19, 0, tzinfo=AUCKLAND)
STORE = Location(name="Woolworths Mount Eden", latitude=-36.8770, longitude=174.7645)


def organisation(
    community_id: str,
    *,
    accepted_categories: list[FoodCategory] | None = None,
    supported_storage: list[StorageType] | None = None,
    declared_capacity_kg: int = 60,
    remaining_capacity_kg: int = 60,
    need: NeedLevel = NeedLevel.MEDIUM,
    window_start: datetime | None = None,
    window_end: datetime | None = None,
    is_open: bool = True,
) -> CommunityOrganisation:
    return CommunityOrganisation(
        community_id=community_id,
        name=f"Community {community_id}",
        location=Location(
            name=f"Community {community_id}",
            latitude=-36.89 - len(community_id) / 1000,
            longitude=174.75 + len(community_id) / 1000,
        ),
        accepted_categories=accepted_categories or [FoodCategory.VEGETABLES],
        supported_storage=supported_storage or [StorageType.AMBIENT],
        needs=[CommunityNeed(category=FoodCategory.VEGETABLES, level=need)],
        declared_capacity_kg=declared_capacity_kg,
        remaining_capacity_kg=remaining_capacity_kg,
        receiving_window=TimeWindow(
            start=window_start or datetime(2026, 8, 8, 8, 0, tzinfo=AUCKLAND),
            end=window_end or datetime(2026, 8, 8, 20, 0, tzinfo=AUCKLAND),
        ),
        is_open=is_open,
    )


def assess(
    communities: list[CommunityOrganisation],
    *,
    required_kg: int,
    clock: PinnedClock | None = None,
    origin: Location = STORE,
    storage_type: StorageType = StorageType.AMBIENT,
    declined_community_ids: tuple[str, ...] = (),
) -> list[CandidateAssessment]:
    selected_clock = clock or PinnedClock(DEMO_NOW)
    request = AssessmentRequest(
        origin=origin,
        category=FoodCategory.VEGETABLES,
        storage_type=storage_type,
        required_kg=required_kg,
        delivery_deadline=DEADLINE,
        now=selected_clock.now(),
        declined_community_ids=declined_community_ids,
    )
    return assess_candidates(
        request,
        communities,
        DeterministicRouteSimulator(selected_clock),
    )


def exclusion_codes(assessment: CandidateAssessment) -> set[ErrorCode]:
    return {reason.code for reason in assessment.exclusions}


def test_vegetable_donation_assessed_for_category_rejecting_b_reports_only_category_failure() -> (
    None
):
    """CATEGORY-REJECTING B -> real assessment -> category code without a false storage cause."""
    community_b = organisation(
        "B",
        accepted_categories=[FoodCategory.DAIRY],
        supported_storage=[StorageType.AMBIENT],
    )

    result = assess([community_b], required_kg=25)[0]

    assert result.category_compatible is False
    assert result.storage_compatible is True
    assert result.status is CandidateStatus.EXCLUDED
    assert exclusion_codes(result) == {ErrorCode.RECIPIENT_CATEGORY_UNSUPPORTED}


def test_ambient_donation_assessed_for_frozen_only_recipient_reports_only_storage_failure() -> None:
    """CATEGORY-VALID, STORAGE-INVALID ORG -> real assessment -> STORAGE_INCOMPATIBLE."""
    frozen_only = organisation("F", supported_storage=[StorageType.FROZEN])

    result = assess([frozen_only], required_kg=25)[0]

    assert result.category_compatible is True
    assert result.storage_compatible is False
    assert exclusion_codes(result) == {ErrorCode.STORAGE_INCOMPATIBLE}


def test_recipient_capacity_below_exact_and_above_boundary_is_assessed_correctly() -> None:
    """24/25/26 KG CAPACITY FOR 25 KG -> real assessment -> false/true/true."""
    communities = [
        organisation("LOW", declared_capacity_kg=24, remaining_capacity_kg=24),
        organisation("EXACT", declared_capacity_kg=25, remaining_capacity_kg=25),
        organisation("HIGH", declared_capacity_kg=26, remaining_capacity_kg=26),
    ]

    low, exact, high = assess(communities, required_kg=25)

    assert low.capacity_sufficient is False
    assert ErrorCode.RECIPIENT_CAPACITY_EXCEEDED in exclusion_codes(low)
    assert "single-destination" in " ".join(r.display_text for r in low.exclusions).lower()
    assert exact.capacity_sufficient is True
    assert high.capacity_sufficient is True


def test_hostile_0300_clock_closes_real_receiving_window_while_demo_clock_opens_it() -> None:
    """SAME ORG + HOSTILE/DEMO CLOCK -> real route/window comparison -> closed/open."""
    recipient = organisation(
        "WINDOW",
        window_start=datetime(2026, 8, 8, 8, 0, tzinfo=AUCKLAND),
        window_end=datetime(2026, 8, 8, 20, 0, tzinfo=AUCKLAND),
    )
    hostile = PinnedClock(datetime(2026, 8, 8, 3, 0, tzinfo=AUCKLAND))

    under_hostile = assess([recipient], required_kg=25, clock=hostile)[0]
    under_demo = assess([recipient], required_kg=25, clock=PinnedClock(DEMO_NOW))[0]

    assert under_hostile.window_open_on_arrival is False
    assert ErrorCode.RECEIVING_WINDOW_CLOSED in exclusion_codes(under_hostile)
    assert under_demo.window_open_on_arrival is True


def test_auckland_zone_resolves_dst_instead_of_using_a_literal_twelve_hour_offset() -> None:
    """SUMMER AUCKLAND INSTANT -> inspect zone -> NZDT +13:00."""
    summer = datetime(2026, 12, 25, 12, 0, tzinfo=AUCKLAND)
    assert str(summer.tzinfo) == "Pacific/Auckland"
    assert summer.utcoffset() is not None
    assert summer.utcoffset().total_seconds() == 13 * 3600


def test_category_excluded_candidate_still_has_a_real_simulated_route_and_eta() -> None:
    """CATEGORY-EXCLUDED B -> real fact pass -> route and ETA still populated."""
    community_b = organisation("B", accepted_categories=[FoodCategory.DAIRY])

    result = assess([community_b], required_kg=60)[0]

    assert result.status is CandidateStatus.EXCLUDED
    assert result.route.origin == STORE
    assert result.route.destination == community_b.location
    assert result.route.eta > DEMO_NOW
    assert result.route.simulated is True
    assert len(result.route.polyline) >= 2


def test_full_sixty_kilograms_uses_one_a_destination_instead_of_an_unrequested_split() -> None:
    """A AND D CAN HOLD 60 -> real allocation -> all 60 goes to higher-need A."""
    community_a = organisation("A", need=NeedLevel.URGENT)
    community_d = organisation("D", declared_capacity_kg=80, remaining_capacity_kg=80)
    assessments = assess([community_a, community_d], required_kg=60)

    plan = plan_allocation(assessments, required_kg=60)

    assert plan.is_complete is True
    assert plan.is_split is False
    assert plan.legs == (AllocationLeg(community_id="A", quantity_kg=60),)


def test_remaining_twenty_five_kilograms_goes_wholly_to_d_and_never_splits_to_c() -> None:
    """A DECLINED, C HAS 10, D HAS 30 -> real rematch policy -> one 25 kg D leg."""
    community_a = organisation(
        "A",
        declared_capacity_kg=35,
        remaining_capacity_kg=0,
        need=NeedLevel.URGENT,
    )
    community_c = organisation(
        "C",
        declared_capacity_kg=10,
        remaining_capacity_kg=10,
        need=NeedLevel.HIGH,
    )
    community_d = organisation(
        "D",
        declared_capacity_kg=30,
        remaining_capacity_kg=30,
        need=NeedLevel.MEDIUM,
    )
    assessments = assess(
        [community_a, community_c, community_d],
        required_kg=25,
        origin=community_a.location,
        declined_community_ids=(community_a.community_id,),
    )

    plan = plan_allocation(assessments, required_kg=25)

    assert ErrorCode.RECIPIENT_DECLINED_THIS_DONATION in exclusion_codes(assessments[0])
    assert ErrorCode.RECIPIENT_CAPACITY_EXCEEDED in exclusion_codes(assessments[1])
    assert assessments[2].route.origin == community_a.location
    assert plan.is_complete is True
    assert plan.is_split is False
    assert plan.legs == (AllocationLeg(community_id="D", quantity_kg=25),)
    assert all(leg.community_id != "A" for leg in plan.legs)
    assert all(leg.community_id != "C" for leg in plan.legs)


def test_no_single_fit_uses_real_capacity_only_split_without_using_other_invalid_recipients() -> (
    None
):
    """TWO CAPACITY-ONLY EXCLUSIONS COVER 60 -> real fallback -> exact split."""
    first = organisation("C", declared_capacity_kg=30, remaining_capacity_kg=30)
    second = organisation("D", declared_capacity_kg=30, remaining_capacity_kg=30)
    category_invalid = organisation(
        "B",
        accepted_categories=[FoodCategory.DAIRY],
        declared_capacity_kg=60,
        remaining_capacity_kg=60,
    )

    plan = plan_allocation(assess([first, second, category_invalid], required_kg=60), 60)

    assert plan.is_split is True
    assert plan.is_complete is True
    assert plan.covered_kg == 60
    assert {leg.community_id for leg in plan.legs} == {"C", "D"}


def test_insufficient_split_capacity_is_not_reported_as_a_feasible_allocation() -> None:
    """ONLY 30 KG TOTAL CAPACITY FOR 60 -> real fallback -> incomplete and infeasible."""
    first = organisation("C", declared_capacity_kg=10, remaining_capacity_kg=10)
    second = organisation("D", declared_capacity_kg=20, remaining_capacity_kg=20)

    plan = plan_allocation(assess([first, second], required_kg=60), 60)

    assert plan.covered_kg == 30
    assert plan.is_complete is False
    assert plan.is_feasible is False
