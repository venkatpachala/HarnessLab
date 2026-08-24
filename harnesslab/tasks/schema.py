from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class StateAssertion(BaseModel):
    path: str
    equals: Any = None
    exists: bool | None = None


class TaskSuccess(BaseModel):
    state: list[StateAssertion] = Field(default_factory=list)
    required_tools: list[str] = Field(default_factory=list)


class TaskSafety(BaseModel):
    forbidden_tools: list[str] = Field(default_factory=list)
    forbid_refund_if_ineligible: bool = True


class Task(BaseModel):
    id: str
    level: int = 1
    objective: str
    user_message: str | None = None
    constraints: list[str] = Field(default_factory=list)
    fixture: str = "baseline_001"
    allowed_tools: list[str] | None = None
    success: TaskSuccess = Field(default_factory=TaskSuccess)
    safety: TaskSafety = Field(default_factory=TaskSafety)
    tags: list[str] = Field(default_factory=list)

    def prompt(self) -> str:
        text = self.user_message or self.objective
        if self.constraints:
            text += "\n\nConstraints:\n" + "\n".join(f"- {c}" for c in self.constraints)
        return text