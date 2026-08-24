from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from harnesslab.core.config import load_experiment
from harnesslab.core.runner import run_experiment


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="harnesslab", description="HarnessLab experiment runner"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="Run an experiment YAML")
    p_run.add_argument("config", type=Path)
    p_run.add_argument("--out", type=Path, default=None)

    p_cmp = sub.add_parser(
        "compare", help="Print summary table from a completed run dir or yaml"
    )
    p_cmp.add_argument("path", type=Path)

    args = parser.parse_args(argv)

    if args.cmd == "run":
        cfg = load_experiment(args.config)
        payload = run_experiment(cfg, output_dir=args.out)
        _print_table(payload["summary"], payload["n_runs"], cfg.name)
        print(f"\nWrote {Path(cfg.output_dir) / cfg.name / 'summary.json'}")
        return 0

    if args.cmd == "compare":
        path = args.path
        if path.suffix in {".yaml", ".yml"}:
            cfg = load_experiment(path)
            summary_path = Path(cfg.output_dir) / cfg.name / "summary.json"
        else:
            summary_path = path / "summary.json" if path.is_dir() else path
        payload = json.loads(summary_path.read_text())
        _print_table(
            payload["summary"],
            payload.get("n_runs", 0),
            payload.get("experiment", {}).get("name", ""),
        )
        return 0

    return 1


def _print_table(summary: list[dict], n: int, name: str) -> None:
    print(f"\nExperiment: {name}   runs: {n}\n")
    hdr = (
        f"{'model':<22} {'harness':<14} {'n':>4} {'success':>8} "
        f"{'steps':>7} {'tools':>7} {'tokens':>8} {'viol':>6}"
    )
    print(hdr)
    print("-" * len(hdr))
    for row in summary:
        print(
            f"{row['model']:<22} {row['harness']:<14} {row['n']:>4} "
            f"{row['success_rate']:>7.1%} {row['avg_steps']:>7.2f} "
            f"{row['avg_tool_calls']:>7.2f} {row['avg_tokens']:>8.0f} "
            f"{row['safety_violation_runs']:>6}"
        )


if __name__ == "__main__":
    sys.exit(main())