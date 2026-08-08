"""Construct the single supported live model with fixed safe parameters."""

from __future__ import annotations

from google.adk.models.lite_llm import LiteLlm

from backend.app.config import Settings
from backend.app.infrastructure.deepseek_adapter import SanitizingLiteLlmClient

THINKING_DISABLED = {"thinking": {"type": "disabled"}}


def build_deepseek_model(settings: Settings) -> LiteLlm:
    """Build DeepSeek through ADK without exposing configuration or secrets."""
    return LiteLlm(
        model=f"openai/{settings.deepseek_model}",
        api_key=settings.require_deepseek_key(),
        api_base=settings.deepseek_base_url,
        temperature=0,
        extra_body=THINKING_DISABLED,
        llm_client=SanitizingLiteLlmClient(),
    )
