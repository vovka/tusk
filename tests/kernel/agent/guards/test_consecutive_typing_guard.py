import types

from tests.support.kernel_api import make_agent, make_registry_tool
from tusk.kernel.agent.guards.consecutive_typing_guard import ConsecutiveTypingGuard
from tusk.kernel.tools.tool_registry import ToolRegistry
from tusk.shared.schemas.tools.tool_call import ToolCall
from tusk.shared.schemas.tools.tool_result import ToolResult


def _typed(guard: ConsecutiveTypingGuard, text: str) -> None:
    guard.observe(ToolCall("gnome.type_text", {"text": text}, "c1"), ToolResult(True, "typed"))


def test_second_consecutive_typing_is_refused() -> None:
    guard = ConsecutiveTypingGuard()
    _typed(guard, "poem one")
    assert guard.refusal("command", ToolCall("gnome.type_text", {"text": "poem two"}, "c2")) is not None


def test_typing_after_another_action_is_allowed() -> None:
    guard = ConsecutiveTypingGuard()
    _typed(guard, "url")
    guard.observe(ToolCall("gnome.press_keys", {"keys": "Return"}, "c2"), ToolResult(True, "pressed"))
    assert guard.refusal("command", ToolCall("gnome.type_text", {"text": "query"}, "c3")) is None


def test_failed_typing_may_be_retried() -> None:
    guard = ConsecutiveTypingGuard()
    guard.observe(ToolCall("gnome.type_text", {"text": "poem"}, "c1"), ToolResult(False, "no window"))
    assert guard.refusal("command", ToolCall("gnome.type_text", {"text": "poem"}, "c2")) is None


def test_command_run_types_a_poem_only_once() -> None:
    typed: list[str] = []
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.type_text", "typed", execute=lambda args: typed.append(args["text"]) or ToolResult(True, "typed")))
    reply = make_agent(_typing_llm(), registry=registry).process_command("type a poem", "command")
    assert typed == ["poem one"]
    assert reply == "typed"



def _typing_llm() -> object:
    calls = iter([ToolCall("gnome.type_text", {"text": "poem one"}, "c1"), ToolCall("gnome.type_text", {"text": "poem two"}, "c2"),
                  ToolCall("done", {"status": "done", "summary": "typed"}, "c3")])
    return types.SimpleNamespace(label="command", complete_tool_call=lambda prompt, messages, tools: next(calls))
