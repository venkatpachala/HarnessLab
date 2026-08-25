from __future__ import annotations

import inspect
from typing import Any

from harnesslab.harness.base import Harness
from harnesslab.harness.direct import DirectHarness
from harnesslab.harness.planner import PlannerHarness
from harnesslab.harness.recovery import RecoveryHarness

HARNESSES: dict[str, type[Harness]] = {
    "direct": DirectHarness,
    "h0": DirectHarness,
    "planner": PlannerHarness,
    "h1": PlannerHarness,
    "recovery": RecoveryHarness,
    "h3": RecoveryHarness,
}


def get_harness(name: str, params: dict[str, Any] | None = None) -> Harness:
    key = name.lower()
    if key not in HARNESSES:
        raise KeyError(f"Unknown harness {name}. Have {list(HARNESSES)}")
    cls = HARNESSES[key]
    raw = dict(params or {})
    sig = inspect.signature(cls.__init__)
    allowed = {k: v for k, v in raw.items() if k in sig.parameters and k != "self"}
    return cls(**allowed)