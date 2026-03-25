import json
import types

from tusk.kernel.llm_task_planner import LLMTaskPlanner
from tusk.kernel.schemas.task_plan import TaskPlan


def test_task_planner_builds_execute_plan_from_structured_output() -> None:
    llm = types.SimpleNamespace(label="planner", complete_structured=lambda *a: json.dumps(_execute_plan()))
    planner = LLMTaskPlanner(llm, types.SimpleNamespace(log=lambda *a: None))
    plan = planner.plan("open gedit", "gnome.launch_application: Launch an application")
    assert plan == TaskPlan("execute", "", ["Open gedit"], ["gnome.launch_application"], "need one app tool")


def test_task_planner_includes_replan_context_in_request() -> None:
    capture: dict[str, str] = {}
    llm = types.SimpleNamespace(label="planner", complete_structured=_capture(capture))
    planner = LLMTaskPlanner(llm, types.SimpleNamespace(log=lambda *a: None))
    previous = TaskPlan("execute", "", ["Type text"], ["gnome.type_text"], "first try")
    planner.plan("insert text", "gnome.type_text: Type text", previous, "Need keypress support")
    assert "Previous plan" in capture["message"]
    assert "Need keypress support" in capture["message"]


def test_task_planner_accepts_execute_list_fallback_shape() -> None:
    llm = types.SimpleNamespace(label="planner", complete_structured=lambda *a: json.dumps(_legacy_execute_plan()))
    planner = LLMTaskPlanner(llm, types.SimpleNamespace(log=lambda *a: None))
    plan = planner.plan("open gedit", "gnome.launch_application: Launch an application")
    assert plan.status == "execute"
    assert plan.selected_tools == ["gnome.launch_application", "gnome.focus_window"]
    assert plan.plan_steps == ["Use gnome.launch_application", "Use gnome.focus_window"]


def test_task_planner_falls_back_after_json_validate_failure() -> None:
    llm = types.SimpleNamespace(
        label="planner",
        complete_structured=lambda *a: (_ for _ in ()).throw(RuntimeError("json_validate_failed")),
        complete=lambda *a: json.dumps(_execute_plan()),
    )
    planner = LLMTaskPlanner(llm, types.SimpleNamespace(log=lambda *a: None))
    plan = planner.plan("open gedit", "gnome.launch_application: Launch an application")
    assert plan.status == "execute"
    assert plan.selected_tools == ["gnome.launch_application"]


def _execute_plan() -> dict[str, object]:
    return {
        "status": "execute",
        "user_reply": "",
        "plan_steps": ["Open gedit"],
        "selected_tools": ["gnome.launch_application"],
        "reason": "need one app tool",
    }


def _legacy_execute_plan() -> dict[str, object]:
    return {
        "execute": [
            {"tool": "gnome.launch_application", "arguments": {"application": "gedit"}},
            {"tool": "gnome.focus_window", "arguments": {"window_title": "gedit"}},
        ]
    }


def _capture(capture: dict[str, str]) -> object:
    def complete(system_prompt: str, user_message: str, schema_name: str, schema: dict, max_tokens: int = 256) -> str:
        capture["prompt"] = system_prompt
        capture["message"] = user_message
        return json.dumps(_execute_plan())

    return complete
