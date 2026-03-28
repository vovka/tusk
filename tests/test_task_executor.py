import types

from tests.kernel_api_support import make_executor, make_registry_tool
from tusk.kernel.schemas.task_plan import TaskPlan
from tusk.kernel.schemas.tool_call import ToolCall
from tusk.kernel.tool_registry import ToolRegistry


def test_task_executor_sends_only_selected_tool_definitions() -> None:
    capture: dict[str, object] = {}
    executor = make_executor(_llm(capture), registry=_registry())
    executor.execute("type hello", _plan())
    names = [item["function"]["name"] for item in capture["tools"]]
    assert "gnome.type_text" in names
    assert "gnome.list_windows" not in names
    assert "need_tools" in names
    assert "Split long literal text into multiple gnome.type_text calls" in capture["prompt"]


def test_task_executor_returns_need_tools_signal() -> None:
    llm = types.SimpleNamespace(
        label="agent",
        complete_tool_call=lambda *args: ToolCall("need_tools", {"reason": "Need window inspection", "needed_capability": "window state"}, "call-1"),
    )
    executor = make_executor(llm, registry=ToolRegistry())
    result = executor.execute("close the active window", TaskPlan("execute", "", ["Close window"], [], "none"))
    assert result.status == "need_tools"
    assert result.needed_capability == "window state"


def _llm(capture: dict[str, object]) -> object:
    return types.SimpleNamespace(label="agent", complete_tool_call=_capture(capture))


def _plan() -> TaskPlan:
    return TaskPlan("execute", "", ["Type text"], ["gnome.type_text"], "selected one tool")


def _registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.type_text", "type"))
    registry.register(make_registry_tool("gnome.list_windows", "list"))
    return registry


def _capture(capture: dict[str, object]) -> object:
    def complete(prompt, messages, tools):
        capture["prompt"] = prompt
        capture["tools"] = list(tools)
        return ToolCall("done", {"reply": "Finished."}, "call-1")

    return complete
