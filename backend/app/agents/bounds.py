"""Loop and tool budgets. Built here because the framework does not supply them.

Verified against the installed google-adk 2.6.3: `RunConfig` exposes
`max_llm_calls`, `streaming_mode`, `speech_config`, `response_modalities`,
`save_live_blob`, `tool_thread_pool_config`, `custom_metadata` and friends --
and NO per-tool timeout and NO wall-clock timeout. The `ToolCallTimeout` and
`MaxTurns` fields in circulation online belong to `adk-golang`, a third-party Go
port, not this SDK.

clean_code_spec 7.1 requires the loop to have a timeout and 7.4 requires one on
every tool that performs I/O, so both are implemented here:

  * `run_within_budget`  -- asyncio.wait_for around the runner invocation
  * `call_tool_within_budget` -- asyncio.wait_for around each I/O tool body

See docs/phase_review_findings.md R-5.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar

from backend.app.config import Settings
from backend.app.domain.errors import AgentError, ErrorCode

T = TypeVar("T")


@dataclass(frozen=True)
class AgentBounds:
    """The three budgets that make the Agent loop terminate."""

    max_llm_calls: int
    run_timeout_seconds: float
    tool_timeout_seconds: float

    @classmethod
    def from_settings(cls, settings: Settings) -> AgentBounds:
        return cls(
            max_llm_calls=settings.agent_max_llm_calls,
            run_timeout_seconds=settings.agent_run_timeout_seconds,
            tool_timeout_seconds=settings.agent_tool_timeout_seconds,
        )


async def run_within_budget(work: Awaitable[T], bounds: AgentBounds) -> T:
    """Wall-clock bound on one whole Agent run.

    A hung run is the failure mode that cannot be survived on stage: a visible,
    recovering error is recoverable, a frozen screen is not.
    """
    try:
        return await asyncio.wait_for(work, timeout=bounds.run_timeout_seconds)
    except TimeoutError as exc:
        raise AgentError(
            ErrorCode.AGENT_TIMEOUT,
            f"Agent run exceeded its {bounds.run_timeout_seconds:g}s wall-clock budget",
        ) from exc


async def call_tool_within_budget(
    tool_name: str,
    work: Callable[[], T],
    bounds: AgentBounds,
) -> T:
    """Run one tool's synchronous I/O off the event loop, under its own timeout.

    The repositories are synchronous, so the body runs in a worker thread; that
    is also what makes `asyncio.wait_for` able to abandon a slow tool without
    blocking the loop that is enforcing the run-level budget.
    """
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(work), timeout=bounds.tool_timeout_seconds
        )
    except TimeoutError as exc:
        raise AgentError(
            ErrorCode.TOOL_TIMEOUT,
            f"Tool {tool_name} exceeded its {bounds.tool_timeout_seconds:g}s budget",
        ) from exc
