import types

from tests.kernel_api_support import make_agent, make_registry_tool
from tusk.kernel.schemas.tool_call import ToolCall
from tusk.kernel.tool_registry import ToolRegistry


def test_agent_stops_after_repeating_same_tool_call() -> None:
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.type_text", "typed", prompt_visible=True))
    calls = iter([_type_call(), _type_call(), _type_call()])
    llm = types.SimpleNamespace(label="agent", complete_tool_call=lambda *args: next(calls))
    reply = make_agent(llm, registry=registry).process_command("clear the editor")
    assert "different action" in reply.lower()


def test_agent_allows_more_than_ten_steps_before_done() -> None:
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.type_text", "typed", prompt_visible=True))
    llm = types.SimpleNamespace(label="agent", complete_tool_call=_many_steps())
    reply = make_agent(llm, registry=registry).process_command("long task")
    assert reply == "Finished after many steps."


def _type_call() -> ToolCall:
    return ToolCall("gnome.type_text", {"text": "hi", "reply": "Typing."}, "call-1")


def _many_steps():
    calls = [ToolCall("gnome.type_text", {"text": str(index)}, f"call-{index}") for index in range(1, 12)]
    calls.append(ToolCall("done", {"reply": "Finished after many steps."}, "call-done"))
    replies = iter(calls)
    return lambda *args: next(replies)
