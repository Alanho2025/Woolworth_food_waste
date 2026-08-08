"""Time.

Every receiving-window and deadline check compares against "now". The demo is
pinned to a pickup window of 16:00-17:00 and a deadline of 19:00 Auckland time.
If the demo runs at 10:00, all four communities are legitimately closed and the
Agent correctly excludes every one of them -- the pitch dies and the code is
not at fault. So "now" is injected, never read from the wall clock directly.

NZ local time is resolved through the Pacific/Auckland zone and never through a
literal +12:00. New Zealand moves to NZDT (+13:00) on 2026-09-27; a hardcoded
offset silently shifts every window by an hour after that date.

See docs/assumption_audit.md C-1.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol
from zoneinfo import ZoneInfo

AUCKLAND = ZoneInfo("Pacific/Auckland")

# Fifteen minutes before the pickup window opens, so the demo starts with the
# window ahead of it rather than already inside it.
DEMO_NOW = datetime(2026, 8, 8, 15, 45, 0, tzinfo=AUCKLAND)


class Clock(Protocol):
    """Supplies the current instant. Always timezone-aware, always UTC."""

    def now(self) -> datetime:
        """Current instant as a timezone-aware UTC datetime."""
        ...


class SystemClock:
    """Real wall-clock time. Used when DEMO_MODE is off."""

    def now(self) -> datetime:
        return datetime.now(UTC)


class PinnedClock:
    """A fixed instant. Used when DEMO_MODE is on, and in tests."""

    def __init__(self, instant: datetime = DEMO_NOW) -> None:
        if instant.tzinfo is None:
            raise ValueError("PinnedClock requires a timezone-aware datetime")
        self._instant = instant.astimezone(UTC)

    def now(self) -> datetime:
        return self._instant


def to_auckland(instant: datetime) -> datetime:
    """Render a UTC instant in Auckland local time for display and window maths."""
    if instant.tzinfo is None:
        raise ValueError("to_auckland requires a timezone-aware datetime")
    return instant.astimezone(AUCKLAND)
