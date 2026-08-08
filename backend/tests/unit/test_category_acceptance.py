"""Category acceptance (foodflow_clean_code_spec.md 10.1, group 1).

Requirement.md 16.2: "Community B is excluded because vegetables are
unsupported." This is the first of the three distinct exclusion causes the demo
demonstrates, and the only one whose beat depends on a seeded organisation
refusing a category outright.
"""

from __future__ import annotations

from backend.app.contracts.core import CandidateStatus, FoodCategory
from backend.app.domain.clock import PinnedClock
from backend.app.domain.errors import ErrorCode
from backend.tests.support import domain_api, world


def test_community_b_does_not_list_vegetables_among_its_accepted_categories() -> None:
    """SEEDED WORLD -> read Community B's accepted categories -> vegetables absent.

    A contract-level guard on the demo world itself. If B ever starts accepting
    vegetables the exclusion beat silently disappears and every downstream
    assertion about "B excluded" becomes vacuously satisfiable.
    """
    community_b = world.community_b()
    assert FoodCategory.VEGETABLES not in community_b.accepted_categories
    assert community_b.needs, "Requirement.md 5 puts B's Need on screen; it must want something"
    assert all(need.category is not FoodCategory.VEGETABLES for need in community_b.needs), (
        "B's seeded need must not be the category B rejects (docs/assumption_audit.md C-5)"
    )


def test_community_b_assessed_against_a_vegetable_donation_is_marked_category_incompatible(
    demo_clock: PinnedClock,
) -> None:
    """VEGETABLE DONATION + COMMUNITY B -> assess -> category_compatible is False."""
    assessment = domain_api.assess_one(
        donation=world.donation(), community=world.community_b(), clock=demo_clock
    )
    assert assessment.category_compatible is False


def test_community_b_assessed_against_a_vegetable_donation_is_excluded_with_the_category_code(
    demo_clock: PinnedClock,
) -> None:
    """VEGETABLE DONATION + COMMUNITY B -> assess -> EXCLUDED, RECIPIENT_CATEGORY_UNSUPPORTED.

    The code, not the message. clean_code_spec 6.3: business outcomes are never
    determined by parsing exception strings.
    """
    assessment = domain_api.assess_one(
        donation=world.donation(), community=world.community_b(), clock=demo_clock
    )
    assert assessment.status is CandidateStatus.EXCLUDED
    codes = [exclusion.code for exclusion in assessment.exclusions]
    assert ErrorCode.RECIPIENT_CATEGORY_UNSUPPORTED in codes, codes


def test_community_b_exclusion_carries_display_text_for_its_card(
    demo_clock: PinnedClock,
) -> None:
    """COMMUNITY B EXCLUDED -> read the exclusion -> non-empty display text.

    Requirement.md 5 shows the reason verbatim on the card. An empty string
    renders as a blank cell on the most important pitch screen.
    """
    assessment = domain_api.assess_one(
        donation=world.donation(), community=world.community_b(), clock=demo_clock
    )
    for exclusion in assessment.exclusions:
        assert exclusion.display_text.strip(), exclusion


def test_communities_a_c_and_d_assessed_against_a_vegetable_donation_are_category_compatible(
    demo_clock: PinnedClock,
) -> None:
    """VEGETABLE DONATION + A, C, D -> assess -> all three are category compatible.

    The negative case alone would pass for an implementation that excludes
    everyone.
    """
    donation = world.donation()
    for community in (world.community_a(), world.community_c(), world.community_d()):
        assessment = domain_api.assess_one(donation=donation, community=community, clock=demo_clock)
        assert assessment.category_compatible is True, community.community_id
