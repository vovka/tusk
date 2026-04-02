from tusk.kernel.agent.agent_result import AgentResult
from tusk.kernel.agent.planner_sequence_promoter import PlannerSequencePromoter
from tusk.kernel.agent.planner_step_plan_validator import PlannerStepPlanValidator
from tusk.kernel.agent.tool_sequence_plan_validator import ToolSequencePlanValidator
from tusk.kernel.tool_registry import ToolRegistry
from tusk.shared.logging.interfaces.log_printer import LogPrinter
from tusk.shared.schemas.tool_sequence_plan import ToolSequencePlan

__all__ = ["PlannerResultValidator"]


class PlannerResultValidator:
    def __init__(self, log_printer: LogPrinter | None = None) -> None:
        self._log = log_printer

    def validate(self, profile_id: str, result: AgentResult, allowed: object) -> AgentResult:
        early = self._early(profile_id, result, allowed)
        if early is not None:
            return early
        registry = self._registry(allowed)
        assert registry is not None
        return self._validated(result, registry)

    def _registry(self, allowed: object) -> ToolRegistry | None:
        return allowed if isinstance(allowed, ToolRegistry) else None

    def _early(self, profile_id: str, result: AgentResult, allowed: object) -> AgentResult | None:
        if profile_id != "planner" or result.status != "done":
            return result
        registry = self._registry(allowed)
        if registry is None:
            return self._failed(result, "planner validation requires a tool registry")
        message = PlannerStepPlanValidator(registry).validate(result.payload.get("planned_steps"))
        return self._failed(result, message) if message is not None else None

    def _validated(self, result: AgentResult, registry: ToolRegistry) -> AgentResult:
        plan = ToolSequencePlan.from_dict(result.payload.get("planned_steps"))
        assert plan is not None
        result = self._normalized(result, plan)
        if self._mode(result) != "sequence":
            return self._promoter(registry).promote(result)
        return self._sequence_result(result, registry, plan)

    def _sequence_result(self, result: AgentResult, registry: ToolRegistry, plan: ToolSequencePlan) -> AgentResult:
        message = ToolSequencePlanValidator(registry).validate(plan.to_dict(), set(plan.tool_names()))
        return self._failed(result, message) if message is not None else self._promoter(registry).materialize(result)

    def _promoter(self, registry: ToolRegistry) -> PlannerSequencePromoter:
        return PlannerSequencePromoter(registry, self._log)

    def _mode(self, result: AgentResult) -> str:
        return str(result.payload.get("execution_mode", "normal"))

    def _failed(self, result: AgentResult, message: str) -> AgentResult:
        return AgentResult("failed", result.session_id, message, message)

    def _normalized(self, result: AgentResult, plan: ToolSequencePlan) -> AgentResult:
        payload = dict(result.payload)
        payload["selected_tool_names"] = list(plan.ordered_tool_names())
        return AgentResult(result.status, result.session_id, result.summary, result.text, payload, result.artifact_refs)
