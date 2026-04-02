from tusk.kernel.agent.simple_schema_validator import SimpleSchemaValidator
from tusk.kernel.tool_registry import ToolRegistry
from tusk.shared.schemas.tool_sequence_plan import ToolSequencePlan

__all__ = ["PlannerStepPlanValidator"]

_FORBIDDEN_TOOLS = {"done", "execute_tool_sequence", "list_available_tools", "run_agent"}
_MAX_PLANNED_STEPS = 8


class PlannerStepPlanValidator:
    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry
        self._schemas = SimpleSchemaValidator()

    def validate(self, plan_data: object) -> str | None:
        plan = ToolSequencePlan.from_dict(plan_data)
        if plan is None:
            return "invalid planned_steps"
        return self._steps(plan) or self._tools(plan) or self._args(plan)

    def _steps(self, plan: ToolSequencePlan) -> str | None:
        ids = [step.step_id for step in plan.steps]
        if not ids:
            return "planned_steps requires at least one step"
        if len(plan.steps) > _MAX_PLANNED_STEPS:
            return f"planned_steps exceeds max steps ({_MAX_PLANNED_STEPS})"
        if any(not step.tool_name or not step.step_id for step in plan.steps):
            return "planned_steps step ids and tool_name values must be non-empty"
        return None if len(ids) == len(set(ids)) else "planned_steps contains duplicate step ids"

    def _tools(self, plan: ToolSequencePlan) -> str | None:
        for step in plan.steps:
            if step.tool_name in _FORBIDDEN_TOOLS:
                return f"{step.step_id}: synthetic tools are not allowed in planned_steps"
            if step.tool_name not in self._registry.real_tool_names():
                return f"{step.step_id}: unknown tool: {step.tool_name}"
        return None

    def _args(self, plan: ToolSequencePlan) -> str | None:
        for step in plan.steps:
            schema = self._registry.get(step.tool_name).input_schema
            message = self._schemas.validate(schema, step.args)
            if message is not None:
                return f"{step.step_id}: {message}"
        return None
