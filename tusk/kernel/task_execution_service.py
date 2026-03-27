from tusk.kernel.model_failure_reply_builder import ModelFailureReplyBuilder
from tusk.lib.logging.interfaces.log_printer import LogPrinter
from tusk.kernel.schemas.task_execution_result import TaskExecutionResult
from tusk.kernel.schemas.task_plan import TaskPlan
from tusk.kernel.task_plan_validator import TaskPlanValidator
from tusk.kernel.tool_registry import ToolRegistry

__all__ = ["TaskExecutionService"]

_MAX_REPLANS = 2


class TaskExecutionService:
    def __init__(self, planner: object, executor: object, tool_registry: ToolRegistry, log_printer: LogPrinter) -> None:
        self._planner = planner
        self._executor = executor
        self._registry = tool_registry
        self._log = log_printer
        self._validator = TaskPlanValidator(tool_registry)
        self._failure = ModelFailureReplyBuilder()

    def run(self, task: str) -> TaskExecutionResult:
        try:
            return self._run(task, None, "")
        except Exception as exc:
            self._log.log("TASK", f"execution failed: {exc}")
            return TaskExecutionResult("failed", self._failure.build(exc), str(exc))

    def _run(self, task: str, previous_plan: TaskPlan | None, needed_capability: str) -> TaskExecutionResult:
        for _ in range(_MAX_REPLANS + 1):
            plan, result = self._attempt(task, previous_plan, needed_capability)
            if result.status != "need_tools":
                return result
            previous_plan, needed_capability = plan, result.needed_capability
        return TaskExecutionResult("failed", "I couldn't finish the task with the available tools.", "replan limit reached")

    def _invalid_plan(self, reason: str) -> TaskExecutionResult:
        reply = "I couldn't build a reliable execution plan for that request."
        return TaskExecutionResult("failed", reply, reason)

    def _attempt(
        self,
        task: str,
        previous_plan: TaskPlan | None,
        needed_capability: str,
    ) -> tuple[TaskPlan | None, TaskExecutionResult]:
        plan = self._plan(task, previous_plan, needed_capability)
        invalid = self._validator.validate(plan)
        if invalid:
            return None, self._invalid_plan(invalid)
        if plan.status != "execute":
            return None, TaskExecutionResult(plan.status, plan.user_reply, plan.reason)
        return plan, self._execute(task, plan)

    def _plan(self, task: str, previous_plan: TaskPlan | None, needed_capability: str) -> TaskPlan:
        try:
            return self._planner.plan(task, self._registry.build_planner_catalog_text(), previous_plan, needed_capability)
        except Exception as exc:
            self._log.log("PLANNER", f"failure: {exc}")
            raise

    def _execute(self, task: str, plan: TaskPlan) -> TaskExecutionResult:
        try:
            return self._executor.execute(task, plan)
        except Exception as exc:
            self._log.log("AGENT", f"execution failure: {exc}")
            raise
