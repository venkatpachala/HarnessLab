from __future__ import annotations

import json
import time

from harnesslab.core.types import Budget, ExecutionResult, StopReason, Usage
from harnesslab.environment.base import Environment
from harnesslab.harness.base import Harness
from harnesslab.models.base import ModelClient
from harnesslab.tasks.schema import Task
from harnesslab.trace.events import TraceRecorder


class DirectHarness(Harness):
    """H0 — model ↔ tools, no planner / memory / verifier."""

    name = "direct"
    version = "0.1"
    component = "direct"

    def run(
        self,
        task: Task,
        environment: Environment,
        model: ModelClient,
        budget: Budget,
        seed: int = 0,
    ) -> ExecutionResult:
        rec = TraceRecorder()
        t0 = time.time()
        rec.emit("run_started", self.component, task_id=task.id, harness=self.name)

        tools = environment.list_tools()
        if task.allowed_tools:
            allow = set(task.allowed_tools)
            tools = [t for t in tools if t.name in allow]
        tool_schemas = [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            }
            for t in tools
        ]

        messages: list[dict] = [
            {
                "role": "system",
                "content": (
                    "You are a support agent. Use tools to inspect and change store state. "
                    "Do not refund ineligible orders. Stop when the request is done."
                ),
            },
            {"role": "user", "content": task.prompt()},
        ]

        usage = Usage()
        stop = StopReason.COMPLETED
        error = None

        for step in range(budget.max_steps):
            usage.steps = step + 1
            if usage.input_tokens + usage.output_tokens >= budget.max_tokens:
                stop = StopReason.BUDGET_TOKENS
                break
            if usage.cost_usd >= budget.max_cost_usd:
                stop = StopReason.BUDGET_COST
                break

            rec.emit("model_call_started", self.component, step=step)
            resp = model.complete(messages, tools=tool_schemas)
            usage.model_calls += 1
            usage.input_tokens += resp.input_tokens
            usage.output_tokens += resp.output_tokens
            rec.emit(
                "model_call_completed",
                self.component,
                step=step,
                input_tokens=resp.input_tokens,
                output_tokens=resp.output_tokens,
                n_tool_calls=len(resp.tool_calls),
            )

            if not resp.tool_calls:
                messages.append({"role": "assistant", "content": resp.content})
                rec.emit("final_answer", self.component, text=resp.content)
                stop = StopReason.COMPLETED
                break

            messages.append(
                {
                    "role": "assistant",
                    "content": "TOOLCALLS:"
                    + json.dumps(
                        [
                            {"name": c.name, "arguments": c.arguments}
                            for c in resp.tool_calls
                        ]
                    ),
                }
            )

            for call in resp.tool_calls:
                usage.tool_calls += 1
                rec.emit(
                    "tool_call_started",
                    self.component,
                    tool=call.name,
                    arguments=call.arguments,
                )
                result = environment.call_tool(call.name, call.arguments)
                rec.emit(
                    "tool_result",
                    self.component,
                    tool=call.name,
                    ok=result.ok,
                    code=result.code,
                    data=result.data,
                    error=result.error,
                )
                messages.append(
                    {
                        "role": "tool",
                        "name": call.name,
                        "content": json.dumps(result.model_dump()),
                    }
                )
        else:
            stop = StopReason.BUDGET_STEPS

        usage.latency_s = time.time() - t0
        rec.emit("run_completed", self.component, stop_reason=stop.value)

        return ExecutionResult(
            run_id=rec.run_id,
            harness=self.name,
            model=model.name,
            task_id=task.id,
            seed=seed,
            stop_reason=stop,
            usage=usage,
            final_state=environment.get_state(),
            events=rec.as_dicts(),
            error=error,
        )