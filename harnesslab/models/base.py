from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ModelResponse(BaseModel):
    content: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    raw: dict[str, Any] = Field(default_factory=dict)


class ModelClient(ABC):
    name: str = "base"

    @abstractmethod
    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None) -> ModelResponse:
        ...