import pytest

from tusk.kernel.agent_backends import AgentRequest
from tusk.kernel.agent_backends.tusk_agent_backend import TuskAgentBackend


class RecordingAgent:
    def __init__(self) -> None:
        self.commands: list[str] = []

    def process_command(self, command: str) -> str:
        self.commands.append(command)
        return "Done."


def test_tusk_agent_backend_exposes_backend_metadata() -> None:
    backend = TuskAgentBackend(RecordingAgent())
    assert backend.name == "tusk"
    assert backend.supports_streaming is False


def test_tusk_agent_backend_normalizes_legacy_reply() -> None:
    agent = RecordingAgent()
    request = AgentRequest("open browser", "command", "session-1")
    result = TuskAgentBackend(agent).run(request)
    assert agent.commands == ["open browser"]
    assert result.status == "success"
    assert result.final_text == "Done."
    assert result.reply == "Done."
    assert result.handled is True


def test_tusk_agent_backend_lets_programmer_errors_surface() -> None:
    class BrokenAgent:
        def process_command(self, command: str) -> str:
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        TuskAgentBackend(BrokenAgent()).run(AgentRequest("open", "command"))
