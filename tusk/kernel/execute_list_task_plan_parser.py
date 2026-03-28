from tusk.kernel.schemas.task_plan import TaskPlan

__all__ = ["ExecuteListTaskPlanParser"]


class ExecuteListTaskPlanParser:
    def parse(self, data: dict[str, object]) -> TaskPlan | None:
        steps = self._steps(data.get("execute", []))
        tools = self._tools(data.get("execute", []))
        if not steps or not tools:
            return None
        return TaskPlan("execute", "", steps, tools, "legacy execute fallback")

    def _steps(self, items: object) -> list[str]:
        return [f"Use {name}" for name in self._tools(items)]

    def _tools(self, items: object) -> list[str]:
        names: list[str] = []
        for item in items if isinstance(items, list) else []:
            self._append_name(names, item)
        return names

    def _append_name(self, names: list[str], item: object) -> None:
        if not isinstance(item, dict):
            return
        name = str(item.get("tool", "")).strip()
        if name and name not in names:
            names.append(name)
