"""Declared-versus-remaining recipient capacity through the real policy."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

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
from backend.app.domain.errors import EligibilityError, ErrorCode
from backend.app.domain.policies.capacity import reserve_recipient_capacity

AUCKLAND = ZoneInfo("Pacific/Auckland")


def community_a() -> CommunityOrganisation:
    return CommunityOrganisation(
        community_id="A",
        name="Community A",
        location=Location(name="Community A", latitude=-36.9082, longitude=174.7387),
        accepted_categories=[FoodCategory.VEGETABLES],
        supported_storage=[StorageType.AMBIENT],
        needs=[CommunityNeed(category=FoodCategory.VEGETABLES, level=NeedLevel.URGENT)],
        declared_capacity_kg=60,
        remaining_capacity_kg=60,
        receiving_window=TimeWindow(
            start=datetime(2026, 8, 8, 8, 0, tzinfo=AUCKLAND),
            end=datetime(2026, 8, 8, 20, 0, tzinfo=AUCKLAND),
        ),
        is_open=True,
    )


def test_reserving_sixty_preserves_declared_capacity_and_consumes_remaining_capacity() -> None:
    """A DECLARES/REMAINS 60 -> reserve 60 -> declared 60, remaining 0."""
    original = community_a()

    reserved = reserve_recipient_capacity(original, 60)

    assert reserved.declared_capacity_kg == 60
    assert reserved.remaining_capacity_kg == 0
    assert original.remaining_capacity_kg == 60, "frozen input must not be mutated"


def test_reserving_more_than_remaining_capacity_raises_typed_capacity_error() -> None:
    """A REMAINS 60 -> reserve 61 -> RECIPIENT_CAPACITY_EXCEEDED."""
    original = community_a()

    with pytest.raises(EligibilityError) as raised:
        reserve_recipient_capacity(original, 61)

    assert raised.value.code is ErrorCode.RECIPIENT_CAPACITY_EXCEEDED
    assert original.declared_capacity_kg == 60
    assert original.remaining_capacity_kg == 60
