"""P0 executable smoke checks for Agent-only quality-gate stages."""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

from backend.app.config import AgentTransport, Settings


class ToolResultEnvelope(BaseModel):
    """Minimal strict result proving schema validation is wired into the gate."""

    model_config = ConfigDict(extra="forbid", strict=True)
    ok: bool
    code: str


def test_agent_schema_validation_rejects_an_untyped_extra_field() -> None:
    """MODEL OUTPUT WITH EXTRA FIELD -> validate -> typed boundary rejects it."""
    with pytest.raises(ValidationError):
        ToolResultEnvelope.model_validate({"ok": True, "code": "OK", "secret": "no"})


def test_agent_bounded_loop_configuration_has_a_small_positive_limit() -> None:
    """P0 SETTINGS -> inspect loop limit -> positive and far below ADK's 500 default."""
    settings = Settings(
        _env_file=None,
        deepseek_base_url="https://api.deepseek.com",
        deepseek_model="deepseek-v4-flash",
        database_url="sqlite:///./foodflow.db",
        demo_mode=True,
        agent_transport=AgentTransport.REPLAY,
    )
    assert 0 < settings.agent_max_llm_calls <= 100
