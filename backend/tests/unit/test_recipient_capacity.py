"""Recipient capacity (foodflow_clean_code_spec.md 10.1, group 3).

Requirement.md 16.3: "Community C is excluded because 10 kg capacity is
insufficient." Under the single-destination allocation policy
(docs/assumption_audit.md C-2) that statement is true; without that policy it is
false, because C could genuinely take 10 of the 25 kg. The two findings are
inseparable, which is why the exclusion wording is asserted here and not left to
the UI worker.
"""

from __future__ import annotations

import pytest

from backend.app.contracts.core import CandidateStatus
from backend.app.domain.clock import PinnedClock
from backend.app.domain.errors import ErrorCode
from backend.tests.support import domain_api, world


def test_the_seeded_capacities_make_the_scripted_exclusions_true() -> None:
    """SEEDED WORLD -> read remaining capacities -> A 60, C 10, D 30.

    The whole demo arithmetic rests on these three numbers: 60 covers the
    donation, 10 cannot cover the 25 kg remainder, 30 can.
    """
    assert world.community_a().remaining_capacity_kg == 60
    assert world.community_c().remaining_capacity_kg == 10
    assert world.community_d().remaining_capacity_kg == 30
    assert world.community_c().remaining_capacity_kg < world.REMAINING_KG
    assert world.community_d().remaining_capacity_kg >= world.REMAINING_KG


def test_community_c_assessed_for_the_full_60_kg_has_insufficient_capacity(
    demo_clock: PinnedClock,
) -> None:
    """60 KG DONATION + COMMUNITY C (10 KG) -> assess -> capacity_sufficient is False."""
    assessment = domain_api.assess_one(
        donation=world.donation(),
        community=world.community_c(),
        clock=demo_clock,
        quantity_kg=world.DONATION_TOTAL_KG,
    )
    assert assessment.capacity_sufficient is False


def test_community_c_assessed_for_the_remaining_25_kg_still_has_insufficient_capacity(
    demo_clock: PinnedClock,
) -> None:
    """25 KG REMAINDER + COMMUNITY C (10 KG) -> assess -> capacity_sufficient is False.

    The rematch beat. 10 < 25, so C is excluded on the rematch as well as on the
    first pass.
    """
    assessment = domain_api.assess_one(
        donation=world.donation(),
        community=world.community_c(),
        clock=demo_clock,
        quantity_kg=world.REMAINING_KG,
    )
    assert assessment.capacity_sufficient is False
    codes = [exclusion.code for exclusion in assessment.exclusions]
    assert ErrorCode.RECIPIENT_CAPACITY_EXCEEDED in codes, codes


def test_community_d_assessed_for_the_remaining_25_kg_has_sufficient_capacity(
    demo_clock: PinnedClock,
) -> None:
    """25 KG REMAINDER + COMMUNITY D (30 KG) -> assess -> capacity_sufficient is True."""
    assessment = domain_api.assess_one(
        donation=world.donation(),
        community=world.community_d(),
        clock=demo_clock,
        quantity_kg=world.REMAINING_KG,
    )
    assert assessment.capacity_sufficient is True
    assert assessment.status is not CandidateStatus.EXCLUDED


def test_capacity_exactly_equal_to_the_requested_quantity_is_sufficient(
    demo_clock: PinnedClock,
) -> None:
    """25 KG REMAINDER + AN ORG WITH EXACTLY 25 KG -> assess -> sufficient.

    The boundary. A `<` where `<=` belongs would exclude D on a 30/30 day and
    nobody would notice until the numbers changed.
    """
    exact_fit = world.community_d(remaining_capacity_kg=world.REMAINING_KG)
    assessment = domain_api.assess_one(
        donation=world.donation(),
        community=exact_fit,
        clock=demo_clock,
        quantity_kg=world.REMAINING_KG,
    )
    assert assessment.capacity_sufficient is True


def test_community_c_exclusion_text_says_insufficient_for_a_single_destination_allocation(
    demo_clock: PinnedClock,
) -> None:
    """COMMUNITY C EXCLUDED -> read the display text -> it names the single-destination policy.

    docs/assumption_audit.md C-2 and implementation_phases P1. A bare
    "insufficient capacity" is subtly untrue — C could take 10 of the 25 — and a
    judge can challenge it on stage. The wording is a product decision recorded
    in the plan, so it is asserted, not left to taste.
    """
    assessment = domain_api.assess_one(
        donation=world.donation(),
        community=world.community_c(),
        clock=demo_clock,
        quantity_kg=world.REMAINING_KG,
    )
    texts = " ".join(exclusion.display_text.lower() for exclusion in assessment.exclusions)
    assert "single-destination" in texts or "single destination" in texts, texts


@pytest.mark.parametrize(
    ("capacity_kg", "requested_kg", "expected"),
    [
        (0, 25, False),
        (24, 25, False),
        (25, 25, True),
        (26, 25, True),
        (60, 60, True),
        (59, 60, False),
    ],
)
def test_capacity_sufficiency_is_decided_at_the_documented_boundary(
    capacity_kg: int, requested_kg: int, expected: bool, demo_clock: PinnedClock
) -> None:
    """ORG WITH capacity_kg -> assess -> sufficiency matches capacity >= requested_kg."""
    community = world.community_d(remaining_capacity_kg=capacity_kg)
    assessment = domain_api.assess_one(
        donation=world.donation(),
        community=community,
        clock=demo_clock,
        quantity_kg=requested_kg,
    )
    assert assessment.capacity_sufficient is expected
