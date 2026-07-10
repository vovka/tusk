import pytest

from tusk.kernel.agent.backends import AgentRequest, AgentResult
from tusk.kernel.agent.backends.tusk_agent_backend import TuskAgentBackend


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
    request = AgentRequest("open browser", "command", "session-1", metadata={"trace_id": "abc"})
    result = TuskAgentBackend(agent).run(request)
    assert agent.commands == ["open browser"]
    assert result.status == "success"
    assert result.final_text == "Done."
    assert result.reply == "Done."
    assert result.handled is True
    assert result.metadata == {"trace_id": "abc", "backend": "tusk", "mode": "command"}


def test_tusk_agent_backend_rejects_missing_agent() -> None:
    with pytest.raises(ValueError, match="agent cannot be None"):
        TuskAgentBackend(None)


def test_tusk_agent_backend_rejects_missing_request() -> None:
    with pytest.raises(ValueError, match="request cannot be None"):
        TuskAgentBackend(RecordingAgent()).run(None)


def test_tusk_agent_backend_lets_programmer_errors_surface() -> None:
    class BrokenAgent:
        def process_command(self, command: str) -> str:
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        TuskAgentBackend(BrokenAgent()).run(AgentRequest("open", "command"))


def test_agent_result_uses_empty_string_when_reply_is_missing() -> None:
    result = AgentResult(True, None)
    assert result.final_text == ""

