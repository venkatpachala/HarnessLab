"""Deterministic scripted model so experiments run without API keys.

The mock is *not* a harness. It is a stand-in brain so we can test the
platform. Real providers plug in behind the same ModelClient interface.
"""

from __future__ import annotations

import json
import re
from typing import Any

from harnesslab.models.base import ModelClient, ModelResponse, ToolCall


class MockScriptModel(ModelClient):
    """Very small policy: follow a few CommerceWorld patterns from the last user text."""

    name = "mock-deterministic"

    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> ModelResponse:
        user = _last_user(messages)
        observations = [m.get("content") or "" for m in messages if m.get("role") == "tool"]
        text = user.lower()

        # After tools, decide next action / finish.
        if any(
            "ineligible" in (o or "").lower() or "not_delivered" in (o or "").lower()
            for o in observations
        ):
            return ModelResponse(
                content="Cannot refund: order is not eligible.",
                input_tokens=_tok(messages),
                output_tokens=12,
            )

        called = _called_tools(messages)

        if "alice" in text and "email" in text and "search_customers" not in called:
            return _tools(
                [ToolCall(name="search_customers", arguments={"query": "Alice"})],
                messages,
            )

        if "c_alice" in text and "list all orders" in text and "list_orders" not in called:
            return _tools(
                [ToolCall(name="list_orders", arguments={"customer_id": "c_alice"})],
                messages,
            )

        if "o_200" in text and "refund" in text:
            if "check_refund_eligibility" not in called:
                return _tools(
                    [
                        ToolCall(
                            name="check_refund_eligibility",
                            arguments={"order_id": "o_200"},
                        )
                    ],
                    messages,
                )
            return ModelResponse(
                content="Order o_200 is processing; refusing refund per policy.",
                input_tokens=_tok(messages),
                output_tokens=16,
            )

        wants_refund = "refund" in text
        wants_policy = "policy" in text
        wants_ticket = "ticket" in text or "t_1" in text

        if wants_policy and "search_policy" not in called:
            return _tools(
                [ToolCall(name="search_policy", arguments={"query": "refund"})],
                messages,
            )

        if wants_refund and "check_refund_eligibility" not in called:
            return _tools(
                [
                    ToolCall(
                        name="check_refund_eligibility",
                        arguments={"order_id": "o_101"},
                    )
                ],
                messages,
            )

        if wants_refund and "refund_payment" not in called:
            return _tools(
                [ToolCall(name="refund_payment", arguments={"order_id": "o_101"})],
                messages,
            )

        if wants_ticket and "update_ticket" not in called:
            return _tools(
                [
                    ToolCall(
                        name="update_ticket",
                        arguments={"ticket_id": "t_1", "status": "resolved"},
                    )
                ],
                messages,
            )

        return ModelResponse(
            content="Done.",
            input_tokens=_tok(messages),
            output_tokens=4,
        )


def _tools(calls: list[ToolCall], messages: list[dict[str, Any]]) -> ModelResponse:
    return ModelResponse(
        content="",
        tool_calls=calls,
        input_tokens=_tok(messages),
        output_tokens=20,
    )


def _last_user(messages: list[dict[str, Any]]) -> str:
    for m in reversed(messages):
        if m.get("role") == "user":
            return str(m.get("content") or "")
    return ""


def _called_tools(messages: list[dict[str, Any]]) -> set[str]:
    names: set[str] = set()
    for m in messages:
        if m.get("role") != "assistant":
            continue
        raw = m.get("content") or ""
        if raw.startswith("TOOLCALLS:"):
            try:
                for c in json.loads(raw.split("TOOLCALLS:", 1)[1]):
                    names.add(c["name"])
            except Exception:
                pass
        for name in re.findall(r"tool_call:(\w+)", raw):
            names.add(name)
    for m in messages:
        if m.get("role") == "tool" and m.get("name"):
            names.add(m["name"])
    return names


def _tok(messages: list[dict[str, Any]]) -> int:
    return max(1, sum(len(str(m.get("content") or "")) // 4 for m in messages))