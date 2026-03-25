import types

from tests.kernel_api_support import HistoryRecorder, make_agent, make_registry_tool
from tusk.kernel.schemas.tool_call import ToolCall
from tusk.kernel.tool_registry import ToolRegistry


def test_main_agent_returns_final_reply() -> None:
    llm = types.SimpleNamespace(label="agent", complete_tool_call=lambda *args: ToolCall("done", {"reply": "Finished."}, "call-1"))
    agent = make_agent(llm)
    assert agent.process_command("test") == "Finished."


def test_main_agent_invalid_json_returns_visible_failure() -> None:
    logs: list[tuple[str, str]] = []
    llm = types.SimpleNamespace(label="agent", complete_tool_call=lambda *args: (_ for _ in ()).throw(ValueError("bad tool call")))
    log = types.SimpleNamespace(log=lambda tag, message: logs.append((tag, message)))
    reply = make_agent(llm, log=log).process_command("test")
    assert "temporarily unavailable" in reply.lower()
    assert any(tag == "AGENT" and "llm failure" in message for tag, message in logs)


def test_main_agent_handles_rate_limit_without_crashing() -> None:
    llm = types.SimpleNamespace(
        label="agent",
        complete_tool_call=lambda *args: (_ for _ in ()).throw(RuntimeError("Rate limit reached")),
    )
    logs: list[tuple[str, str]] = []
    log = types.SimpleNamespace(log=lambda tag, message, *rest: logs.append((tag, message)))
    reply = make_agent(llm, log=log).process_command("tell me a joke")
    assert "rate limited" in reply.lower()
    assert any(tag == "AGENT" and "llm failure" in message for tag, message in logs)


def test_clarify_stops_agent_loop_and_persists_reply() -> None:
    history = HistoryRecorder()
    llm = types.SimpleNamespace(
        label="agent",
        complete_tool_call=lambda *a: ToolCall("clarify", {"reply": "What exactly should I open?"}, "call-1"),
    )
    reply = make_agent(llm, history=history).process_command("open it")
    assert reply == "What exactly should I open?"
    assert history.stored == [("user", "Command: open it"), ("assistant", "What exactly should I open?")]


def test_main_agent_blocks_hidden_direct_tool_calls() -> None:
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.list_windows", "listed"))
    llm = types.SimpleNamespace(label="agent", complete_tool_call=_hidden_then_done())
    reply = make_agent(llm, registry=registry).process_command("list windows")
    assert reply == "Describe the tool before calling it directly."


def test_main_agent_allows_described_tool_call() -> None:
    registry = ToolRegistry()
    registry.register(make_registry_tool("describe_tool", "describe", broker=True, prompt_visible=True))
    registry.register(make_registry_tool("gnome.list_windows", "listed"))
    llm = types.SimpleNamespace(label="agent", complete_tool_call=_described_then_done())
    reply = make_agent(llm, registry=registry).process_command("list windows")
    assert reply == "Finished."


def _hidden_then_done():
    replies = iter([
        ToolCall("gnome.list_windows", {"reply": "Listing windows."}, "call-1"),
        ToolCall("done", {"reply": "Describe the tool before calling it directly."}, "call-2"),
    ])
    return lambda *args: next(replies)


def _described_then_done():
    replies = iter([
        ToolCall("describe_tool", {"name": "gnome.list_windows", "reply": "Checking schema."}, "call-1"),
        ToolCall("gnome.list_windows", {"reply": "Listing windows."}, "call-2"),
        ToolCall("done", {"reply": "Finished."}, "call-3"),
    ])
    return lambda *args: next(replies)
