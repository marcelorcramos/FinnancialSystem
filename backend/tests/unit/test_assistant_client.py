"""The request the real client sends to the Claude API (caught by a mock transport)."""

import json
from typing import Any

import anthropic
import httpx2

from app.core.assistant_client import FALLBACK_BETA, ClaudeClient


async def test_the_request_names_the_model_effort_and_refusal_fallback() -> None:
    sent: list[httpx2.Request] = []

    def handle(request: httpx2.Request) -> httpx2.Response:
        sent.append(request)
        return httpx2.Response(
            200,
            json={
                "id": "msg_1",
                "type": "message",
                "role": "assistant",
                "model": "claude-opus-5-5",
                "content": [{"type": "text", "text": "{}"}],
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {"input_tokens": 1, "output_tokens": 1},
            },
        )

    client = ClaudeClient(
        "test-key",
        http_client=anthropic.DefaultAsyncHttpxClient(transport=httpx2.MockTransport(handle)),
    )
    schema: dict[str, Any] = {"type": "json_schema", "schema": {"type": "object"}}
    message = await client.create(
        system="sys",
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=100,
        output_format=schema,
    )
    assert message.content[0].type == "text"

    [request] = sent
    body = json.loads(request.content)
    assert request.url.path == "/v1/messages"
    assert request.headers["authorization"] == "Bearer test-key"
    assert FALLBACK_BETA in request.headers["anthropic-beta"]
    assert body["model"] == "claude-opus-5-5"
    assert body["fallbacks"] == "default"
    assert body["output_config"] == {"effort": "low", "format": schema}
    assert "tools" not in body
    assert "thinking" not in body  # Opus 5.5 thinks adaptively by default
