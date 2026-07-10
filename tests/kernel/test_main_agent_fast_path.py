import types

from tusk.kernel.core.main_agent import MainAgent
from tusk.kernel.agent.agent_run_request import AgentRunRequest


def _orchestrator(requests: list[AgentRunRequest]) -> types.SimpleNamespace:
    def run(request: AgentRunRequest) -> types.SimpleNamespace:
        requests.append(request)
        return types.SimpleNamespace(status="done", session_id="conv-1", reply_text=lambda: "opened gedit")
    return types.SimpleNamespace(run=run)


def _store(events: list[tuple[str, str, dict]]) -> types.SimpleNamespace:
    return types.SimpleNamespace(append_event=lambda session_id, name, data: events.append((session_id, name, data)))


def _agent(requests: list[AgentRunRequest], events: list | None = None) -> MainAgent:
    history = types.SimpleNamespace(append=lambda message: None)
    store = _store(events) if events is not None else None
    return MainAgent(_orchestrator(requests), history, store)


def test_command_kind_runs_command_profile_in_fresh_session() -> None:
    requests: list[AgentRunRequest] = []
    reply = _agent(requests).process_command("open gedit", "command")
    assert reply == "opened gedit"
    assert requests[0].profile_id == "command"
    assert requests[0].session_id == ""
    assert requests[0].runtime_tool_names == ("*",)


def test_conversation_kind_keeps_conversation_profile_and_session() -> None:
    requests: list[AgentRunRequest] = []
    agent = _agent(requests)
    agent.process_command("hello")
    agent.process_command("hello again")
    assert [request.profile_id for request in requests] == ["conversation", "conversation"]
    assert requests[1].session_id == "conv-1"


def test_fast_command_appends_exchange_to_conversation_session() -> None:
    requests: list[AgentRunRequest] = []
    events: list[tuple[str, str, dict]] = []
    agent = _agent(requests, events)
    agent.process_command("hello")
    agent.process_command("open gedit", "command")
    lines = [(sid, data["role"], data["content"]) for sid, name, data in events]
    assert ("conv-1", "user", "open gedit") in lines
    assert ("conv-1", "assistant", "[did: opened gedit]") in lines


def test_fast_command_skips_history_share_without_conversation_session() -> None:
    events: list[tuple[str, str, dict]] = []
    _agent([], events).process_command("open gedit", "command")
    assert events == []


def test_fast_command_does_not_adopt_the_command_session() -> None:
    requests: list[AgentRunRequest] = []
    agent = _agent(requests)
    agent.process_command("open gedit", "command")
    agent.process_command("open gedit again", "command")
    assert [request.session_id for request in requests] == ["", ""]
