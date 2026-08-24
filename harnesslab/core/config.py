from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from harnesslab.core.types import Budget


class ModelConfig(BaseModel):
    provider: str = "mock"
    name: str = "mock-deterministic"
    temperature: float = 0.0
    input_cost_per_1k: float = 0.0
    output_cost_per_1k: float = 0.0
    api_key: str | None = None
    base_url: str | None = None
    timeout_s: float = 120.0


class EnvConfig(BaseModel):
    name: str = "commerce_world"
    version: str = "0.1"
    fixture: str | None = None
    permissions: dict[str, bool] = Field(default_factory=dict)
    faults: list[dict[str, Any]] = Field(default_factory=list)


class HarnessConfig(BaseModel):
    name: str = "direct"
    version: str = "0.1"
    params: dict[str, Any] = Field(default_factory=dict)


class TaskSetConfig(BaseModel):
    dataset: str = "commerce_v1"
    version: str = "1"
    ids: list[str] | None = None
    levels: list[int] | None = None


class EvaluationConfig(BaseModel):
    version: str = "0.1"
    use_llm_judge: bool = False


class ExperimentConfig(BaseModel):
    name: str
    model: ModelConfig = Field(default_factory=ModelConfig)
    models: list[ModelConfig] | None = None
    environment: EnvConfig = Field(default_factory=EnvConfig)
    harness: HarnessConfig = Field(default_factory=HarnessConfig)
    harnesses: list[HarnessConfig] | None = None
    tasks: TaskSetConfig = Field(default_factory=TaskSetConfig)
    budget: Budget = Field(default_factory=Budget)
    evaluation: EvaluationConfig = Field(default_factory=EvaluationConfig)
    repetitions: int = 1
    seed: int = 0
    output_dir: str = "runs"


def load_experiment(path: str | Path) -> ExperimentConfig:
    data = yaml.safe_load(Path(path).read_text())
    return ExperimentConfig.model_validate(data)