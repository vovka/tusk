from abc import ABC, abstractmethod

from tusk.kernel.schemas.task_plan import TaskPlan

__all__ = ["TaskPlanner"]


class TaskPlanner(ABC):
    @abstractmethod
    def plan(
        self,
        task: str,
        tool_catalog: str,
        previous_plan: TaskPlan | None = None,
        needed_capability: str = "",
    ) -> TaskPlan:
        ...
