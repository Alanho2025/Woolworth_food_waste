"""Receiving window (foodflow_clean_code_spec.md 10.1, group 4) and the demo clock.

THE FAILURE THIS FILE EXISTS FOR
--------------------------------
docs/assumption_audit.md C-1, promoted to BLOCKER. The demo is pinned to a
16:00-17:00 pickup window and a 19:00 deadline, Auckland time. If the demo runs
at 10:00 in the morning, every one of the four communities is legitimately
closed, the Agent correctly excludes all four, the pitch dies, and the code is
not at fault. It is the single failure that only appears on stage, because every
developer who tests it during working hours sees it pass.

The defence is that "now" is injected through the `Clock` port and never read
from the wall clock. This file proves the defence from both sides:

  * the window check genuinely FAILS at 03:00 and at 23:00, so it is not vacuous;
  * the DEMO_MODE clock (`domain/clock.py DEMO_NOW`) lands inside every seeded
    receiving window, so the demo passes whatever the machine clock says.

`backend/tests/test_architecture.py::test_no_module_outside_domain_clock_reads_the_wall_clock_directly`
is the third leg: it proves no module can bypass the injected clock. The machine
clock is never changed by this suite — `sudo date` would be both destructive and
useless in CI.
"""

from __future__ import annotations

import pytest

from backend.app.contracts.core import TimeWindow
from backend.app.domain.clock import AUCKLAND, DEMO_NOW, PinnedClock, SystemClock, to_auckland
from backend.app.domain.errors import ErrorCode
from backend.tests.support import domain_api, world

# The two wall-clock times that break the demo. 03:00 is before every seeded
# window opens; 23:00 is after every one has closed.
HOSTILE_HOURS = [3, 23]


# --------------------------------------------------------------------------
# The demo clock itself — runs today, depends on no unbuilt module
# --------------------------------------------------------------------------


def test_the_demo_clock_sits_fifteen_minutes_before_the_pickup_window_opens() -> None:
    """DEMO_NOW -> compare with the 16:00 pickup window -> 15:45, just outside it.

    Starting inside the window would rob the demo of the "pickup is imminent"
    framing; starting hours before it would make every ETA implausible.
    """
    local_now = to_auckland(PinnedClock(DEMO_NOW).now())
    window = world.pickup_window()
    assert (local_now.hour, local_now.minute) == (15, 45)
    assert local_now < window.start
    assert (window.start - local_now).total_seconds() == 15 * 60


def test_the_demo_clock_is_resolved_through_the_auckland_zone_not_a_literal_offset() -> None:
    """DEMO_NOW -> inspect its tzinfo -> Pacific/Auckland.

    New Zealand moves to NZDT (+13:00) on 2026-09-27. A hardcoded +12:00 shifts
    every window by an hour after that date, silently.
    """
    assert DEMO_NOW.tzinfo is AUCKLAND
    assert str(DEMO_NOW.tzinfo) == "Pacific/Auckland"


def test_the_zone_still_resolves_correctly_after_the_2026_dst_transition() -> None:
    """AN INSTANT AFTER 2026-09-27 -> convert to Auckland -> +13:00, not +12:00.

    A regression pin on the literal-offset trap rather than on today's value.
    """
    from datetime import UTC, datetime

    summer = datetime(2026, 12, 25, 12, 0, tzinfo=UTC)
    offset = to_auckland(summer).utcoffset()
    assert offset is not None
    assert offset.total_seconds() == 13 * 3600


@pytest.mark.parametrize(
    "community_builder_name", ["community_a", "community_b", "community_c", "community_d"]
)
def test_every_seeded_receiving_window_contains_the_demo_clock_instant(
    community_builder_name: str,
) -> None:
    """DEMO_NOW -> compare against each seeded receiving window -> inside all four.

    If this fails, the demo excludes communities for a reason the pitch never
    intends to demonstrate.
    """
    community = getattr(world, community_builder_name)()
    window: TimeWindow = community.receiving_window
    now = PinnedClock(DEMO_NOW).now()
    assert window.start <= now <= window.end, (
        f"{community.community_id} window {window.start}..{window.end} excludes DEMO_NOW {now}"
    )


@pytest.mark.parametrize("hour", HOSTILE_HOURS)
def test_a_clock_at_an_hostile_hour_falls_outside_every_seeded_receiving_window(hour: int) -> None:
    """PINNED CLOCK AT 03:00 / 23:00 -> compare against every window -> outside all four.

    The proof that the window comparison above is not vacuously true. At these
    two hours the correct answer really is "everyone is closed" — which is
    exactly the on-stage disaster the injected clock prevents.
    """
    now = PinnedClock(world.auckland(hour)).now()
    for community in world.all_communities():
        window = community.receiving_window
        assert not (window.start <= now <= window.end), (
            f"{community.community_id} appears open at {hour:02d}:00; "
            "the hostile-hour test can no longer detect the C-1 failure"
        )


