import time
from typing import Callable

from tusk.kernel.agent.tool_sequence.plan_validator import PlanValidator
from tusk.kernel.agent.tool_sequence.recorder import Recorder
from tusk.kernel.tools.tool_registry import ToolRegistry
from tusk.shared.schemas.tools.tool_result import ToolResult
from tusk.shared.schemas.tools.tool_sequence_plan import ToolSequencePlan
from tusk.shared.schemas.tools.tool_sequence_step import ToolSequenceStep

__all__ = ["Executor"]


class Executor:
    def __init__(self, registry: ToolRegistry, session_store: object,
                 interrupt_token: object | None = None, sleep: Callable[[float], None] = time.sleep) -> None:
        self._registry = registry
        self._validator = PlanValidator(registry)
        self._record = Recorder(session_store)
        self._token = interrupt_token
        self._sleep = sleep

    def execute(self, session_id: str, parameters: dict[str, object], allowed: set[str]) -> ToolResult:
        message = self._validator.validate(parameters, allowed)
        if message is not None:
            return self._invalid(session_id, message)
        plan = ToolSequencePlan.from_dict(parameters)
        assert plan is not None
        return self._run(session_id, plan)

    def execute_plan(self, session_id: str, plan: ToolSequencePlan | None, allowed: set[str]) -> ToolResult:
        if plan is None:
            return self._invalid(session_id, "execute_tool_sequence requires a resolved sequence_plan")
        message = self._validator.validate(plan.to_dict(), allowed)
        return self._invalid(session_id, message) if message is not None else self._run(session_id, plan)

    def _invalid(self, session_id: str, message: str) -> ToolResult:
        self._record.finished(session_id, "failed", message)
        return ToolResult(False, message, {"status": "failed", "summary": message})

    def _run(self, session_id: str, plan: ToolSequencePlan) -> ToolResult:
        self._record.started(session_id, plan.goal)
        completed: list[str] = []
        step_results: dict[str, object] = {}
        for step in plan.steps:
            outcome = self._run_step(session_id, plan, step, completed, step_results)
            if outcome is not None:
                return outcome
        return self._done(session_id, plan, completed, step_results)

    def _run_step(
        self, session_id: str, plan: ToolSequencePlan, step: ToolSequenceStep,
        completed: list[str], step_results: dict[str, object],
    ) -> ToolResult | None:
        if self._interrupted():
            return self._cancelled(session_id, plan, completed, step_results)
        result = self._step(session_id, step)
        step_results[step.step_id] = self._step_data(result)
        if not result.success:
            return self._failed(session_id, plan, completed, step.step_id, step_results, result.message)
        completed.append(step.step_id)
        self._settle(plan, step)
        return None

    def _settle(self, plan: ToolSequencePlan, step: ToolSequenceStep) -> None:
        # ponytail: fixed manifest-declared pause after launch-style steps — swap for a window-ready probe if it flakes
        settle_ms = self._registry.get(step.tool_name).settle_ms
        if settle_ms and step is not plan.steps[-1]:
            self._sleep(settle_ms / 1000)

    def _step(self, session_id: str, step: ToolSequenceStep) -> ToolResult:
        self._record.requested(session_id, step.step_id, step.tool_name, step.args)
        result = self._registry.get(step.tool_name).execute(step.args)
        self._record.result(session_id, step.step_id, step.tool_name, result)
        return result

    def _interrupted(self) -> bool:
        return self._token is not None and self._token.is_interrupted

    def _cancelled(self, session_id: str, plan: ToolSequencePlan, completed: list[str], results: dict[str, object]) -> ToolResult:
        summary = "sequence cancelled by user"
        self._record.finished(session_id, "cancelled", summary)
        return ToolResult(False, summary, self._payload("cancelled", plan, completed, "", results))

    def _done(self, session_id: str, plan: ToolSequencePlan, completed: list[str], results: dict[str, object]) -> ToolResult:
        summary = self._summary(plan, "completed")
        self._record.finished(session_id, "done", summary)
        payload = self._payload("done", plan, completed, "", results)
        return ToolResult(True, summary, payload)

    def _failed(self, session_id: str, plan: ToolSequencePlan, completed: list[str],
                failed_step_id: str, results: dict[str, object], message: str) -> ToolResult:
        summary = f"sequence failed at {failed_step_id}: {message}"
        self._record.finished(session_id, "failed", summary)
        payload = self._payload("failed", plan, completed, failed_step_id, results)
        return ToolResult(False, summary, payload)

    def _payload(
        self, status: str, plan: ToolSequencePlan, completed: list[str],
        failed_step_id: str, results: dict[str, object],
    ) -> dict[str, object]:
        return {
            "status": status,
            "goal": plan.goal,
            "completed_step_ids": completed,
            "failed_step_id": failed_step_id,
            "step_results": results,
        }

    def _step_data(self, result: ToolResult) -> dict[str, object]:
        data = {"success": result.success, "message": result.message}
        if result.data is not None:
            data["data"] = result.data
        return data

    def _summary(self, plan: ToolSequencePlan, outcome: str) -> str:
        goal = plan.goal or "sequence"
        return f"{goal} {outcome}"
