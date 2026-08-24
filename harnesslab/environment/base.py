from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class ToolError(Exception):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def to_result(self) -> "ToolResult":
        return ToolResult(ok=False, code=self.code, error=self.message, data=self.details)


class ToolResult(BaseModel):
    ok: bool = True
    code: str = "ok"
    data: Any = None
    error: str | None = None


class ToolSpec(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    permission: str | None = None


class Environment(ABC):
    name: str = "base"

    @abstractmethod
    def reset(self, fixture: str | None = None) -> dict[str, Any]: ...

    @abstractmethod
    def snapshot(self) -> dict[str, Any]: ...

    @abstractmethod
    def restore(self, snap: dict[str, Any]) -> None: ...

    @abstractmethod
    def get_state(self) -> dict[str, Any]: ...

    @abstractmethod
    def list_tools(self) -> list[ToolSpec]: ...

    @abstractmethod
    def call_tool(self, name: str, arguments: dict[str, Any]) -> ToolResult: ...

    def diff(self, before: dict[str, Any], after: dict[str, Any] | None = None) -> dict[str, Any]:
        after = after if after is not None else self.get_state()
        return compute_diff(before, after)


def compute_diff(before: Any, after: Any, path: str = "") -> dict[str, Any]:
    changes: dict[str, Any] = {}
    if type(before) is not type(after):
        changes[path or "$"] = {"from": before, "to": after}
        return changes
    if isinstance(before, dict):
        keys = set(before) | set(after)
        for k in sorted(keys):
            p = f"{path}.{k}" if path else str(k)
            if k not in before:
                changes[p] = {"from": None, "to": after[k]}
            elif k not in after:
                changes[p] = {"from": before[k], "to": None}
            else:
                changes.update(compute_diff(before[k], after[k], p))
        return changes
    if isinstance(before, list):
        if before != after:
            changes[path or "$"] = {"from": before, "to": after}
        return changes
    if before != after:
        changes[path or "$"] = {"from": before, "to": after}
    return changes