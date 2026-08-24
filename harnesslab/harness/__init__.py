from harnesslab.harness.base import Harness
from harnesslab.harness.direct import DirectHarness

HARNESSES = {"direct": DirectHarness, "h0": DirectHarness}


def get_harness(name: str) -> Harness:
    key = name.lower()
    if key not in HARNESSES:
        raise KeyError(f"Unknown harness {name}. Have {list(HARNESSES)}")
    return HARNESSES[key]()