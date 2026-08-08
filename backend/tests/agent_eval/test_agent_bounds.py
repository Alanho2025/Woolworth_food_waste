"""P3 forced-runaway checks for the real wall-clock and tool budget wrappers."""

from __future__ import annotations

import asyncio
import time

import pytest

from backend.app.agents.bounds import AgentBounds, call_tool_within_budget, run_within_budget
from backend.app.domain.errors import AgentError, ErrorCode


def tiny_bounds() -> AgentBounds:
    return AgentBounds(
        max_llm_calls=2,
        run_timeout_seconds=0.01,
        tool_timeout_seconds=0.01,
    )


@pytest.mark.asyncio
async def test_agent_run_that_never_finishes_is_cancelled_by_wall_clock_budget() -> None:
    """NON-TERMINATING RUN -> real budget wrapper -> typed AGENT_TIMEOUT."""
    cancelled = asyncio.Event()

    async def never_finishes() -> None:
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    with pytest.raises(AgentError) as raised:
        await run_within_budget(never_finishes(), tiny_bounds())

    assert raised.value.code is ErrorCode.AGENT_TIMEOUT
    assert cancelled.is_set(), "timed-out Agent task must be cancelled, not left running"


@pytest.mark.asyncio
async def test_blocking_tool_that_exceeds_budget_returns_typed_tool_timeout() -> None:
    """SLOW SYNC TOOL -> real thread/time budget -> typed TOOL_TIMEOUT."""

    def slow_tool() -> str:
        time.sleep(0.05)
        return "too late"

    with pytest.raises(AgentError) as raised:
        await call_tool_within_budget("slow_tool", slow_tool, tiny_bounds())

    assert raised.value.code is ErrorCode.TOOL_TIMEOUT
    assert "slow_tool" in raised.value.detail
