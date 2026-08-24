"""OpenAI-compatible chat + tools adapter.

Works with:
  - OpenAI
  - Azure OpenAI (via base_url)
  - Ollama OpenAI endpoint (http://localhost:11434/v1)
  - Most OpenAI-compatible proxies (OpenRouter, vLLM, etc.)

Not a harness — only the model brain behind ModelClient.
"""

from __future__ import annotations

import json
import os
from typing import Any

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from harnesslab.models.base import ModelClient, ModelResponse, ToolCall


class OpenAICompatModel(ModelClient):
    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None,
        temperature: float = 0.0,
        timeout_s: float = 120.0,
    ):
        self.model = model
        self.name = model
        self.temperature = temperature
        self.timeout_s = timeout_s
        self.api_key = (
            api_key
            or os.environ.get("OPENAI_API_KEY")
            or os.environ.get("HARNESSLAB_API_KEY")
            or os.environ.get("OLLAMA_API_KEY")
            or "ollama"
        )
        self.base_url = (
            base_url
            or os.environ.get("OPENAI_BASE_URL")
            or os.environ.get("HARNESSLAB_BASE_URL")
            or None
        )
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI
        except ImportError as e:
            raise ImportError(
                "openai package required for real models. Run: uv pip install openai"
            ) from e
        kwargs: dict[str, Any] = {"api_key": self.api_key, "timeout": self.timeout_s}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        self._client = OpenAI(**kwargs)
        return self._client

    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> ModelResponse:
        client = self._get_client()
        oai_messages = _to_openai_messages(messages)
        oai_tools = _to_openai_tools(tools) if tools else None

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": oai_messages,
            "temperature": self.temperature,
        }
        if oai_tools:
            kwargs["tools"] = oai_tools
            kwargs["tool_choice"] = "auto"

        resp = client.chat.completions.create(**kwargs)
        choice = resp.choices[0].message
        usage = resp.usage

        tool_calls: list[ToolCall] = []
        if choice.tool_calls:
            for tc in choice.tool_calls:
                args: dict[str, Any]
                raw_args = tc.function.arguments or "{}"
                try:
                    args = json.loads(raw_args)
                    if not isinstance(args, dict):
                        args = {"value": args}
                except json.JSONDecodeError:
                    args = {"_raw": raw_args}
                tool_calls.append(ToolCall(name=tc.function.name, arguments=args))

        return ModelResponse(
            content=(choice.content or "") if not tool_calls else (choice.content or ""),
            tool_calls=tool_calls,
            input_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
            raw={"id": getattr(resp, "id", None), "model": getattr(resp, "model", None)},
        )


def _to_openai_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for t in tools:
        params = t.get("parameters") or {}
        # Our ToolSpec uses {name: {type: string}}; OpenAI wants JSON Schema object
        if params and "type" not in params:
            props = {}
            required = []
            for key, schema in params.items():
                if isinstance(schema, dict):
                    props[key] = schema
                else:
                    props[key] = {"type": "string"}
                required.append(key)
            params = {"type": "object", "properties": props, "required": required}
        out.append(
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description") or "",
                    "parameters": params or {"type": "object", "properties": {}},
                },
            }
        )
    return out


def _to_openai_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert DirectHarness transcript → OpenAI tool-calling messages."""
    out: list[dict[str, Any]] = []
    pending_tool_ids: list[str] = []
    tool_counter = 0

    for m in messages:
        role = m.get("role")
        content = m.get("content") or ""

        if role == "system":
            out.append({"role": "system", "content": content})
            continue

        if role == "user":
            out.append({"role": "user", "content": content})
            continue

        if role == "assistant":
            if content.startswith("TOOLCALLS:"):
                try:
                    calls = json.loads(content.split("TOOLCALLS:", 1)[1])
                except json.JSONDecodeError:
                    out.append({"role": "assistant", "content": content})
                    continue
                tool_calls = []
                pending_tool_ids = []
                for c in calls:
                    tool_counter += 1
                    tid = f"call_{tool_counter}"
                    pending_tool_ids.append(tid)
                    tool_calls.append(
                        {
                            "id": tid,
                            "type": "function",
                            "function": {
                                "name": c["name"],
                                "arguments": json.dumps(c.get("arguments") or {}),
                            },
                        }
                    )
                out.append({"role": "assistant", "content": None, "tool_calls": tool_calls})
            else:
                out.append({"role": "assistant", "content": content})
            continue

        if role == "tool":
            tid = pending_tool_ids.pop(0) if pending_tool_ids else f"call_{tool_counter}"
            out.append(
                {
                    "role": "tool",
                    "tool_call_id": tid,
                    "content": content if isinstance(content, str) else json.dumps(content),
                }
            )
            continue

        # fallback
        out.append({"role": "user", "content": str(content)})

    return out
