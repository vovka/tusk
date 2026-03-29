import json
import types

from tests.kernel_api_support import HistoryRecorder, make_agent, make_registry_tool
from tusk.kernel.schemas.tool_call import ToolCall
from tusk.kernel.tool_registry import ToolRegistry


def test_main_agent_returns_final_reply() -> None:
    llm = types.SimpleNamespace(
        label="conversation",
        complete_tool_call=lambda *args: ToolCall(
            "done",
            {"status": "done", "summary": "Finished.", "text": "Finished."},
            "call-1",
        ),
    )
    assert make_agent(llm).process_command("test") == "Finished."


def test_main_agent_invalid_json_returns_visible_failure() -> None:
    logs: list[tuple[str, str]] = []
    llm = types.SimpleNamespace(label="conversation", complete_tool_call=lambda *args: (_ for _ in ()).throw(ValueError("bad tool call")))
    log = types.SimpleNamespace(log=lambda tag, message: logs.append((tag, message)))
    reply = make_agent(llm, log=log).process_command("test")
    assert "temporarily unavailable" in reply.lower()
    assert any(tag == "AGENT" and "llm failure" in message for tag, message in logs)


def test_clarify_persists_reply() -> None:
    history = HistoryRecorder()
    llm = types.SimpleNamespace(
        label="conversation",
        complete_tool_call=lambda *a: ToolCall(
            "done",
            {"status": "clarify", "summary": "Need detail", "text": "What exactly should I open?"},
            "call-1",
        ),
    )
    reply = make_agent(llm, history=history).process_command("open it")
    assert reply == "What exactly should I open?"
    assert history.stored == [("user", "Command: open it"), ("assistant", "What exactly should I open?")]


def test_main_agent_delegates_to_planner_then_executor() -> None:
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.launch_application", "launched", input_schema=_launch_schema()))
    conversation = _conversation_orchestrator_llm()
    planner = types.SimpleNamespace(
        label="planner",
        complete_tool_call=lambda *args: ToolCall(
            "done",
            {
                "status": "done",
                "summary": "Plan ready",
                "payload": {
                    "selected_tool_names": ["gnome.launch_application"],
                    "plan_text": "Launch gedit.",
                },
            },
            "plan-1",
        ),
    )
    executor = types.SimpleNamespace(
        label="executor",
        complete_tool_call=lambda *args: ToolCall(
            "done",
            {"status": "done", "summary": "Opened gedit", "text": "Opened gedit."},
            "exec-1",
        ),
    )
    reply = make_agent(conversation, registry=registry, planner_llm=planner, executor_llm=executor).process_command("open gedit")
    assert reply == "Opened gedit."


def _conversation_orchestrator_llm() -> object:
    state = {"step": 0}

    def complete(prompt, messages, tools):
        state["step"] += 1
        if state["step"] == 1:
            return ToolCall("run_agent", {"profile_id": "planner", "instruction": "open gedit"}, "call-1")
        if state["step"] == 2:
            planner_result = json.loads(messages[-1]["content"])
            return ToolCall(
                "run_agent",
                {
                    "profile_id": "executor",
                    "instruction": "open gedit",
                    "runtime_tool_names": planner_result["payload"]["selected_tool_names"],
                    "session_refs": [planner_result["session_id"]],
                },
                "call-2",
            )
        return ToolCall("done", {"status": "done", "summary": "Opened gedit", "text": "Opened gedit."}, "call-3")

    return types.SimpleNamespace(label="conversation", complete_tool_call=complete)


def _launch_schema() -> dict[str, object]:
    return {
        "type": "object",
        "properties": {"application_name": {"type": "string"}},
        "required": ["application_name"],
        "additionalProperties": False,
    }
