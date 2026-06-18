from tusk.kernel.agent_backends import AgentRequest
from tusk.kernel.command_mode import CommandMode
from tests.null_log_printer import NullLogPrinter
from tests.recording_backend import RecordingBackend


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
    assert backend.requests[1] == AgentRequest(
        user_text="close browser",
        mode="command",
        session_id="next-session",
    )
