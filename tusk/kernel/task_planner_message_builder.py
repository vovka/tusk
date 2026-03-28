from tusk.kernel.schemas.task_plan import TaskPlan

__all__ = ["TaskPlannerMessageBuilder"]


class TaskPlannerMessageBuilder:
    def build(
        self,
        task: str,
        tool_catalog: str,
        previous_plan: TaskPlan | None = None,
        needed_capability: str = "",
    ) -> str:
        parts = [f"Task:\n{task}", f"Tool catalog:\n{tool_catalog}"]
        if previous_plan:
            parts.extend(self._replan_parts(previous_plan, needed_capability))
        return "\n\n".join(parts)

    def _replan_parts(self, plan: TaskPlan, needed_capability: str) -> list[str]:
        tools = ", ".join(plan.selected_tools)
        steps = "\n".join(f"- {step}" for step in plan.plan_steps)
        return [
            f"Previous plan:\n{steps}",
            f"Previous tools:\n{tools}",
            f"Execution needs more capability:\n{needed_capability}",
        ]
