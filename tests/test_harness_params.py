from harnesslab.harness import get_harness
from harnesslab.harness.recovery import RecoveryHarness


def test_recovery_reads_max_retries():
    h = get_harness("recovery", {"max_retries": 4})
    assert isinstance(h, RecoveryHarness)
    assert h.max_retries == 4


def test_direct_ignores_unknown_params():
    h = get_harness("direct", {"max_retries": 9})
    assert h.name == "direct"