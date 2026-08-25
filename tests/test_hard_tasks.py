
"""Validate hard tasks load and oracles point at real fixture paths."""

from __future__ import annotations

from harnesslab.environment.commerce.fixtures import get_fixture
from harnesslab.evaluation.outcome import _get_path
from harnesslab.tasks.loader import load_tasks


def test_hard_tasks_load():
    hard = [
        t
        for t in load_tasks()
        if t.fixture == "hard_001" or t.id.endswith("baseline") or "hard" in t.tags
    ]
    assert len(hard) >= 20, len(hard)


def test_oracle_paths_exist_on_fixture():
    tasks = load_tasks()
    for t in tasks:
        state = get_fixture(t.fixture)
        for ass in t.success.state:
            if ass.exists is False:
                continue
            val = _get_path(state, ass.path)
            if val is None:
                assert "create_ticket" in t.success.required_tools, (
                    f"{t.id}: missing fixture path {ass.path}"
                )


def test_hard_fixture_has_traps():
    s = get_fixture("hard_001")
    assert s["customers"]["c_alicia"]["name"] == "Alicia Cheng"
    assert s["orders"]["o_102"]["status"] == "cancelled"
    assert s["orders"]["o_103"]["status"] == "refunded"
    assert s["orders"]["o_300"]["customer_id"] == "c_alicia"
    assert s["tickets"]["t_2"]["customer_id"] == "c_bob"