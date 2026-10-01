import types

from tests.kernel_api_support import make_registry_tool
from tusk.kernel.agent.orchestrator_tool_dispatcher import OrchestratorToolDispatcher
from tusk.kernel.tools.tool_registry import ToolRegistry
from tusk.shared.schemas.tools.tool_call import ToolCall
from tusk.shared.schemas.tools.tool_result import ToolResult


def test_dispatcher_holds_destructive_call() -> None:
    seen: list[dict] = []
    result = _dispatch(seen, ToolCall("gnome.close_window", {"window_title": "Code"}, "c1"))
    assert result.message.startswith("needs_confirmation")
    assert seen == []


def test_dispatcher_runs_harmless_key_press() -> None:
    seen: list[dict] = []
    assert _dispatch(seen, ToolCall("gnome.press_keys", {"keys": "<ctrl>v"}, "c1")).success is True
    assert seen == [{"keys": "<ctrl>v"}]


def _dispatch(seen: list[dict], call: ToolCall) -> ToolResult:
    registry = ToolRegistry()
    for name in ("gnome.close_window", "gnome.press_keys"):
        registry.register(make_registry_tool(name, "ok", execute=lambda arguments: seen.append(arguments) or ToolResult(True, "ok")))
    dispatcher = OrchestratorToolDispatcher(registry, types.SimpleNamespace(), types.SimpleNamespace())
    return dispatcher.dispatch(call, lambda tool_call: ToolResult(False, "unused"))
