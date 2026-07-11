from tusk.kernel.agent.backends import AgentRequest
from tusk.kernel.core.command_mode import CommandMode
from tests.null_log_printer import NullLogPrinter
from tests.recording_backend import RecordingBackend


def test_command_mode_sends_command_agent_request() -> None:
    backend = RecordingBackend()
    response = CommandMode(backend, NullLogPrinter()).process_command("open browser", "command")
    assert backend.requests[0] == AgentRequest(user_text="open browser", mode="command")
    assert response.handled is True
    assert response.reply == "Done."


def test_command_mode_keeps_commands_one_shot() -> None:
    backend = RecordingBackend()
    command_mode = CommandMode(backend, NullLogPrinter())
    command_mode.process_command("open browser", "command")
    command_mode.process_command("close browser", "command")
    assert backend.requests[1].session_id == ""


def test_command_mode_propagates_session_id_for_conversation() -> None:
    backend = RecordingBackend()
    command_mode = CommandMode(backend, NullLogPrinter())
    command_mode.process_command("hello", "conversation")
    command_mode.process_command("again", "conversation")
    assert backend.requests[1].session_id == "next-session"
