import types

from tests.kernel_api_support import make_registry_tool
from tusk.kernel.describe_tool_tool import DescribeToolTool
from tusk.kernel.find_tools_tool import FindToolsTool
from tusk.kernel.run_tool_tool import RunToolTool
from tusk.kernel.schemas.tool_result import ToolResult
from tusk.kernel.tool_registry import ToolRegistry


def test_find_tools_returns_matching_hidden_tool() -> None:
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.launch_application", "Launch an application"))
    result = FindToolsTool(registry).execute({"query": "launch application"})
    assert "gnome.launch_application" in result.message


def test_describe_tool_returns_schema_for_hidden_tool() -> None:
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.type_text", "Type text"))
    result = DescribeToolTool(registry).execute({"name": "gnome.type_text"})
    assert '"text"' in result.message and "input_json" in result.message


def test_run_tool_executes_hidden_tool() -> None:
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.type_text", "typed"))
    result = RunToolTool(registry).execute({"name": "gnome.type_text", "input_json": "{\"text\":\"hi\"}"})
    assert result == ToolResult(True, "typed")


def test_run_tool_rejects_broker_target() -> None:
    registry = ToolRegistry()
    registry.register(make_registry_tool("find_tools", "discover", broker=True, prompt_visible=True))
    result = RunToolTool(registry).execute({"name": "find_tools", "input_json": "{}"})
    assert "cannot execute broker tool" in result.message


def test_run_tool_rejects_control_chars_for_type_text() -> None:
    registry = ToolRegistry()
    registry.register(_failing_type_text_tool())
    result = RunToolTool(registry).execute({"name": "gnome.type_text", "input_json": "{\"text\":\"\\u0001\\u007f\"}"})
    assert "use press_keys" in result.message


def test_run_tool_rejects_invalid_input_json() -> None:
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.type_text", "typed"))
    result = RunToolTool(registry).execute({"name": "gnome.type_text", "input_json": "[]"})
    assert "must decode to an object" in result.message


def test_run_tool_rejects_missing_required_arguments() -> None:
    registry = ToolRegistry()
    registry.register(_required_tool())
    result = RunToolTool(registry).execute({"name": "gnome.close_window", "input_json": "{}"})
    assert "missing arguments" in result.message


def _failing_type_text_tool() -> object:
    return types.SimpleNamespace(
        name="gnome.type_text",
        description="typed",
        input_schema={"type": "object", "properties": {"text": {"type": "string"}}},
        source="gnome",
        broker=False,
        prompt_visible=False,
        execute=lambda arguments: ToolResult(False, _control_text_error()),
    )


def _required_tool() -> object:
    return types.SimpleNamespace(
        name="gnome.close_window",
        description="close",
        input_schema={"type": "object", "properties": {"window_title": {"type": "string"}}, "required": ["window_title"]},
        source="gnome",
        broker=False,
        prompt_visible=False,
        execute=lambda arguments: ToolResult(True, "closed"),
    )


def _control_text_error() -> str:
    return "type_text only accepts literal printable text; use press_keys for Enter, Delete, shortcuts, or control keys."
