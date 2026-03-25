import types

from tusk.kernel.schemas.task_execution_result import TaskExecutionResult
from tusk.kernel.schemas.task_plan import TaskPlan
from tusk.kernel.task_execution_service import TaskExecutionService
from tusk.kernel.tool_registry import ToolRegistry


def test_task_execution_service_replans_when_executor_needs_tools() -> None:
    service, planner = _replanning_service()
    result = service.run("open gedit and press enter")
    assert result.reply == "Completed."
    assert planner.requests[1]["needed"] == "keyboard tool"


def test_task_execution_service_rejects_unknown_selected_tools() -> None:
    planner = _planner([TaskPlan("execute", "", ["Open gedit"], ["missing.tool"], "bad")])
    service = TaskExecutionService(planner, _executor([]), _registry(), _log([]))
    result = service.run("open gedit")
    assert result.status == "failed"
    assert "couldn't build a reliable execution plan" in result.reply.lower()


def test_task_execution_service_handles_planner_failure() -> None:
    planner = types.SimpleNamespace(plan=lambda *args: (_ for _ in ()).throw(RuntimeError("planner unavailable")))
    logs: list[tuple[str, str]] = []
    service = TaskExecutionService(planner, _executor([]), _registry(), _log(logs))
    result = service.run("open gedit")
    assert result.status == "failed"
    assert "temporarily unavailable" in result.reply.lower()
    assert ("PLANNER", "failure: planner unavailable") in logs


def _planner(plans: list[TaskPlan]) -> object:
    requests: list[dict[str, object]] = []
    iterator = iter(plans)

    def plan(task: str, tool_catalog: str, previous_plan: TaskPlan | None = None, needed_capability: str = "") -> TaskPlan:
        requests.append({"task": task, "catalog": tool_catalog, "previous": previous_plan, "needed": needed_capability})
        return next(iterator)

    return types.SimpleNamespace(plan=plan, requests=requests)


def _executor(results: list[TaskExecutionResult]) -> object:
    iterator = iter(results)
    return types.SimpleNamespace(execute=lambda task, plan: next(iterator))


def _registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(_tool("gnome.launch_application", "Launch", "name"))
    registry.register(_tool("gnome.press_keys", "Press", "keys"))
    return registry


def _log(logs: list[tuple[str, str]]) -> object:
    return types.SimpleNamespace(log=lambda tag, message: logs.append((tag, message)))


def _replanning_service() -> tuple[TaskExecutionService, object]:
    planner = _planner(_plans())
    executor = _executor(_results())
    return TaskExecutionService(planner, executor, _registry(), _log([])), planner


def _plans() -> list[TaskPlan]:
    return [
        TaskPlan("execute", "", ["Open gedit"], ["gnome.launch_application"], "first"),
        TaskPlan("execute", "", ["Open gedit", "Press Enter"], ["gnome.launch_application", "gnome.press_keys"], "second"),
    ]


def _results() -> list[TaskExecutionResult]:
    return [
        TaskExecutionResult("need_tools", "", "Need Enter key support", "keyboard tool"),
        TaskExecutionResult("done", "Completed.", ""),
    ]


def _tool(name: str, description: str, field: str) -> object:
    return types.SimpleNamespace(
        name=name,
        description=description,
        input_schema={"type": "object", "properties": {field: {"type": "string"}}},
        execute=lambda arguments: None,
        source="gnome",
    )
