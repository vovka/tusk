import json
import types

from tests.kernel_api_support import HistoryRecorder, make_agent, make_registry_tool
from tusk.kernel.schemas.tool_call import ToolCall
from tusk.kernel.tool_registry import ToolRegistry


def test_main_agent_returns_final_reply() -> None:
    llm = _done_llm("done", "Finished.", "Finished.")
    assert make_agent(llm).process_command("test") == "Finished."


def test_main_agent_invalid_json_returns_visible_failure() -> None:
    logs: list[tuple[str, str]] = []
    llm = _failing_llm(ValueError("bad tool call"))
    log = types.SimpleNamespace(log=lambda tag, message: logs.append((tag, message)))
    reply = make_agent(llm, log=log).process_command("test")
    assert "temporarily unavailable" in reply.lower()
    assert any(tag == "AGENT" and "llm failure" in message for tag, message in logs)


def test_clarify_persists_reply() -> None:
    history = HistoryRecorder()
    llm = _done_llm("clarify", "Need detail", "What exactly should I open?")
    reply = make_agent(llm, history=history).process_command("open it")
    assert reply == "What exactly should I open?"
    expected = [("user", "Command: open it"), ("assistant", "What exactly should I open?")]
    assert history.stored == expected


def test_main_agent_delegates_to_planner_then_executor() -> None:
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.launch_application", "launched", input_schema=_launch_schema()))
    reply = _run_delegation(registry)
    assert reply == "Opened gedit."


def _run_delegation(registry: ToolRegistry) -> str:
    conversation = _conversation_llm()
    planner = _planner_llm()
    executor = _done_llm("done", "Opened gedit", "Opened gedit.")
    agent = make_agent(conversation, registry=registry, planner_llm=planner, executor_llm=executor)
    return agent.process_command("open gedit")


def _conversation_llm() -> object:
    state = {"step": 0}
    return types.SimpleNamespace(label="conversation", complete_tool_call=lambda p, m, t: _conversation_step(state, m))


def _conversation_step(state: dict[str, int], messages: list[dict[str, str]]) -> ToolCall:
    state["step"] += 1
    if state["step"] == 1:
        return _planner_call()
    if state["step"] == 2:
        return _executor_call(messages)
    return ToolCall("done", {"status": "done", "summary": "Opened gedit", "text": "Opened gedit."}, "call-3")


def _planner_call() -> ToolCall:
    return ToolCall("run_agent", {"profile_id": "planner", "instruction": "open gedit"}, "call-1")


def _executor_call(messages: list[dict[str, str]]) -> ToolCall:
    planner_result = json.loads(messages[-1]["content"])
    return ToolCall("run_agent", {
        "profile_id": "executor", "instruction": "open gedit",
        "runtime_tool_names": planner_result["payload"]["selected_tool_names"],
        "session_refs": [planner_result["session_id"]],
    }, "call-2")


def _planner_llm() -> object:
    return types.SimpleNamespace(label="planner", complete_tool_call=lambda *args: ToolCall("done", {
        "status": "done", "summary": "Plan ready",
        "payload": {"selected_tool_names": ["gnome.launch_application"], "plan_text": "Launch gedit."},
    }, "plan-1"))


def _done_llm(status: str, summary: str, text: str) -> object:
    return types.SimpleNamespace(
        label="conversation",
        complete_tool_call=lambda *args: ToolCall("done", {"status": status, "summary": summary, "text": text}, "call-1"),
    )


def _failing_llm(exc: Exception) -> object:
    return types.SimpleNamespace(label="conversation", complete_tool_call=lambda *args: (_ for _ in ()).throw(exc))


def _launch_schema() -> dict[str, object]:
    return {
        "type": "object",
        "properties": {"application_name": {"type": "string"}},
        "required": ["application_name"],
        "additionalProperties": False,
    }
