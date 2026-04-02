import json
import types

from tests.kernel_api_support import make_agent, make_registry_tool
from tusk.kernel.tool_registry import ToolRegistry
from tusk.shared.schemas.tool_call import ToolCall
from tusk.shared.schemas.tool_result import ToolResult


def test_sequence_plan_runs_through_meta_tool() -> None:
    seen: list[dict[str, object]] = []
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.type_text", "typed", sequence_callable=True, execute=lambda args: _record(seen, args)))
    reply = make_agent(_conversation(), registry=registry, planner_llm=_planner(), executor_llm=_executor()).process_command("type hello")
    assert reply == "Typed hello."
    assert seen == [{"text": "hello"}]


def _conversation() -> object:
    state = {"step": 0}
    return types.SimpleNamespace(label="conversation", complete_tool_call=lambda p, m, t: _conversation_step(state, m))


def _conversation_step(state: dict[str, int], messages: list[dict[str, str]]) -> ToolCall:
    state["step"] += 1
    if state["step"] == 1:
        return ToolCall("run_agent", {"profile_id": "planner", "instruction": "type hello"}, "c1")
    if state["step"] == 2:
        child = _child(messages)
        params = {"profile_id": "executor", "instruction": "type hello", "session_refs": [child["child_session_id"]]}
        return ToolCall("run_agent", params, "c2")
    return ToolCall("done", {"status": "done", "summary": "Typed hello.", "text": "Typed hello."}, "c3")


def _planner() -> object:
    def complete(*args):
        payload = {"selected_tool_names": ["gnome.type_text"], "execution_mode": "normal", "planned_steps": {"goal": "Type hello", "steps": [_step()]}}
        return ToolCall("done", {"status": "done", "summary": "ready", "payload": payload}, "p1")

    return types.SimpleNamespace(label="planner", complete_tool_call=complete)


def _executor() -> object:
    state = {"step": 0}

    def complete(prompt, messages, tools):
        state["step"] += 1
        if state["step"] == 1:
            return ToolCall("execute_tool_sequence", {}, "e1")
        return ToolCall("done", {"status": "done", "summary": "Typed hello.", "text": "Typed hello."}, "e2")

    return types.SimpleNamespace(label="executor", complete_tool_call=complete)


def _child(messages: list[dict[str, str]]) -> dict[str, object]:
    content = next(item["content"] for item in reversed(messages) if item["content"].startswith("[child-result]"))
    fields = [line.split(": ", 1) for line in content.splitlines()[1:]]
    return {key: json.loads(value) if key == "child_payload" else value for key, value in fields}


def _step() -> dict[str, object]:
    return {"id": "s1", "tool_name": "gnome.type_text", "args": {"text": "hello"}}


def _record(seen: list[dict[str, object]], arguments: dict[str, object]) -> object:
    seen.append(dict(arguments))
    return ToolResult(True, "typed", {"echo": dict(arguments)})
