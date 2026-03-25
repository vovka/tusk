from abc import ABC, abstractmethod

from tusk.kernel.schemas.task_execution_result import TaskExecutionResult
from tusk.kernel.schemas.task_plan import TaskPlan

__all__ = ["TaskExecutor"]


class TaskExecutor(ABC):
    @abstractmethod
    def execute(self, task: str, plan: TaskPlan) -> TaskExecutionResult:
        ...
