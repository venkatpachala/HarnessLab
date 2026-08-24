from __future__ import annotations

import json
from pathlib import Path
import pytest

from harnesslab.core.config import load_experiment
from harnesslab.core.runner import run_experiment
from harnesslab.tasks.loader import load_tasks


def test_load_tasks():
    tasks = load_tasks()
    assert len(tasks) == 6
    task_ids = [t.id for t in tasks]
    expected = [
        "lookup_alice",
        "list_alice_orders",
        "refund_alice_latest",
        "do_not_refund_processing",
        "policy_then_refund",
        "close_ticket_after_refund",
    ]
    assert task_ids == expected


def test_h0_smoke_experiment(tmp_path: Path):
    config_path = Path(__file__).resolve().parent.parent / "experiments" / "h0_smoke.yaml"
    cfg = load_experiment(config_path)
    
    payload = run_experiment(cfg, output_dir=tmp_path)
    
    assert payload["n_runs"] == 6
    exp_dir = tmp_path / cfg.name
    assert (exp_dir / "summary.json").exists()
    
    summary_data = json.loads((exp_dir / "summary.json").read_text())
    assert summary_data["n_runs"] == 6
    
    rows = summary_data["rows"]
    assert len(rows) == 6
    
    # Check specific task results
    by_task = {r["task_id"]: r for r in rows}
    
    # Check do_not_refund_processing task
    assert "do_not_refund_processing" in by_task
    dnr = by_task["do_not_refund_processing"]
    assert dnr["success"] is True
    assert len(dnr["safety_violations"]) == 0
    
    # Check refund_alice_latest task
    assert "refund_alice_latest" in by_task
    ral = by_task["refund_alice_latest"]
    assert ral["success"] is True
    
    # Verify per-run detail JSON
    run_id = ral["run_id"]
    run_file = exp_dir / f"{run_id}.json"
    assert run_file.exists()
    run_data = json.loads(run_file.read_text())
    assert "result" in run_data
    assert "eval" in run_data
    assert run_data["eval"]["success"] is True
    assert run_data["result"]["final_state"]["orders"]["o_101"]["status"] == "refunded"
