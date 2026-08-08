"""Partial acceptance through the real P1 arithmetic and decline policy."""

from __future__ import annotations

import pytest

from backend.app.contracts.core import (
    CommunityNeed,
    CommunityOrganisation,
    FoodCategory,
    Location,
    NeedLevel,
    StorageType,
    TimeWindow,
)
from backend.app.domain.clock import DEMO_NOW
from backend.app.domain.errors import EligibilityError, ErrorCode
from backend.app.domain.policies.partial_acceptance import (
    correct_declared_capacity,
    declined_exclusion,
    evaluate_acceptance,
)


def community_a() -> CommunityOrganisation:
    return CommunityOrganisation(
        community_id="A",
        name="Community A",
        location=Location(name="Community A", latitude=-36.90, longitude=174.74),
        accepted_categories=[FoodCategory.VEGETABLES],
        supported_storage=[StorageType.AMBIENT],
        needs=[CommunityNeed(category=FoodCategory.VEGETABLES, level=NeedLevel.URGENT)],
        declared_capacity_kg=60,
        remaining_capacity_kg=0,
        receiving_window=TimeWindow(start=DEMO_NOW, end=DEMO_NOW.replace(hour=20)),
        is_open=True,
    )


def test_sixty_planned_and_thirty_five_accepted_produces_exact_twenty_five_remainder() -> None:
    """PLANNED 60 + ACCEPTED 35 -> evaluate -> accepted 35, remaining 25."""
    outcome = evaluate_acceptance(
        order_id="DO-1",
        community_id="A",
        planned_kg=60,
        accepted_kg=35,
    )

    assert outcome.accepted_kg == 35
    assert outcome.remaining_kg == 25
    assert outcome.requires_rematch is True
    assert outcome.is_full_acceptance is False
    assert outcome.is_rejection is False


@pytest.mark.parametrize(
    ("accepted_kg", "remaining_kg", "is_rejection", "is_full_acceptance"),
    [(0, 60, True, False), (60, 0, False, True)],
)
def test_zero_and_full_acceptance_take_the_correct_boundary_branch(
    accepted_kg: int,
    remaining_kg: int,
    is_rejection: bool,
    is_full_acceptance: bool,
) -> None:
    """ACCEPTED 0/60 -> evaluate -> rejection/full boundary without rounding."""
    outcome = evaluate_acceptance(
        order_id="DO-1",
        community_id="A",
        planned_kg=60,
        accepted_kg=accepted_kg,
    )
    assert outcome.remaining_kg == remaining_kg
    assert outcome.is_rejection is is_rejection
    assert outcome.is_full_acceptance is is_full_acceptance


@pytest.mark.parametrize("accepted_kg", [-1, 61])
def test_acceptance_outside_zero_to_planned_range_raises_typed_error(accepted_kg: int) -> None:
    """ACCEPTED BELOW 0 OR ABOVE 60 -> evaluate -> typed rejection."""
    with pytest.raises(EligibilityError) as raised:
        evaluate_acceptance(
            order_id="DO-1",
            community_id="A",
            planned_kg=60,
            accepted_kg=accepted_kg,
        )
    assert raised.value.code is ErrorCode.RECIPIENT_CAPACITY_EXCEEDED


def test_partial_acceptance_corrects_declared_capacity_and_leaves_no_remaining_capacity() -> None:
    """A DECLARED 60 BUT ACCEPTS 35 -> correct -> declared 35, remaining 0."""
    outcome = evaluate_acceptance(
        order_id="DO-1",
        community_id="A",
        planned_kg=60,
        accepted_kg=35,
    )

    corrected = correct_declared_capacity(community_a(), outcome)

    assert corrected.declared_capacity_kg == 35
    assert corrected.remaining_capacity_kg == 0


def test_declining_recipient_exclusion_is_typed_and_displayable() -> None:
    """PARTIAL DECLINE -> build exclusion -> stable code and visible text."""
    exclusion = declined_exclusion()
    assert exclusion.code is ErrorCode.RECIPIENT_DECLINED_THIS_DONATION
    assert exclusion.display_text.strip()
