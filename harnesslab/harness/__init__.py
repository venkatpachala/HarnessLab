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


def get_harness(name: str) -> Harness:
    key = name.lower()
    if key not in HARNESSES:
        raise KeyError(f"Unknown harness {name}. Have {list(HARNESSES)}")
    return HARNESSES[key]()