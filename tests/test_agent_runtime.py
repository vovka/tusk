import types

from tests.kernel_api_support import make_agent, make_registry_tool
from tusk.shared.schemas.tool_call import ToolCall
from tusk.kernel.tool_registry import ToolRegistry


def test_planner_rejects_missing_planned_steps() -> None:
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.type_text", "type"))
    conversation = _delegate_to_planner()
    planner = _planner_with_payload({})
    reply = make_agent(conversation, registry=registry, planner_llm=planner).process_command("test")
    assert "invalid planned_steps" in reply.lower()


def test_planner_accepts_valid_steps_with_bad_selected_names() -> None:
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.type_text", "type"))
    conversation = _delegate_to_planner()
    planner = _planner_with_payload(_planned_payload(["executor", "desktop"]))
    reply = make_agent(conversation, registry=registry, planner_llm=planner).process_command("test")
    assert "child_status: done" in reply.lower()


def test_executor_rejects_empty_tools() -> None:
    conversation = _delegate_to_executor(runtime_tools=[])
    reply = make_agent(conversation).process_command("test")
    assert "requires runtime tools" in reply.lower()


def test_child_failure_bubbles_to_parent() -> None:
    conversation = _delegate_to_planner()
    planner = _failing_llm(RuntimeError("provider down"))
    reply = make_agent(conversation, planner_llm=planner).process_command("test")
    assert "unavailable" in reply.lower() or "failed" in reply.lower()


def test_recursion_guard_blocks_self_delegation() -> None:
    conversation = _delegate_to_conversation()
    reply = make_agent(conversation).process_command("test")
    assert "recursive" in reply.lower() or "failed" in reply.lower()


def test_conversation_must_finish_after_executor_done() -> None:
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.type_text", "type"))
    conversation = _delegate_after_executor_done()
    executor = _executor_done()
    reply = make_agent(conversation, registry=registry, executor_llm=executor).process_command("test")
    assert "must call done after executor returns status=done" in reply.lower()


def _delegate_to_planner() -> object:
    state = {"step": 0}

    def complete(prompt, messages, tools):
        state["step"] += 1
        if state["step"] == 1:
            return ToolCall("run_agent", {"profile_id": "planner", "instruction": "do work"}, "c1")
        return ToolCall("done", {"status": "done", "summary": "done", "text": messages[-1]["content"]}, "c2")

    return types.SimpleNamespace(label="conversation", complete_tool_call=complete)


def _delegate_to_executor(runtime_tools: list[str] | None = None) -> object:
    state = {"step": 0}

    def complete(prompt, messages, tools):
        state["step"] += 1
        if state["step"] == 1:
            params = {"profile_id": "executor", "instruction": "do work", "runtime_tool_names": runtime_tools or []}
            return ToolCall("run_agent", params, "c1")
        return ToolCall("done", {"status": "done", "summary": "done", "text": messages[-1]["content"]}, "c2")

    return types.SimpleNamespace(label="conversation", complete_tool_call=complete)


def _delegate_to_conversation() -> object:
    state = {"step": 0}

    def complete(prompt, messages, tools):
        state["step"] += 1
        if state["step"] == 1:
            return ToolCall("run_agent", {"profile_id": "conversation", "instruction": "loop"}, "c1")
        return ToolCall("done", {"status": "done", "summary": "done", "text": messages[-1]["content"]}, "c2")

    return types.SimpleNamespace(label="conversation", complete_tool_call=complete)


def _planner_with_payload(payload: dict[str, object]) -> object:
    return types.SimpleNamespace(
        label="planner",
        complete_tool_call=lambda *a: ToolCall("done", {"status": "done", "summary": "planned", "payload": payload}, "p1"),
    )


def _planned_payload(names: list[str]) -> dict[str, object]:
    step = {"id": "s1", "tool_name": "gnome.type_text", "args": {"text": "hello"}}
    return {"selected_tool_names": names, "execution_mode": "normal", "planned_steps": {"steps": [step]}}


def _delegate_after_executor_done() -> object:
    state = {"step": 0}

    def complete(prompt, messages, tools):
        state["step"] += 1
        if state["step"] == 1:
            params = {"profile_id": "executor", "instruction": "do work", "runtime_tool_names": ["gnome.type_text"]}
            return ToolCall("run_agent", params, "c1")
        return ToolCall("run_agent", {"profile_id": "planner", "instruction": "do more work"}, "c2")

    return types.SimpleNamespace(label="conversation", complete_tool_call=complete)


def _executor_done() -> object:
    return types.SimpleNamespace(
        label="executor",
        complete_tool_call=lambda *a: ToolCall("done", {"status": "done", "summary": "finished", "text": "finished"}, "e1"),
    )


def _failing_llm(exc: Exception) -> object:
    return types.SimpleNamespace(label="planner", complete_tool_call=lambda *args: (_ for _ in ()).throw(exc))
