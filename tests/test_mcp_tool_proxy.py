import types

from tusk.lib.mcp import MCPToolProxy


def test_mcp_tool_proxy_converts_adapter_exception_to_failure() -> None:
    proxy = MCPToolProxy("gnome", _schema(), _client(), lambda coro: (_ for _ in ()).throw(RuntimeError("boom")))
    result = proxy.execute({})
    assert result.success is False
    assert "tool execution failed" in result.message


def _schema() -> object:
    return types.SimpleNamespace(
        name="close_window",
        description="close",
        input_schema={"type": "object", "properties": {"window_title": {"type": "string"}}},
    )


def _client() -> object:
    return types.SimpleNamespace(call_tool=lambda name, parameters: None)
