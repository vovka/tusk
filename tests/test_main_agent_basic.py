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


def test_main_agent_executes_task_tool() -> None:
    registry = ToolRegistry()
    registry.register(make_registry_tool("execute_task", "task finished", planner_visible=False, input_schema=_task_schema()))
    llm = types.SimpleNamespace(label="agent", complete_tool_call=lambda *args: ToolCall("execute_task", {"task": "open gedit"}, "call-1"))
    reply = make_agent(llm, registry=registry).process_command("open gedit")
    assert reply == "task finished"


def test_main_agent_routes_start_dictation_through_execute_task() -> None:
    calls: list[dict[str, str]] = []
    registry = ToolRegistry()
    registry.register(_execute_task(calls))
    llm = types.SimpleNamespace(label="agent", complete_tool_call=lambda *args: ToolCall("execute_task", {}, "call-1"))
    reply = make_agent(llm, registry=registry).process_command("start dictation mode")
    assert reply == "dictation started"
    assert calls == [{"task": "start dictation mode"}]


def test_main_agent_blocks_direct_desktop_tool_calls() -> None:
    registry = ToolRegistry()
    registry.register(make_registry_tool("execute_task", "task finished", planner_visible=False, input_schema=_task_schema()))
    registry.register(make_registry_tool("gnome.list_windows", "listed"))
    llm = types.SimpleNamespace(label="agent", complete_tool_call=lambda *args: ToolCall("gnome.list_windows", {}, "call-1"))
    reply = make_agent(llm, registry=registry).process_command("list windows")
    assert reply == "Use execute_task for actionable requests."


def _task_schema() -> dict[str, object]:
    return {
        "type": "object",
        "properties": {"task": {"type": "string"}},
        "required": ["task"],
        "additionalProperties": False,
    }


def _execute_task(calls: list[dict[str, str]]) -> object:
    def execute(arguments: dict[str, str]) -> object:
        calls.append(arguments)
        return types.SimpleNamespace(message="dictation started")

    return types.SimpleNamespace(
        name="execute_task",
        description="task finished",
        input_schema=_task_schema(),
        execute=execute,
        source="kernel",
        planner_visible=False,
    )
