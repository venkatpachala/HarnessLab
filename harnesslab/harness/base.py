from __future__ import annotations

from abc import ABC, abstractmethod

from harnesslab.core.types import Budget, ExecutionResult
from harnesslab.environment.base import Environment
from harnesslab.models.base import ModelClient
from harnesslab.tasks.schema import Task


class Harness(ABC):
    """Common interface every harness must implement.

    Experiment validity rule: harnesses may only differ in *how* they
    call the model and tools. They share the same Environment, Task,
    ModelClient, and Budget for a given run.
    """

    name: str = "base"
    version: str = "0.1"

    @abstractmethod
    def run(
        self,
        task: Task,
        environment: Environment,
        model: ModelClient,
        budget: Budget,
        seed: int = 0,
    ) -> ExecutionResult:
        """Execute one task and return a full result + trace.

        Must not mutate global config. May mutate `environment` state
        through tools (that is the point of state-based eval).
        """
        ...