"""The connection to the Claude API, behind a small interface so tests use a fake.

Every request goes through here: the model, the timeout, effort and the
server-side fallback on refusals are set in one place.
"""

from functools import lru_cache
from typing import Any, Protocol, cast

import anthropic
from anthropic import omit
from anthropic.types.beta import BetaMessage

from app.core.config import settings

# A model refusal is re-run on a fallback model chosen by the API, in the same call.
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class AssistantClient(Protocol):
    async def create(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        max_tokens: int,
        tools: list[dict[str, Any]] | None = None,
        output_format: dict[str, Any] | None = None,
    ) -> BetaMessage: ...


class ClaudeClient:
    def __init__(self, api_key: str, http_client: Any = None) -> None:
        self._client = anthropic.AsyncAnthropic(
            api_key=api_key,
            timeout=settings.ASSISTANT_TIMEOUT_SECONDS,
            max_retries=2,
            http_client=http_client,
        )

    async def create(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        max_tokens: int,
        tools: list[dict[str, Any]] | None = None,
        output_format: dict[str, Any] | None = None,
    ) -> BetaMessage:
        # Reading reports and answering in a few sentences: low effort holds up.
        output_config: dict[str, Any] = {"effort": "low"}
        if output_format is not None:
            output_config["format"] = output_format
        return await self._client.beta.messages.create(
            model=settings.ASSISTANT_MODEL,
            betas=[FALLBACK_BETA],
            fallbacks="default",
            max_tokens=max_tokens,
            system=system,
            messages=cast(Any, messages),
            tools=cast(Any, tools) if tools else omit,
            output_config=cast(Any, output_config),
        )


@lru_cache
def get_assistant_client() -> AssistantClient | None:
    """The client, or None while the assistant is not set up (no API key)."""
    if not settings.ANTHROPIC_API_KEY:
        return None
    return ClaudeClient(settings.ANTHROPIC_API_KEY)
