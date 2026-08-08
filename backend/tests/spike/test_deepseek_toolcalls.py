"""P0 live measurement: ADK 2.6.x -> LiteLLM -> DeepSeek typed tools.

This is deliberately committed, skipped by default, and re-runnable with the
exact command in ``docs/implementation_phases.md``. It never prints prompts,
provider payloads, exception messages, or credentials. Only aggregate counts
and latency statistics leave the test process.
"""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass, field
from typing import Any

import pytest
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm, LiteLLMClient
from google.adk.runners import InMemoryRunner

from backend.app.config import Settings

TURN_COUNT = 30
EXPECTED_TOOLS = frozenset({"typed_increment", "typed_scale", "typed_label"})


def typed_increment(value: int) -> dict[str, int]:
    """Return ``value + 1`` as a typed, JSON-serializable object."""
    return {"incremented": value + 1}


def typed_scale(value: int, factor: int) -> dict[str, int]:
    """Return ``value * factor`` as a typed, JSON-serializable object."""
    return {"scaled": value * factor}


def typed_label(turn: int, label: str) -> dict[str, str | int]:
    """Return an opaque turn label as a typed, JSON-serializable object."""
    return {"turn": turn, "label": label}


def _contains_reasoning_content(value: object) -> bool:
    """Detect a non-null ``reasoning_content`` field in a raw provider payload."""
    if isinstance(value, dict):
        return any(
            (key == "reasoning_content" and nested is not None)
            or _contains_reasoning_content(nested)
            for key, nested in value.items()
        )
    if isinstance(value, list):
        return any(_contains_reasoning_content(item) for item in value)
    return False


class CapturingLiteLlmClient(LiteLLMClient):
    """Capture only the two facts the spike asserts; retain no response text."""

    def __init__(self) -> None:
        self.response_count = 0
        self.reasoning_response_count = 0
        self.forwarded_extra_bodies: list[object] = []

    async def acompletion(self, model: Any, messages: Any, tools: Any, **kwargs: Any) -> Any:
        self.forwarded_extra_bodies.append(kwargs.get("extra_body"))
        response = await super().acompletion(model=model, messages=messages, tools=tools, **kwargs)
        self.response_count += 1
        model_dump = getattr(response, "model_dump", None)
        payload = model_dump(exclude_none=True) if callable(model_dump) else {}
        if _contains_reasoning_content(payload):
            self.reasoning_response_count += 1
        return response


@dataclass
class ArmResult:
    name: str
    turns_attempted: int = 0
    failures: int = 0
    latencies_seconds: list[float] = field(default_factory=list)
    failure_kinds: dict[str, int] = field(default_factory=dict)
    response_count: int = 0
    reasoning_response_count: int = 0

    @property
    def failure_rate(self) -> float:
        return self.failures / self.turns_attempted if self.turns_attempted else 1.0

    @property
    def p95_seconds(self) -> float:
        if not self.latencies_seconds:
            return 0.0
        ordered = sorted(self.latencies_seconds)
        index = min(len(ordered) - 1, int(0.95 * len(ordered)))
        return ordered[index]

    def record_failure(self, kind: str) -> None:
        self.failures += 1
        self.failure_kinds[kind] = self.failure_kinds.get(kind, 0) + 1


def _settings_without_reading_process_environment() -> Settings:
    """Read the project config boundary, then require the live secret there."""
    # Unlike ordinary unit tests, this live opt-in intentionally reads .env via
    # the one authorised config boundary. No field is echoed by this module.
    return Settings()


async def _measure_arm(
    *, name: str, settings: Settings, extra_body: dict[str, object] | None
) -> tuple[ArmResult, CapturingLiteLlmClient]:
    key = settings.require_deepseek_key()
    client = CapturingLiteLlmClient()
    model_kwargs: dict[str, object] = {
        "api_key": key,
        "api_base": settings.deepseek_base_url,
        "temperature": 0,
        "llm_client": client,
    }
    if extra_body is not None:
        model_kwargs["extra_body"] = extra_body

    model = LiteLlm(model=f"openai/{settings.deepseek_model}", **model_kwargs)
    agent = LlmAgent(
        name=f"p0_spike_{name}",
        model=model,
        instruction=(
            "This is a tool-protocol reliability test. For every user turn, call "
            "typed_increment, typed_scale, and typed_label exactly once each. "
            "All three calls are mandatory. After their results arrive, reply only DONE."
        ),
        tools=[typed_increment, typed_scale, typed_label],
    )
    runner = InMemoryRunner(agent=agent)
    result = ArmResult(name=name)

    for turn in range(1, TURN_COUNT + 1):
        result.turns_attempted += 1
        started = time.perf_counter()
        try:
            events = await runner.run_debug(
                (
                    f"Turn {turn}. Call all three required tools. Use value={turn}, "
                    f"factor=2, turn={turn}, label='p0-{turn}'."
                ),
                user_id=f"p0-{name}",
                session_id=f"p0-{name}-{turn}",
                quiet=True,
            )
            called = {
                call.name
                for event in events
                for call in event.get_function_calls()
                if call.name is not None
            }
            if called != EXPECTED_TOOLS:
                result.record_failure("incomplete_tool_set")
        except Exception as exc:  # provider errors are data, not secret-bearing output
            result.record_failure(type(exc).__name__)
        finally:
            result.latencies_seconds.append(time.perf_counter() - started)

    result.response_count = client.response_count
    result.reasoning_response_count = client.reasoning_response_count
    return result, client


@pytest.mark.skip(reason="P0 spike; unskip to re-measure")
@pytest.mark.spike
@pytest.mark.live
@pytest.mark.asyncio
async def test_two_arms_complete_30_typed_multi_tool_turns_and_measure_reliability() -> None:
    """TWO MODEL MODES -> 30 multi-tool turns each -> record reliability and reasoning."""
    settings = _settings_without_reading_process_environment()
    arm_a, arm_a_client = await _measure_arm(
        name="thinking_disabled",
        settings=settings,
        extra_body={"thinking": {"type": "disabled"}},
    )
    arm_b, _arm_b_client = await _measure_arm(
        name="provider_default",
        settings=settings,
        extra_body=None,
    )

    for result in (arm_a, arm_b):
        print(
            f"P0 spike {result.name}: turns={result.turns_attempted}, "
            f"failures={result.failures}, failure_rate={result.failure_rate:.3f}, "
            f"median_s={statistics.median(result.latencies_seconds):.3f}, "
            f"p95_s={result.p95_seconds:.3f}, responses={result.response_count}, "
            f"reasoning_responses={result.reasoning_response_count}, "
            f"failure_kinds={sorted(result.failure_kinds.items())}"
        )

    assert arm_a.turns_attempted == TURN_COUNT
    assert arm_b.turns_attempted == TURN_COUNT
    assert arm_a_client.forwarded_extra_bodies
    assert all(
        body == {"thinking": {"type": "disabled"}} for body in arm_a_client.forwarded_extra_bodies
    ), "ADK LiteLlm did not forward Arm A's explicit thinking-disabled body"
    assert arm_a.reasoning_response_count == 0, (
        "Arm A returned reasoning_content despite explicit thinking disablement"
    )
    assert arm_a.failures == 0, (
        "Arm A is not reliable enough to enter P1; use the aggregate failure kinds above"
    )
