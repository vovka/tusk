from tusk.kernel.agent.simple_schema_validator import SimpleSchemaValidator
from tusk.kernel.tools.tool_registry import ToolRegistry
from tusk.shared.schemas.tools.tool_sequence_plan import ToolSequencePlan

__all__ = ["PlanValidator"]

_FORBIDDEN_TOOLS = {"done", "execute_tool_sequence", "list_available_tools", "run_agent"}
_MAX_STEPS = 8


class PlanValidator:
    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry
        self._schemas = SimpleSchemaValidator()

    def validate_steps(self, plan: ToolSequencePlan) -> str | None:
        return self._steps(plan, "planned_steps") or self._tools(plan, "planned_steps") or self._args(plan)

    def validate_sequence(self, plan: ToolSequencePlan, allowed_tool_names: set[str]) -> str | None:
        return (self._steps(plan, "sequence_plan") or self._tools(plan, "sequence_plan")
                or self._sequence_tools(plan, allowed_tool_names) or self._args(plan))

    def _steps(self, plan: ToolSequencePlan, field_name: str) -> str | None:
        ids = [step.step_id for step in plan.steps]
        if not ids:
            return f"{field_name} requires at least one step"
        if len(plan.steps) > _MAX_STEPS:
            return f"{field_name} exceeds max steps ({_MAX_STEPS})"
        if any(not step.tool_name or not step.step_id for step in plan.steps):
            return f"{field_name} step ids and tool_name values must be non-empty"
        return None if len(ids) == len(set(ids)) else f"{field_name} contains duplicate step ids"

    def _tools(self, plan: ToolSequencePlan, field_name: str) -> str | None:
        for step in plan.steps:
            if step.tool_name in _FORBIDDEN_TOOLS:
                return f"{step.step_id}: synthetic tools are not allowed in {field_name}"
            if step.tool_name not in self._registry.tool_names():
                return f"{step.step_id}: unknown tool: {step.tool_name}"
        return None

    def _args(self, plan: ToolSequencePlan) -> str | None:
        for step in plan.steps:
            message = self._schemas.validate(self._registry.get(step.tool_name).input_schema, step.args)
            if message is not None:
                return f"{step.step_id}: {message}"
        return None

    def _sequence_tools(self, plan: ToolSequencePlan, allowed_tool_names: set[str]) -> str | None:
        for step in plan.steps:
            if not self._registry.get(step.tool_name).sequence_callable:
                return f"{step.step_id}: tool is not sequence_callable: {step.tool_name}"
        if plan.tool_names() != allowed_tool_names:
            return "sequence_plan tool set must match selected_tool_names"
        return None
