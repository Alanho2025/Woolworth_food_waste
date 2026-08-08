"""Configuration boundary.

This is the ONLY module in the backend that reads environment variables
(clean_code_spec 6.4). Secrets never leave it, and never reach the frontend
bundle, logs, prompts, or test fixtures.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentTransport(StrEnum):
    LIVE = "live"
    REPLAY = "replay"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # DeepSeek.
    #
    # deepseek-v4-flash is the current generation and the choice here; the legacy
    # deepseek-chat / deepseek-reasoner aliases still resolve (verified by live
    # probe 2026-08-08) but are on a deprecation path. deepseek-v4-pro costs
    # roughly 3.1x and is not needed for this journey.
    #
    # Load-bearing, and empirically verified: deepseek-v4-flash runs with
    # THINKING ENABLED BY DEFAULT and returns reasoning_content. It must be
    # explicitly disabled -- see the adapter, and docs/assumption_audit.md A-1/D-5.
    # The key stays optional so replay mode genuinely works without a secret.
    # `require_deepseek_key` is the loud boundary when live transport is used.
    deepseek_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("DEEPSEEK_API_KEY", "DeepSeekAPI_KEY"),
    )
    deepseek_base_url: str
    deepseek_model: str

    database_url: str

    # Pins the clock and uses the seeded world. Without it, receiving-window
    # checks compare against real wall-clock time and every community is
    # correctly closed outside 16:00-19:00 NZ. See docs/assumption_audit.md C-1.
    demo_mode: bool

    # Separate from demo_mode on purpose. One boolean driving both the clock and
    # the model transport would violate clean_code_spec 5.2, and would make the
    # combination we actually need for rehearsal -- live model, pinned clock --
    # unreachable. See docs/phase_review_findings.md R-9.
    agent_transport: AgentTransport

    # Bounded loop. ADK's RunConfig.max_llm_calls defaults to 500, which would
    # let a runaway loop make 500 DeepSeek calls before stopping.
    agent_max_llm_calls: int = Field(default=24, gt=0)
    # RunConfig has NO wall-clock or per-tool timeout field -- the ToolCallTimeout
    # and MaxTurns fields in circulation belong to adk-golang, a third-party Go
    # port, not this SDK. clean_code_spec 7.1 and 7.4 require both timeouts, so
    # they are enforced here in application code.
    # See docs/phase_review_findings.md R-5.
    agent_run_timeout_seconds: float = Field(default=90.0, gt=0)
    agent_tool_timeout_seconds: float = Field(default=10.0, gt=0)

    def require_deepseek_key(self) -> str:
        """Fail loudly rather than making a live call with an empty key."""
        if not self.deepseek_api_key.strip():
            raise RuntimeError(
                "DEEPSEEK_API_KEY is not set. Set it, or run with "
                "AGENT_TRANSPORT=replay to use recorded fixtures."
            )
        return self.deepseek_api_key


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    # Required values are supplied by BaseSettings from the environment rather
    # than as Python arguments, which mypy cannot infer.
    return Settings()  # type: ignore[call-arg]
