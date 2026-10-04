import types

from tests.kernel_api_support import make_agent, make_registry_tool
from tusk.kernel.agent.runtime.call_tool import CallTool
from tusk.kernel.tools.tool_registry import ToolRegistry
from tusk.shared.schemas.tools.tool_call import ToolCall
from tusk.shared.schemas.tools.tool_result import ToolResult

_SLOT_SCHEMA = {
    "type": "object",
    "properties": {"slot": {"type": "string", "enum": ["a", "b"]}, "provider": {"type": "string"}},
    "required": ["slot"],
}


def test_unwrap_turns_call_tool_into_the_named_tool_call() -> None:
    wrapped = ToolCall("call_tool", {"name": "gnome.type_text", "arguments": {"text": "hi"}}, "c1")
    assert CallTool.unwrap(wrapped) == ToolCall("gnome.type_text", {"text": "hi"}, "c1")


def test_unwrap_leaves_other_calls_alone() -> None:
    call = ToolCall("done", {"status": "done"})
    assert CallTool.unwrap(call) is call


def test_catalogue_line_shows_short_name_args_and_enum_without_restated_description() -> None:
    registry = _registry()
    description = CallTool.definition(registry.planner_tools())["function"]["description"]
    assert "\nclose_window(window_title)\n" in description
    assert "switch_model(slot=a|b, provider?): Switch a slot's model" in description


def test_command_run_through_call_tool_keeps_consecutive_typing_guard() -> None:
    typed: list[str] = []
    registry = ToolRegistry()
    execute = lambda args: typed.append(args["text"]) or ToolResult(True, "typed")
    registry.register(make_registry_tool("gnome.type_text", "Type text", execute=execute))
    make_agent(_typing_llm(), registry=registry).process_command("type a poem", "command")
    assert typed == ["poem one"]


def _registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.close_window", "Close a window", input_schema=_window_schema()))
    registry.register(make_registry_tool("switch_model", "Switch a slot's model", input_schema=_SLOT_SCHEMA))
    return registry


def _window_schema() -> dict:
    return {"type": "object", "properties": {"window_title": {"type": "string"}}, "required": ["window_title"]}


def _typing_llm() -> object:
    calls = iter([
        ToolCall("call_tool", {"name": "type_text", "arguments": {"text": "poem one"}}, "c1"),
        ToolCall("call_tool", {"name": "type_text", "arguments": {"text": "poem two"}}, "c2"),
        ToolCall("done", {"status": "done", "summary": "typed"}, "c3"),
    ])
    return types.SimpleNamespace(label="command", complete_tool_call=lambda prompt, messages, tools: next(calls))
