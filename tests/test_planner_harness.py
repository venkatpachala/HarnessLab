from harnesslab.core.types import Budget
from harnesslab.environment.commerce.world import CommerceWorld
from harnesslab.harness.planner import PlannerHarness
from harnesslab.models.mock import MockScriptModel
from harnesslab.tasks.loader import load_tasks


def test_planner_emits_plan_and_can_refund():
    tasks = {t.id: t for t in load_tasks()}
    task = tasks["refund_alice_latest"]
    env = CommerceWorld(fixture=task.fixture)
    harness = PlannerHarness()
    result = harness.run(task, env, MockScriptModel(), Budget(max_steps=12), seed=0)

    types = [e["type"] for e in result.events]
    assert "plan_created" in types
    assert result.extra.get("plan")
    assert result.final_state["orders"]["o_101"]["status"] == "refunded"