from tusk.kernel.interfaces.log_printer import LogPrinter
from tusk.kernel.interfaces.task_planner import TaskPlanner
from tusk.kernel.schemas.task_plan import TaskPlan

__all__ = ["FallbackTaskPlanner"]


class FallbackTaskPlanner(TaskPlanner):
    def __init__(self, primary: TaskPlanner, secondary: TaskPlanner, log_printer: LogPrinter) -> None:
        self._primary = primary
        self._secondary = secondary
        self._log = log_printer

    def plan(
        self,
        task: str,
        tool_catalog: str,
        previous_plan: TaskPlan | None = None,
        needed_capability: str = "",
    ) -> TaskPlan:
        try:
            return self._primary.plan(task, tool_catalog, previous_plan, needed_capability)
        except Exception as exc:
            self._log.log("PLANNER", f"primary planner failed: {exc}")
        return self._secondary.plan(task, tool_catalog, previous_plan, needed_capability)
