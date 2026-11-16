"""A scripted stand-in for the Claude API client, built from real SDK message types."""

import json
from collections.abc import Callable
from typing import Any

from anthropic.types.beta import BetaMessage

Reply = Callable[[list[dict[str, Any]]], BetaMessage]


def message(content: list[dict[str, Any]], stop_reason: str = "end_turn") -> BetaMessage:
    return BetaMessage.model_validate(
        {
            "id": "msg_test",
            "type": "message",
            "role": "assistant",
            "model": "claude-opus-5-5",
            "content": [{"type": "thinking", "thinking": "", "signature": "sig"}, *content],
            "stop_reason": stop_reason,
            "stop_sequence": None,
            "usage": {"input_tokens": 100, "output_tokens": 20},
        }
    )


def text(answer: str) -> BetaMessage:
    return message([{"type": "text", "text": answer}])


def tool_call(name: str, arguments: dict[str, Any], call_id: str = "toolu_1") -> BetaMessage:
    return message(
        [{"type": "tool_use", "id": call_id, "name": name, "input": arguments}], "tool_use"
    )


def last_tool_result(messages: list[dict[str, Any]]) -> dict[str, Any]:
    block = messages[-1]["content"][0]
    assert block["type"] == "tool_result"
    return block


def tool_output(messages: list[dict[str, Any]]) -> Any:
    return json.loads(last_tool_result(messages)["content"])


class FakeClient:
    """Answers each request with the next scripted reply (a message or a function of the
    messages sent), and records every request."""

    def __init__(self, *replies: BetaMessage | Reply | Exception) -> None:
        self.replies = list(replies)
        self.requests: list[dict[str, Any]] = []

    async def create(self, **request: Any) -> BetaMessage:
        self.requests.append(json.loads(json.dumps(request)))  # a frozen copy
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        if callable(reply):
            return reply(request["messages"])
        return reply
