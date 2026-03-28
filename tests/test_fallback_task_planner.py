import types

from tusk.kernel.fallback_task_planner import FallbackTaskPlanner
from tusk.kernel.schemas.task_plan import TaskPlan


def test_fallback_task_planner_uses_primary_plan() -> None:
    fallback = FallbackTaskPlanner(_planner(_plan("primary")), _planner(_plan("secondary")), _log())
    plan = fallback.plan("open gedit", "catalog")
    assert plan.reason == "primary"


def test_fallback_task_planner_uses_secondary_after_primary_failure() -> None:
    logged: list[tuple] = []
    fallback = FallbackTaskPlanner(_failing(), _planner(_plan("secondary")), _log(logged))
    plan = fallback.plan("open gedit", "catalog")
    assert plan.reason == "secondary"
    assert logged == [("PLANNER", "primary planner failed: planner offline")]


def _plan(reason: str) -> TaskPlan:
    return TaskPlan("execute", "", ["Open gedit"], ["gnome.launch_application"], reason)


def _planner(plan: TaskPlan) -> object:
    return types.SimpleNamespace(plan=lambda *args: plan)


def _failing() -> object:
    return types.SimpleNamespace(plan=lambda *args: (_ for _ in ()).throw(RuntimeError("planner offline")))


def _log(logged: list[tuple] | None = None) -> object:
    store = logged if logged is not None else []
    return types.SimpleNamespace(log=lambda *args: store.append(args))
