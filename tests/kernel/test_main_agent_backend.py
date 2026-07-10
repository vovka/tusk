import types
from typing import Any

from tusk.kernel.agent.backends import AgentRequest
from tusk.kernel.core.main_agent import MainAgent


class RecordingOrchestrator:
    def __init__(self) -> None:
        self.requests: list[Any] = []

    def run(self, request: Any) -> Any:
        self.requests.append(request)
        return types.SimpleNamespace(
            status="done",
            session_id="result-session",
            reply_text=lambda: "Done.",
        )


def test_main_agent_run_uses_request_session_id() -> None:
    orchestrator = RecordingOrchestrator()
    history = types.SimpleNamespace(append=lambda message: None)
    request = AgentRequest(
        user_text="open browser",
        mode="conversation",
        session_id="input-session",
    )
    result = MainAgent(orchestrator, history).run(request)
    assert orchestrator.requests[0].session_id == "input-session"
    assert result.session_id == "result-session"


def test_main_agent_run_clears_stale_session_id() -> None:
    orchestrator = RecordingOrchestrator()
    history = types.SimpleNamespace(append=lambda message: None)
    agent = MainAgent(orchestrator, history)
    initial_request = AgentRequest("open browser", "conversation", "input-session")
    clear_request = AgentRequest("close browser", "conversation", "")
    agent.run(initial_request)
    agent.run(clear_request)
    assert orchestrator.requests[1].session_id == ""
