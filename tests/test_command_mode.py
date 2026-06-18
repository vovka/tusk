from dataclasses import dataclass

from tusk.kernel.agent_backends import AgentBackend, AgentRequest, AgentResult
from tusk.kernel.command_mode import CommandMode


@dataclass
class RecordingBackend(AgentBackend):
    request: AgentRequest | None = None

    def run(self, request: AgentRequest) -> AgentResult:
        self.request = request
        return AgentResult(True, "Done.")


class NullLogPrinter:
    def log(self, source: str, message: str, style: str) -> None:
        pass


def test_command_mode_sends_command_agent_request() -> None:
    backend = RecordingBackend()
    response = CommandMode(backend, NullLogPrinter()).process_command("open browser")
    assert backend.request == AgentRequest(user_text="open browser", mode="command")
    assert response.handled is True
    assert response.reply == "Done."