def test_the_system_clock_and_the_pinned_clock_are_different_objects_with_different_answers() -> (
    None
):
    """SYSTEM CLOCK vs PINNED CLOCK -> read both -> the pinned one ignores wall time.

    Cheap, but it is the assertion that would fail the day someone "simplifies"
    PinnedClock into a SystemClock alias.
    """
    pinned = PinnedClock(DEMO_NOW)
    assert pinned.now() == pinned.now()
    assert pinned.now() != SystemClock().now()


def test_a_naive_datetime_is_refused_by_the_pinned_clock() -> None:
    """NAIVE DATETIME -> construct PinnedClock -> ValueError.

    A naive instant compared against a zone-aware window raises TypeError deep
    inside a policy; failing at construction is the loud version of that.
    """
    from datetime import datetime

    with pytest.raises(ValueError, match="timezone-aware"):
        PinnedClock(datetime(2026, 8, 8, 15, 45))


# --------------------------------------------------------------------------
# The policy — the same proof, through the real receiving-window check
# --------------------------------------------------------------------------


def test_all_four_communities_are_window_open_under_the_demo_clock(demo_clock: PinnedClock) -> None:
    """DEMO CLOCK -> assess all four communities -> window_open_on_arrival for each.

    Requirement.md 16 needs B excluded on category and C on capacity — not on
    opening hours. A window failure here would exclude the wrong organisations
    for the wrong reasons and the scripted beats would not land.
    """
    assessments = domain_api.assess_candidates(
        donation=world.donation(), communities=world.all_communities(), clock=demo_clock
    )
    closed = [a.community.community_id for a in assessments if not a.window_open_on_arrival]
    assert closed == [], f"closed under the demo clock: {closed}"


@pytest.mark.parametrize("hour", HOSTILE_HOURS)
def test_all_four_communities_are_window_closed_under_a_clock_at_an_hostile_hour(hour: int) -> None:
    """PINNED CLOCK AT 03:00 / 23:00 -> assess all four -> every window is closed.

    Deliberately asserts the *bad* outcome. It proves the receiving-window rule
    is real rather than hardcoded to True, which is the only way the passing
    test above means anything.
    """
    hostile_clock = PinnedClock(world.auckland(hour))
    assessments = domain_api.assess_candidates(
        donation=world.donation(), communities=world.all_communities(), clock=hostile_clock
    )
    open_now = [a.community.community_id for a in assessments if a.window_open_on_arrival]
    assert open_now == [], f"open at {hour:02d}:00: {open_now}"


@pytest.mark.parametrize("hour", HOSTILE_HOURS)
def test_the_demo_clock_keeps_every_window_open_regardless_of_the_hour_the_demo_is_run(
    hour: int,
) -> None:
    """WALL CLOCK AT 03:00 / 23:00, DEMO CLOCK INJECTED -> assess -> every window open.

    THE test of this file. Two clocks are constructed in the same process: one
    standing in for a hostile machine clock, one being the DEMO_MODE clock. The
    hostile clock closes every window; the injected demo clock opens every one.
    Since the policy is given the clock rather than reading it, the demo is
    independent of the hour it is presented.
    """
    hostile_clock = PinnedClock(world.auckland(hour))
    demo_clock = PinnedClock(DEMO_NOW)
    donation = world.donation()
    communities = world.all_communities()

    under_hostile = domain_api.assess_candidates(
        donation=donation, communities=communities, clock=hostile_clock
    )
    under_demo = domain_api.assess_candidates(
        donation=donation, communities=communities, clock=demo_clock
    )

    assert all(not a.window_open_on_arrival for a in under_hostile)
    assert all(a.window_open_on_arrival for a in under_demo)


@pytest.mark.parametrize("hour", HOSTILE_HOURS)
def test_a_window_closed_candidate_is_excluded_under_the_receiving_window_code(hour: int) -> None:
    """PINNED CLOCK AT AN HOSTILE HOUR -> assess Community A -> RECEIVING_WINDOW_CLOSED."""
    assessment = domain_api.assess_one(
        donation=world.donation(),
        community=world.community_a(),
        clock=PinnedClock(world.auckland(hour)),
    )
    codes = [exclusion.code for exclusion in assessment.exclusions]
    assert ErrorCode.RECEIVING_WINDOW_CLOSED in codes, codes


def test_a_community_flagged_closed_is_excluded_even_inside_its_published_window(
    demo_clock: PinnedClock,
) -> None:
    """OPEN WINDOW BUT is_open FALSE -> assess -> window_open_on_arrival is False.

    `is_open` is a live operational flag, not a derived one; published hours and
    the shutter being up are two different facts.
    """
    shuttered = world.community_a().model_copy(update={"is_open": False})
    assessment = domain_api.assess_one(
        donation=world.donation(), community=shuttered, clock=demo_clock
    )
    assert assessment.window_open_on_arrival is False
