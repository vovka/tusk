import types
from typing import Any

from tusk.kernel.agent import AgentResult
from tusk.kernel.agent_backends import AgentRequest
from tusk.kernel.main_agent import MainAgent


class RecordingOrchestrator:
    def __init__(self) -> None:
        self.requests: list[Any] = []

    def run(self, request: Any) -> AgentResult:
        self.requests.append(request)
        return AgentResult("done", "result-session", "Done.")


def test_main_agent_run_uses_request_session_id() -> None:
    orchestrator = RecordingOrchestrator()
    history = types.SimpleNamespace(append=lambda message: None)
    request = AgentRequest("open browser", "command", "input-session")
    result = MainAgent(orchestrator, history).run(request)
    assert orchestrator.requests[0].session_id == "input-session"
    assert result.session_id == "result-session"
