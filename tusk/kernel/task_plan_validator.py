from tusk.kernel.schemas.task_plan import TaskPlan
from tusk.kernel.tool_registry import ToolRegistry

__all__ = ["TaskPlanValidator"]


class TaskPlanValidator:
    def __init__(self, tool_registry: ToolRegistry) -> None:
        self._registry = tool_registry

    def validate(self, plan: TaskPlan) -> str:
        return self._status_error(plan) or self._tool_error(plan)

    def _status_error(self, plan: TaskPlan) -> str:
        if plan.status == "execute" and plan.plan_steps and plan.selected_tools:
            return ""
        if plan.status == "execute":
            return "missing plan steps or selected tools"
        if plan.status in {"clarify", "unknown"} and plan.user_reply:
            return ""
        return "missing user reply"

    def _tool_error(self, plan: TaskPlan) -> str:
        if plan.status != "execute":
            return ""
        allowed = self._registry.planner_tool_names()
        names = [name for name in plan.selected_tools if name not in allowed]
        return "" if not names else f"unknown selected tools: {', '.join(names)}"
