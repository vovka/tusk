from tusk.kernel.agent.agent_result import AgentResult
from tusk.kernel.agent.tool_sequence_plan_validator import ToolSequencePlanValidator
from tusk.kernel.tool_registry import ToolRegistry
from tusk.shared.logging.interfaces.log_printer import LogPrinter
from tusk.shared.schemas.tool_sequence_plan import ToolSequencePlan

__all__ = ["PlannerSequencePromoter"]


class PlannerSequencePromoter:
    def __init__(
        self,
        registry: ToolRegistry,
        log_printer: LogPrinter | None = None,
    ) -> None:
        self._registry = registry
        self._log = log_printer

    def promote(self, result: AgentResult) -> AgentResult:
        plan = ToolSequencePlan.from_dict(result.payload.get("planned_steps"))
        if plan is None:
            return result
        message = ToolSequencePlanValidator(self._registry).validate(plan.to_dict(), set(plan.tool_names()))
        if message is not None:
            return result
        self._write_log(result.session_id, plan)
        return self._result(result, plan)

    def materialize(self, result: AgentResult) -> AgentResult:
        plan = ToolSequencePlan.from_dict(result.payload.get("planned_steps"))
        return result if plan is None else self._result(result, plan)

    def _write_log(self, session_id: str, plan: ToolSequencePlan) -> None:
        if self._log is None:
            return
        text = f"session={session_id} promoted normal plan to sequence with {len(plan.steps)} steps"
        self._log.log("SEQPROMOTE", text)

    def _result(self, result: AgentResult, plan: ToolSequencePlan) -> AgentResult:
        payload = dict(result.payload)
        payload["execution_mode"] = "sequence"
        payload["sequence_plan"] = plan.to_dict()
        return AgentResult(result.status, result.session_id, result.summary, result.text, payload, result.artifact_refs)
