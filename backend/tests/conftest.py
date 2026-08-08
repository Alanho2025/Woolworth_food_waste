"""Shared fixtures.

Mocks isolate DeepSeek, the clock, and routing only. No fixture here supplies an
allocation, capacity, or eligibility decision — those are the subject of the
tests (foodflow_clean_code_spec.md 10.2).
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Iterator
from datetime import datetime
from pathlib import Path

import pytest

# `backend/` has no __init__.py, so pytest puts `backend/` on sys.path rather
# than the repository root. The application package is imported as
# `backend.app.*`, which needs the repository root.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.contracts.core import (  # noqa: E402
    CommunityOrganisation,
    DonationInventory,
    DonationRequest,
    Driver,
)
from backend.app.domain.clock import DEMO_NOW, PinnedClock  # noqa: E402
from backend.tests.support import world  # noqa: E402


@pytest.fixture
def demo_clock() -> PinnedClock:
    """The DEMO_MODE clock: 2026-08-08 15:45 Auckland, fifteen minutes before pickup."""
    return PinnedClock(DEMO_NOW)


@pytest.fixture
def clock_at() -> Callable[[int, int], PinnedClock]:
    """Build a PinnedClock at an Auckland wall-clock hour on the demo date."""

    def _build(hour: int, minute: int = 0) -> PinnedClock:
        return PinnedClock(world.auckland(hour, minute))

    return _build


@pytest.fixture
def donation() -> DonationRequest:
    return world.donation()


@pytest.fixture
def inventory() -> DonationInventory:
    return world.fresh_inventory()


@pytest.fixture
def communities() -> list[CommunityOrganisation]:
    return world.all_communities()


@pytest.fixture
def drivers() -> list[Driver]:
    return world.all_drivers()


@pytest.fixture
def demo_now() -> datetime:
    return DEMO_NOW


@pytest.fixture(autouse=True)
def _isolated_settings_cache() -> Iterator[None]:
    """Never let one test's environment leak into another's Settings.

    `get_settings` is `lru_cache`d, which is right for the application and wrong
    for a suite that varies DEMO_MODE and AGENT_TRANSPORT.
    """
    from backend.app.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
