from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class StopReason(str, Enum):
    COMPLETED = "completed"
    BUDGET_STEPS = "budget_steps"
    BUDGET_TOKENS = "budget_tokens"
    BUDGET_COST = "budget_cost"
    ERROR = "error"
    REFUSED = "refused"


class Budget(BaseModel):
    max_steps: int = 20
    max_tokens: int = 20_000
    max_cost_usd: float = 1.0
    max_seconds: float = 120.0


class Usage(BaseModel):
    steps: int = 0
    model_calls: int = 0
    tool_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_s: float = 0.0


class ExecutionResult(BaseModel):
    run_id: str
    experiment: str | None = None
    harness: str
    model: str
    task_id: str
    seed: int = 0
    stop_reason: StopReason = StopReason.COMPLETED
    success: bool | None = None
    usage: Usage = Field(default_factory=Usage)
    final_state: dict[str, Any] = Field(default_factory=dict)
    events: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)