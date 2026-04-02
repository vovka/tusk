import tempfile

from tusk.kernel.agent.agent_run_request import AgentRunRequest
from tusk.kernel.agent.file_agent_session_store import FileAgentSessionStore
from tusk.kernel.agent.planner_runtime_tool_resolver import PlannerRuntimeToolResolver


def test_resolver_recovers_sequence_mode_and_plan_from_session_ref() -> None:
    store = FileAgentSessionStore(tempfile.mkdtemp(prefix="tusk-sequence-"))
    session_id = store.create_session_id()
    store.start_session(session_id, "planner", "", "", {})
    store.append_event(session_id, "session_finished", _result(session_id))
    request = AgentRunRequest("type hello", profile_id="executor", session_refs=(session_id,))
    resolved = PlannerRuntimeToolResolver(store).resolve(request, {"gnome.type_text"})
    assert resolved.runtime_tool_names == ("gnome.type_text",)
    assert resolved.execution_mode == "sequence"
    assert resolved.sequence_plan is not None
    assert resolved.sequence_plan.steps[0].tool_name == "gnome.type_text"


def _result(session_id: str) -> dict[str, object]:
    payload = {
        "selected_tool_names": ["gnome.type_text"],
        "execution_mode": "sequence",
        "planned_steps": {"goal": "Type hello", "steps": [_step()]},
    }
    return {"status": "done", "session_id": session_id, "summary": "ready", "text": "", "payload": payload, "artifact_refs": []}


def _step() -> dict[str, object]:
    return {"id": "s1", "tool_name": "gnome.type_text", "args": {"text": "hello"}}
