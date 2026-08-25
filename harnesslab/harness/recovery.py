"""H3 — Direct loop + harness-level recovery.

Retryable errors (timeout, rate_limit, server_error) are retried in the
harness. After max_retries extra attempts, the model sees
`retries_exhausted` instead of another raw timeout — so it is less likely
to spam the same call.
"""

from __future__ import annotations

import json
import time

from harnesslab.core.types import Budget, ExecutionResult, StopReason, Usage
from harnesslab.environment.base import Environment, ToolResult
from harnesslab.harness.base import Harness
from harnesslab.models.base import ModelClient, ToolCall
from harnesslab.tasks.schema import Task
from harnesslab.trace.events import TraceRecorder

RETRYABLE = {"timeout", "rate_limit", "server_error"}

SYSTEM = (
    "You are a support agent. Use tools to inspect and change store state. "
    "Do not refund ineligible orders. Stop when the request is done. "
    "If a tool returns code retries_exhausted, do not immediately repeat "
    "the same call; use another approach or stop."
)


class RecoveryHarness(Harness):
    name = "recovery"
    version = "0.2"

    def __init__(self, max_retries: int = 2):
        self.max_retries = max_retries

    def run(self, task, environment, model, budget, seed=0) -> ExecutionResult:
        rec = TraceRecorder()
        t0 = time.time()
        rec.emit("run_started", "recovery", task_id=task.id, harness=self.name)

        tools = environment.list_tools()
        if task.allowed_tools:
            allow = set(task.allowed_tools)
            tools = [t for t in tools if t.name in allow]
        tool_schemas = [
            {"name": t.name, "description": t.description, "parameters": t.parameters}
            for t in tools
        ]

        messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": task.prompt()},
        ]
        usage = Usage()
        stop = StopReason.COMPLETED

        for step in range(budget.max_steps):
            usage.steps = step + 1
            if usage.input_tokens + usage.output_tokens >= budget.max_tokens:
                stop = StopReason.BUDGET_TOKENS
                break

            rec.emit("model_call_started", "direct", step=step)
            resp = model.complete(messages, tools=tool_schemas)
            usage.model_calls += 1
            usage.input_tokens += resp.input_tokens
            usage.output_tokens += resp.output_tokens
            rec.emit(
                "model_call_completed",
                "direct",
                step=step,
                input_tokens=resp.input_tokens,
                output_tokens=resp.output_tokens,
                n_tool_calls=len(resp.tool_calls),
            )

            if not resp.tool_calls:
                messages.append({"role": "assistant", "content": resp.content})
                rec.emit("final_answer", "direct", text=resp.content)
                stop = StopReason.COMPLETED
                break

            messages.append(
                {
                    "role": "assistant",
                    "content": "TOOLCALLS:"
                    + json.dumps(
                        [{"name": c.name, "arguments": c.arguments} for c in resp.tool_calls]
                    ),
                }
            )
            for call in resp.tool_calls:
                result = self._call_with_retry(environment, rec, call, usage)
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
        rec.emit("run_completed", "recovery", stop_reason=stop.value)
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
            extra={"max_retries": self.max_retries},
        )

    def _call_with_retry(self, environment, rec, call: ToolCall, usage) -> ToolResult:
        attempt = 0
        last = ToolResult(ok=False, code="error", error="no attempt")
        while True:
            usage.tool_calls += 1
            rec.emit(
                "tool_call_started",
                "recovery" if attempt else "direct",
                tool=call.name,
                arguments=call.arguments,
                attempt=attempt,
            )
            last = environment.call_tool(call.name, call.arguments)
            rec.emit(
                "tool_result",
                "recovery" if attempt else "direct",
                tool=call.name,
                ok=last.ok,
                code=last.code,
                data=last.data,
                error=last.error,
                attempt=attempt,
            )
            if last.ok or last.code not in RETRYABLE:
                return last
            if attempt >= self.max_retries:
                exhausted = ToolResult(
                    ok=False,
                    code="retries_exhausted",
                    error=f"{last.code} after {attempt + 1} attempts",
                    data={"last_code": last.code, "attempts": attempt + 1},
                )
                rec.emit(
                    "retries_exhausted",
                    "recovery",
                    tool=call.name,
                    last_code=last.code,
                    attempts=attempt + 1,
                )
                return exhausted
            attempt += 1
            rec.emit(
                "retry",
                "recovery",
                tool=call.name,
                code=last.code,
                attempt=attempt,
                max_retries=self.max_retries,
            )