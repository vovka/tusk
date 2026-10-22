from tusk.kernel.agent.agent_result import AgentResult
from tusk.kernel.agent.tool_sequence.plan_validator import PlanValidator
from tusk.kernel.tools.tool_registry import ToolRegistry
from tusk.shared.logging.interfaces.log_printer import LogPrinter
from tusk.shared.schemas.tools.tool_sequence_plan import ToolSequencePlan

__all__ = ["ResultValidator"]


class ResultValidator:
    def __init__(self, log_printer: LogPrinter | None = None) -> None:
        self._log = log_printer

    def validate(self, profile_id: str, result: AgentResult, registry: ToolRegistry) -> AgentResult:
        if profile_id != "planner" or result.status != "done":
            return result
        plan = ToolSequencePlan.from_dict(result.payload.get("planned_steps"))
        if plan is None:
            return self._failed(result, "invalid planned_steps")
        return self._validated(result, plan, PlanValidator(registry))

    def _validated(self, result: AgentResult, plan: ToolSequencePlan, validator: PlanValidator) -> AgentResult:
        message = validator.validate_steps(plan)
        if message is not None:
            return self._failed(result, message)
        result = self._normalized(result, plan)
        message = validator.validate_sequence(plan, plan.tool_names())
        if self._mode(result) == "sequence":
            return self._failed(result, message) if message is not None else self._as_sequence(result, plan)
        return result if message is not None else self._promoted(result, plan)

    def _promoted(self, result: AgentResult, plan: ToolSequencePlan) -> AgentResult:
        if self._log is not None:
            text = f"session={result.session_id} promoted normal plan to sequence with {len(plan.steps)} steps"
            self._log.log("SEQPROMOTE", text)
        return self._as_sequence(result, plan)

    def _as_sequence(self, result: AgentResult, plan: ToolSequencePlan) -> AgentResult:
        payload = dict(result.payload)
        payload["execution_mode"] = "sequence"
        payload["sequence_plan"] = plan.to_dict()
        return self._with_payload(result, payload)

    def _normalized(self, result: AgentResult, plan: ToolSequencePlan) -> AgentResult:
        payload = dict(result.payload)
        payload["selected_tool_names"] = list(plan.ordered_tool_names())
        return self._with_payload(result, payload)

    def _with_payload(self, result: AgentResult, payload: dict[str, object]) -> AgentResult:
        return AgentResult(result.status, result.session_id, result.summary, result.text, payload, result.artifact_refs)

    def _mode(self, result: AgentResult) -> str:
        return str(result.payload.get("execution_mode", "normal"))

    def _failed(self, result: AgentResult, message: str) -> AgentResult:
        return AgentResult("failed", result.session_id, message, message)
