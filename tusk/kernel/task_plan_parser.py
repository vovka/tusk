import json

from tusk.kernel.execute_list_task_plan_parser import ExecuteListTaskPlanParser
from tusk.kernel.schemas.task_plan import TaskPlan

__all__ = ["TaskPlanParser"]


class TaskPlanParser:
    def __init__(self) -> None:
        self._fallback = ExecuteListTaskPlanParser()

    def parse(self, raw: str) -> TaskPlan:
        data = json.loads(raw)
        return self._fallback.parse(data) or self._parsed(data)

    def _parsed(self, data: dict[str, object]) -> TaskPlan:
        return TaskPlan(
            str(data.get("status", "")),
            str(data.get("user_reply", "")),
            self._list(data, "plan_steps"),
            self._list(data, "selected_tools"),
            str(data.get("reason", "")),
        )

    def _list(self, data: dict[str, object], key: str) -> list[str]:
        return [str(item) for item in data.get(key, [])]
