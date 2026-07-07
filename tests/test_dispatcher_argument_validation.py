import types

from tusk.kernel.agent.orchestrator_tool_dispatcher import OrchestratorToolDispatcher
from tusk.kernel.tools.registered_tool import RegisteredTool
from tusk.kernel.tools.tool_registry import ToolRegistry
from tusk.shared.schemas.tool_call import ToolCall
from tusk.shared.schemas.tool_result import ToolResult

_SCHEMA = {
    "type": "object",
    "properties": {"title": {"type": "string"}},
    "required": ["title"],
    "additionalProperties": False,
}


def test_dispatch_rejects_arguments_missing_required_fields() -> None:
    result = _dispatch(ToolCall("close_window", {}, "c1"))
    assert result.success is False
    assert "title" in result.message


def test_dispatch_rejects_unexpected_argument_fields() -> None:
    result = _dispatch(ToolCall("close_window", {"title": "Firefox", "force": True}, "c1"))
    assert result.success is False
    assert "force" in result.message


def test_dispatch_rejects_wrong_argument_types() -> None:
    result = _dispatch(ToolCall("close_window", {"title": 42}, "c1"))
    assert result.success is False


def test_dispatch_executes_valid_arguments() -> None:
    result = _dispatch(ToolCall("close_window", {"title": "Firefox"}, "c1"))
    assert result.success is True
    assert result.message == "closed"


def _dispatch(tool_call: ToolCall) -> ToolResult:
    registry = ToolRegistry()
    registry.register(RegisteredTool("close_window", "closes a window", _SCHEMA, lambda args: ToolResult(True, "closed"), "gnome"))
    dispatcher = OrchestratorToolDispatcher(registry, types.SimpleNamespace(list_tools=lambda: None), types.SimpleNamespace())
    return dispatcher.dispatch(tool_call, run_agent=lambda call: ToolResult(False, "unused"))
