"""DeepSeek-specific LiteLLM boundary.

Thinking is disabled at request construction and any unexpected provider
reasoning payload is removed here before ADK can observe or retain it.
"""

from __future__ import annotations

from typing import Any

from google.adk.models.lite_llm import LiteLLMClient
from pydantic import BaseModel


def sanitize_provider_response(value: Any) -> Any:
    """Return a structurally equivalent value without hidden reasoning fields."""
    if isinstance(value, dict):
        return {
            key: sanitize_provider_response(nested)
            for key, nested in value.items()
            if key != "reasoning_content"
        }
    if isinstance(value, list):
        return [sanitize_provider_response(item) for item in value]
    if isinstance(value, tuple):
        return tuple(sanitize_provider_response(item) for item in value)
    if isinstance(value, BaseModel):
        updates = {
            name: sanitize_provider_response(getattr(value, name))
            for name in type(value).model_fields
            if name != "reasoning_content"
        }
        if "reasoning_content" in type(value).model_fields:
            updates["reasoning_content"] = None
        return value.model_copy(update=updates)
    return value


class SanitizingLiteLlmClient(LiteLLMClient):
    """Ensure provider-only reasoning cannot cross the model boundary."""

    async def acompletion(
        self,
        model: Any,
        messages: Any,
        tools: Any,
        **kwargs: Any,
    ) -> Any:
        response = await super().acompletion(
            model=model,
            messages=messages,
            tools=tools,
            **kwargs,
        )
        return sanitize_provider_response(response)
