"""The configuration boundary.

`backend/app/config.py` is the only module permitted to read the environment
(foodflow_clean_code_spec.md 6.4). Two things are load-bearing here:

  * `DEMO_MODE` and `AGENT_TRANSPORT` are two flags, not one. One boolean
    driving both the clock and the model transport would make the combination
    the team actually needs for rehearsal — live model, pinned clock —
    unreachable (docs/phase_review_findings.md R-9).
  * `require_deepseek_key()` fails loudly rather than issuing a live call with
    an empty key.

Every Settings instance below is constructed with `_env_file=None`. The
developer `.env` holds a real key; a suite that reads it would pass or fail
depending on whose machine it ran on, and could print a secret into CI output.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.app.config import AgentTransport, Settings, get_settings

PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = PROJECT_ROOT / "backend" / "app"


REQUIRED_SETTINGS: dict[str, object] = {
    "deepseek_base_url": "https://api.deepseek.com",
    "deepseek_model": "deepseek-v4-flash",
    "database_url": "sqlite:///./foodflow.db",
    "demo_mode": True,
    "agent_transport": AgentTransport.REPLAY,
}


def isolated(**overrides: object) -> Settings:
    """A Settings built from explicit values only — no .env, no process env."""
    values = {**REQUIRED_SETTINGS, **overrides}
    return Settings(_env_file=None, **values)  # type: ignore[call-arg]


# --------------------------------------------------------------------------
# Every setting loads
# --------------------------------------------------------------------------


def test_all_six_documented_variables_load_at_the_configuration_boundary() -> None:
    """ALL SIX VARIABLES SET -> construct Settings -> typed values are present."""
    settings = isolated()

    assert settings.deepseek_api_key == ""
    assert settings.deepseek_base_url == "https://api.deepseek.com"
    assert settings.deepseek_model == "deepseek-v4-flash"
    assert settings.database_url.startswith("sqlite")
    assert settings.demo_mode is True
    assert settings.agent_transport is AgentTransport.REPLAY
    assert settings.agent_run_timeout_seconds > 0
    assert settings.agent_tool_timeout_seconds > 0


@pytest.mark.parametrize(
    "missing",
    [
        "deepseek_base_url",
        "deepseek_model",
        "database_url",
        "demo_mode",
        "agent_transport",
    ],
)
def test_missing_required_configuration_variable_raises_validation_error(
    missing: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ONE REQUIRED VARIABLE MISSING -> construct Settings -> fail at the boundary."""
    monkeypatch.delenv(missing.upper(), raising=False)
    values = {name: value for name, value in REQUIRED_SETTINGS.items() if name != missing}
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)  # type: ignore[call-arg]


def test_agent_max_llm_calls_defaults_far_below_the_adk_default_of_500() -> None:
    """EMPTY ENVIRONMENT -> read agent_max_llm_calls -> a bounded, small budget.

    ADK's RunConfig.max_llm_calls defaults to 500, which would let a runaway
    loop make 500 DeepSeek calls before stopping. clean_code_spec 7.1 requires
    a bounded loop.
    """
    settings = isolated()
    assert 0 < settings.agent_max_llm_calls <= 100, settings.agent_max_llm_calls


