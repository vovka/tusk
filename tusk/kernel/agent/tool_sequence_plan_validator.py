from tusk.kernel.agent.simple_schema_validator import SimpleSchemaValidator
from tusk.kernel.tool_registry import ToolRegistry
from tusk.shared.schemas.tool_sequence_plan import ToolSequencePlan

__all__ = ["ToolSequencePlanValidator"]

_FORBIDDEN_TOOLS = {"done", "execute_tool_sequence", "list_available_tools", "run_agent"}
_MAX_SEQUENCE_STEPS = 8


class ToolSequencePlanValidator:
    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry
        self._schemas = SimpleSchemaValidator()

    def validate(self, plan_data: object, allowed: set[str]) -> str | None:
        plan = ToolSequencePlan.from_dict(plan_data)
        if plan is None:
            return "invalid sequence_plan"
        return self._steps(plan) or self._tools(plan, allowed) or self._args(plan)

    def _steps(self, plan: ToolSequencePlan) -> str | None:
        ids = [step.step_id for step in plan.steps]
        if not ids:
            return "sequence_plan requires at least one step"
        if len(plan.steps) > _MAX_SEQUENCE_STEPS:
            return f"sequence_plan exceeds max steps ({_MAX_SEQUENCE_STEPS})"
        if any(not step.tool_name or not step.step_id for step in plan.steps):
            return "sequence_plan step ids and tool_name values must be non-empty"
        return None if len(ids) == len(set(ids)) else "sequence_plan contains duplicate step ids"

    def _tools(self, plan: ToolSequencePlan, allowed: set[str]) -> str | None:
        for step in plan.steps:
            message = self._tool(step.tool_name)
            if message is not None:
                return f"{step.step_id}: {message}"
        return None if plan.tool_names() == allowed else "sequence_plan tool set must match selected_tool_names"

    def _tool(self, name: str) -> str | None:
        if name in _FORBIDDEN_TOOLS:
            return "synthetic tools are not allowed in sequence_plan"
        if name not in self._registry.real_tool_names():
            return f"unknown tool: {name}"
        tool = self._registry.get(name)
        return None if tool.sequence_callable else f"tool is not sequence_callable: {name}"

    def _args(self, plan: ToolSequencePlan) -> str | None:
        for step in plan.steps:
            message = self._schemas.validate(self._registry.get(step.tool_name).input_schema, step.args)
            if message is not None:
                return f"{step.step_id}: {message}"
        return None
