from __future__ import annotations

import json
from pathlib import Path

from harnesslab.core.config import ExperimentConfig, ModelConfig
from harnesslab.core.types import ExecutionResult
from harnesslab.environment.commerce.world import CommerceWorld
from harnesslab.evaluation.outcome import EvalReport, evaluate_run
from harnesslab.harness import get_harness
from harnesslab.models.mock import MockScriptModel
from harnesslab.models.openai_compat import OpenAICompatModel
from harnesslab.tasks.loader import load_tasks, select_tasks


def build_model(provider: str, name: str, cfg: ModelConfig | None = None):
    """Build a ModelClient. cfg carries temperature / base_url / api_key when present."""
    provider = (provider or "mock").lower()
    if provider in {"mock", "none"} or name.startswith("mock"):
        return MockScriptModel()

    if provider in {
        "openai",
        "openai_compat",
        "ollama",
        "openrouter",
        "vllm",
        "azure",
    }:
        base_url = cfg.base_url if cfg else None
        if provider == "ollama" and not base_url:
            base_url = "http://localhost:11434/v1"
        if provider == "openrouter" and not base_url:
            base_url = "https://openrouter.ai/api/v1"
        api_key = cfg.api_key if cfg else None
        if provider == "openrouter" and not api_key:
            import os

            api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
        return OpenAICompatModel(
            model=name,
            api_key=api_key,
            base_url=base_url,
            temperature=(cfg.temperature if cfg else 0.0),
            timeout_s=(cfg.timeout_s if cfg else 120.0),
        )

    raise NotImplementedError(
        f"Provider {provider}/{name} not supported. "
        f"Use mock | openai | ollama | openrouter | openai_compat"
    )


def run_once(
    cfg: ExperimentConfig,
    task,
    harness_name: str,
    model,
    seed: int,
    harness_params: dict | None = None,
) -> tuple[ExecutionResult, EvalReport]:
    env = CommerceWorld(
        fixture=task.fixture or cfg.environment.fixture or "baseline_001",
        permissions=cfg.environment.permissions or None,
        faults=cfg.environment.faults or None,
        rng_seed=seed,
    )
    before = env.get_state()
    harness = get_harness(harness_name, harness_params)
    result = harness.run(task, env, model, cfg.budget, seed=seed)
    result.experiment = cfg.name
    report = evaluate_run(task, result, initial_state=before)
    result.success = report.success
    return result, report


def run_experiment(cfg: ExperimentConfig, output_dir: str | Path | None = None) -> dict:
    tasks = select_tasks(
        load_tasks(),
        ids=cfg.tasks.ids,
        levels=cfg.tasks.levels,
    )
    if not tasks:
        raise RuntimeError("No tasks selected")

    harnesses = cfg.harnesses or [cfg.harness]
    models = cfg.models or [cfg.model]

    out = Path(output_dir or cfg.output_dir) / cfg.name
    out.mkdir(parents=True, exist_ok=True)

    rows = []
    n = 0
    for mcfg in models:
        model = build_model(mcfg.provider, mcfg.name, mcfg)
        for hcfg in harnesses:
            for task in tasks:
                for r in range(cfg.repetitions):
                    seed = cfg.seed + r
                    result, report = run_once(
                        cfg, task, hcfg.name, model, seed, harness_params=hcfg.params
                    )
                    n += 1
                    rec = {
                        "run_id": result.run_id,
                        "experiment": cfg.name,
                        "model": model.name,
                        "harness": hcfg.name,
                        "task_id": task.id,
                        "level": task.level,
                        "rep": r,
                        "success": report.success,
                        "stop_reason": result.stop_reason.value,
                        "steps": result.usage.steps,
                        "tool_calls": result.usage.tool_calls,
                        "tokens": result.usage.input_tokens + result.usage.output_tokens,
                        "latency_s": round(result.usage.latency_s, 4),
                        "safety_violations": report.safety_violations,
                        "missing_required_tools": report.missing_required_tools,
                    }
                    rows.append(rec)
                    (out / f"{result.run_id}.json").write_text(
                        json.dumps(
                            {
                                "result": result.model_dump(),
                                "eval": report.model_dump(),
                            },
                            default=str,
                            indent=2,
                        )
                    )

    summary = _summarize(rows)
    payload = {
        "experiment": cfg.model_dump(),
        "n_runs": n,
        "rows": rows,
        "summary": summary,
    }
    (out / "summary.json").write_text(json.dumps(payload, indent=2, default=str))
    return payload


def _summarize(rows: list[dict]) -> list[dict]:
    groups: dict[tuple, list] = {}
    for row in rows:
        key = (row["model"], row["harness"])
        groups.setdefault(key, []).append(row)
    out = []
    for (model, harness), rs in sorted(groups.items()):
        succ = [r for r in rs if r["success"]]
        out.append(
            {
                "model": model,
                "harness": harness,
                "n": len(rs),
                "success_rate": round(len(succ) / len(rs), 4) if rs else 0,
                "avg_steps": round(sum(r["steps"] for r in rs) / len(rs), 3),
                "avg_tool_calls": round(sum(r["tool_calls"] for r in rs) / len(rs), 3),
                "avg_tokens": round(sum(r["tokens"] for r in rs) / len(rs), 1),
                "avg_latency_s": round(sum(r["latency_s"] for r in rs) / len(rs), 4),
                "safety_violation_runs": sum(1 for r in rs if r["safety_violations"]),
            }
        )
    return out