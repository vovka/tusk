import types

from tusk.lib.mcp import MCPToolProxy
from tusk.kernel.tool_registry import ToolRegistry


def test_mcp_tool_proxy_converts_adapter_exception_to_failure() -> None:
    proxy = MCPToolProxy("gnome", _schema(), _client(), lambda coro: (_ for _ in ()).throw(RuntimeError("boom")))
    result = proxy.execute({})
    assert result.success is False
    assert "tool execution failed" in result.message


def test_dictation_lifecycle_tools_are_hidden_from_planner() -> None:
    registry = ToolRegistry()
    registry.register(MCPToolProxy("dictation", _schema("start_dictation"), _client(), lambda coro: None))
    registry.register(MCPToolProxy("dictation", _schema("stop_dictation"), _client(), lambda coro: None))
    registry.register(MCPToolProxy("dictation", _schema("process_segment"), _client(), lambda coro: None))
    assert registry.planner_tool_names() == {"dictation.process_segment"}


def test_non_lifecycle_adapter_tools_remain_planner_visible() -> None:
    proxy = MCPToolProxy("gnome", _schema("type_text"), _client(), lambda coro: None)
    assert proxy.planner_visible is True


def _schema(name: str = "close_window") -> object:
    return types.SimpleNamespace(
        name=name,
        description="close",
        input_schema={"type": "object", "properties": {"window_title": {"type": "string"}}},
    )


def _client() -> object:
    return types.SimpleNamespace(call_tool=lambda name, parameters: None)
