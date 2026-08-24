from __future__ import annotations

import time
import uuid
from typing import Any

from pydantic import BaseModel, Field


def now_ms() -> int:
    return int(time.time() * 1000)


class Event(BaseModel):
    type: str
    ts: int = Field(default_factory=now_ms)
    component: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class TraceRecorder:
    def __init__(self, run_id: str | None = None):
        self.run_id = run_id or uuid.uuid4().hex[:12]
        self.events: list[Event] = []

    def emit(self, type: str, component: str | None = None, **data: Any) -> Event:
        ev = Event(type=type, component=component, data=data)
        self.events.append(ev)
        return ev

    def as_dicts(self) -> list[dict[str, Any]]:
        return [e.model_dump() for e in self.events]