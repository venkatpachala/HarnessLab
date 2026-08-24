from __future__ import annotations

from pathlib import Path

import yaml

from harnesslab.tasks.schema import Task

DEFAULT_DIR = Path(__file__).resolve().parent / "commerce"


def load_tasks(path: str | Path | None = None) -> list[Task]:
    root = Path(path) if path else DEFAULT_DIR
    tasks: list[Task] = []
    files = [root] if root.is_file() else sorted(root.glob("*.yaml")) + sorted(root.glob("*.yml"))
    for f in files:
        data = yaml.safe_load(f.read_text()) or []
        if isinstance(data, dict) and "tasks" in data:
            data = data["tasks"]
        if isinstance(data, dict):
            data = [data]
        for item in data:
            tasks.append(Task.model_validate(item))
    return tasks


def select_tasks(tasks: list[Task], ids: list[str] | None = None, levels: list[int] | None = None) -> list[Task]:
    out = tasks
    if ids:
        want = set(ids)
        out = [t for t in out if t.id in want]
    if levels:
        lv = set(levels)
        out = [t for t in out if t.level in lv]
    return out