def test_every_setting_can_be_overridden_from_the_process_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ENVIRONMENT SET -> construct Settings -> the environment wins."""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-not-a-real-secret")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://example.invalid")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./other.db")
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setenv("AGENT_TRANSPORT", "live")
    monkeypatch.setenv("AGENT_MAX_LLM_CALLS", "7")

    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    assert settings.deepseek_api_key == "test-key-not-a-real-secret"
    assert settings.deepseek_base_url == "https://example.invalid"
    assert settings.deepseek_model == "deepseek-v4-pro"
    assert settings.database_url == "sqlite:///./other.db"
    assert settings.demo_mode is False
    assert settings.agent_transport is AgentTransport.LIVE
    assert settings.agent_max_llm_calls == 7


def test_legacy_mixed_case_deepseek_key_environment_name_is_supported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """LEGACY KEY NAME -> config boundary -> live key remains usable during migration."""
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("DeepSeekAPI_KEY", "legacy-test-key-not-a-real-secret")

    settings = Settings(_env_file=None, **REQUIRED_SETTINGS)  # type: ignore[call-arg]

    assert settings.require_deepseek_key() == "legacy-test-key-not-a-real-secret"


def test_standard_deepseek_key_name_takes_precedence_over_legacy_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """BOTH KEY NAMES -> config boundary -> documented uppercase name wins."""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "standard-test-key-not-a-real-secret")
    monkeypatch.setenv("DeepSeekAPI_KEY", "legacy-test-key-not-a-real-secret")

    settings = Settings(_env_file=None, **REQUIRED_SETTINGS)  # type: ignore[call-arg]

    assert settings.require_deepseek_key() == "standard-test-key-not-a-real-secret"


def test_whitespace_legacy_deepseek_key_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """WHITESPACE LEGACY KEY -> live boundary -> no provider request is attempted."""
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("DeepSeekAPI_KEY", "   ")
    settings = Settings(_env_file=None, **REQUIRED_SETTINGS)  # type: ignore[call-arg]

    with pytest.raises(RuntimeError):
        settings.require_deepseek_key()


# --------------------------------------------------------------------------
# R-9 — DEMO_MODE and AGENT_TRANSPORT are independent
# --------------------------------------------------------------------------


@pytest.mark.parametrize("demo_mode", [True, False])
@pytest.mark.parametrize("transport", [AgentTransport.LIVE, AgentTransport.REPLAY])
def test_every_combination_of_demo_mode_and_agent_transport_is_reachable(
    demo_mode: bool, transport: AgentTransport
) -> None:
    """EITHER FLAG SET EITHER WAY -> construct Settings -> both values are honoured.

    All four combinations must exist. If they ever collapse into one flag this
    parametrisation stops distinguishing them and the test below catches it.
    """
    settings = isolated(demo_mode=demo_mode, agent_transport=transport)
    assert settings.demo_mode is demo_mode
    assert settings.agent_transport is transport


def test_pinning_the_clock_does_not_force_the_replay_transport() -> None:
    """DEMO_MODE ON, TRANSPORT LIVE -> construct Settings -> both survive.

    This is the rehearsal configuration: a real DeepSeek call against the pinned
    demo world. It is the specific combination a single merged flag would make
    unreachable (docs/phase_review_findings.md R-9).
    """
    settings = isolated(demo_mode=True, agent_transport=AgentTransport.LIVE)
    assert settings.demo_mode is True
    assert settings.agent_transport is AgentTransport.LIVE


def test_selecting_the_replay_transport_does_not_force_the_demo_clock() -> None:
    """DEMO_MODE OFF, TRANSPORT REPLAY -> construct Settings -> both survive.

    The mirror image: deterministic fixtures against real wall-clock time, which
    is what a CI run wants.
    """
    settings = isolated(demo_mode=False, agent_transport=AgentTransport.REPLAY)
    assert settings.demo_mode is False
    assert settings.agent_transport is AgentTransport.REPLAY


def test_an_unrecognised_agent_transport_is_rejected_rather_than_defaulted() -> None:
    """AGENT_TRANSPORT=banana -> construct Settings -> ValidationError.

    Silently falling back to `replay` would let a run that was meant to be live
    quietly become a fixture replay, which AGENTS_FoodFlow.md 20 forbids
    presenting as live.
    """
    with pytest.raises(ValidationError):
        isolated(agent_transport="banana")


# --------------------------------------------------------------------------
# require_deepseek_key
# --------------------------------------------------------------------------


def test_requiring_the_key_when_it_is_empty_raises_rather_than_calling_deepseek() -> None:
    """EMPTY KEY -> require_deepseek_key() -> RuntimeError naming the replay escape hatch."""
    settings = isolated(deepseek_api_key="")
    with pytest.raises(RuntimeError) as raised:
        settings.require_deepseek_key()
    message = str(raised.value)
    assert "DEEPSEEK_API_KEY" in message
    assert "replay" in message.lower(), "the error must name the way out, not just the problem"


def test_requiring_the_key_when_it_is_set_returns_it() -> None:
    """KEY SET -> require_deepseek_key() -> the key is returned unchanged."""
    settings = isolated(deepseek_api_key="test-key-not-a-real-secret")
    assert settings.require_deepseek_key() == "test-key-not-a-real-secret"


def test_a_whitespace_only_key_is_not_accepted_as_a_key() -> None:
    """KEY OF SPACES -> require_deepseek_key() -> RuntimeError.

    A copy-paste that captured only whitespace must fail at the boundary rather
    than at the first live call, mid-demo.
    """
    settings = isolated(deepseek_api_key="   ")
    with pytest.raises(RuntimeError):
        settings.require_deepseek_key()


def test_no_settings_default_contains_a_credential_shaped_literal() -> None:
    """DEFAULTS -> inspect every string default -> no `sk-` literal.

    clean_code_spec 6.4: secrets never leave the config boundary, and a default
    committed into the module would be in the repository forever.
    """
    settings = isolated()
    for name, value in settings.model_dump().items():
        if isinstance(value, str):
            assert not value.startswith("sk-"), f"{name} carries a credential-shaped default"


# --------------------------------------------------------------------------
# get_settings
# --------------------------------------------------------------------------


def test_get_settings_returns_one_cached_instance(monkeypatch: pytest.MonkeyPatch) -> None:
    """CALLED TWICE -> get_settings() -> the same object both times."""
    for name, value in REQUIRED_SETTINGS.items():
        monkeypatch.setenv(name.upper(), str(value))
    get_settings.cache_clear()
    assert get_settings() is get_settings()


# --------------------------------------------------------------------------
# The boundary itself
# --------------------------------------------------------------------------


def test_config_module_is_the_only_backend_module_that_reads_the_environment() -> None:
    """BACKEND APP -> scan for os.environ / os.getenv -> only config.py.

    clean_code_spec 6.4. A stray `os.getenv("DEEPSEEK_API_KEY")` in an adapter
    is how a secret reaches a log line.
    """
    allowed = {APP_ROOT / "config.py"}
    offenders: list[str] = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        if path in allowed or "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in {"environ", "getenv"}:
                offenders.append(f"{path.relative_to(PROJECT_ROOT)}:{node.lineno} os.{node.attr}")
            elif isinstance(node, ast.Name) and node.id == "getenv":
                offenders.append(f"{path.relative_to(PROJECT_ROOT)}:{node.lineno} getenv")
    assert offenders == [], (
        "only backend/app/config.py may read the environment (clean_code_spec 6.4):\n"
        + "\n".join(offenders)
    )
