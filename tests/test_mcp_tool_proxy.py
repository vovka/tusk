import types

from tusk.shared.mcp import MCPToolProxy


def test_mcp_tool_proxy_converts_adapter_exception_to_failure() -> None:
    proxy = MCPToolProxy("gnome", _schema(), _failing_client())
    result = proxy.execute({})
    assert result.success is False
    assert "tool execution failed" in result.message


def test_flags_default_to_visible_and_not_sequence_callable() -> None:
    proxy = MCPToolProxy("gnome", _schema("type_text"), _client())
    assert proxy.planner_visible is True
    assert proxy.sequence_callable is False


def test_flags_come_from_constructor() -> None:
    proxy = MCPToolProxy("dictation", _schema("start_dictation"), _client(), planner_visible=False, sequence_callable=True)
    assert proxy.planner_visible is False
    assert proxy.sequence_callable is True


def _schema(name: str = "close_window") -> object:
    return types.SimpleNamespace(
        name=name,
        description="close",
        input_schema={"type": "object", "properties": {"window_title": {"type": "string"}}},
    )


def _client() -> object:
    return types.SimpleNamespace(call_tool=lambda name, parameters: None)


def _failing_client() -> object:
    def call_tool(name: str, parameters: dict) -> object:
        raise RuntimeError("boom")

    return types.SimpleNamespace(call_tool=call_tool)
