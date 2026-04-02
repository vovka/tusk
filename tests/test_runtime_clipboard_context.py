import types

from tests.kernel_api_support import make_agent
from tusk.shared.schemas.tool_call import ToolCall
from tusk.shared.schemas.tool_result import ToolResult
from tusk.kernel.tool_registry import ToolRegistry


def test_executor_sees_written_clipboard_text_in_context() -> None:
    reply = make_agent(_delegate_once(), registry=_registry(), executor_llm=_clipboard_executor()).process_command("test")
    assert "child_summary: saw clipboard text" in reply


def _delegate_once() -> object:
    state = {"step": 0}
    params = {"profile_id": "executor", "instruction": "paste", "runtime_tool_names": ["gnome.write_clipboard"]}

    def complete(prompt, messages, tools):
        state["step"] += 1
        if state["step"] == 1:
            return ToolCall("run_agent", params, "c1")
        return ToolCall("done", {"status": "done", "summary": "done", "text": messages[-1]["content"]}, "c2")

    return types.SimpleNamespace(label="conversation", complete_tool_call=complete)


def _registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(_clipboard_tool())
    return registry


def _clipboard_tool() -> object:
    schema = {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}
    execute = lambda arguments: ToolResult(True, "clipboard written", {"clipboard_text": arguments["text"]})
    return types.SimpleNamespace(name="gnome.write_clipboard", description="clipboard", input_schema=schema, execute=execute, source="gnome", planner_visible=True)


def _clipboard_executor() -> object:
    state = {"step": 0}

    def complete(prompt, messages, tools):
        state["step"] += 1
        return _clipboard_step(state["step"], messages)

    return types.SimpleNamespace(label="executor", complete_tool_call=complete)


def _clipboard_step(step: int, messages: list[dict[str, str]]) -> ToolCall:
    if step == 1:
        return ToolCall("gnome.write_clipboard", {"text": "frozen sonnet"}, "e1")
    if _saw_clipboard_text(messages):
        return ToolCall("done", {"status": "done", "summary": "saw clipboard text", "text": "ok"}, "e2")
    return ToolCall("done", {"status": "failed", "summary": "missing clipboard text", "text": "missing"}, "e2")


def _saw_clipboard_text(messages: list[dict[str, str]]) -> bool:
    return any(item["content"] == "[clipboard-written]\nfrozen sonnet" for item in messages)
