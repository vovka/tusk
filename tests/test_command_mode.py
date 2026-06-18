from dataclasses import dataclass, field

from tusk.kernel.agent_backends import AgentBackend, AgentRequest, AgentResult
from tusk.kernel.command_mode import CommandMode


@dataclass
class RecordingBackend(AgentBackend):
    requests: list[AgentRequest] = field(default_factory=list)

    def run(self, request: AgentRequest) -> AgentResult:
        self.requests.append(request)
        return AgentResult(True, "Done.", "next-session")


class NullLogPrinter:
    def log(self, source: str, message: str, style: str) -> None:
        pass


def test_command_mode_sends_command_agent_request() -> None:
    backend = RecordingBackend()
    response = CommandMode(backend, NullLogPrinter()).process_command("open browser")
    assert backend.requests[0] == AgentRequest(user_text="open browser", mode="command")
    assert response.handled is True
    assert response.reply == "Done."


def test_command_mode_propagates_backend_session_id() -> None:
    backend = RecordingBackend()
    command_mode = CommandMode(backend, NullLogPrinter())
    command_mode.process_command("open browser")
    command_mode.process_command("close browser")
    assert backend.requests[1] == AgentRequest("close browser", "command", "next-session")
