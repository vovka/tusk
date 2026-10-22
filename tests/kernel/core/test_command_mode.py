import types

from tusk.kernel.agent.backends import BackendRequest
from tusk.kernel.core.command_mode import CommandMode
from tusk.shared.schemas.kernel_response import KernelResponse
from tests.support.recording_log_printer import RecordingLogPrinter
from tests.support.recording_backend import RecordingBackend


def _gate(resolved: KernelResponse | None = None, question: str | None = None) -> object:
    return types.SimpleNamespace(resolve=lambda text: resolved, take_question=lambda: question)


def test_command_mode_sends_command_agent_request() -> None:
    backend = RecordingBackend()
    response = CommandMode(backend, RecordingLogPrinter(), _gate()).process_command("open browser", "command")
    assert backend.requests[0] == BackendRequest(user_text="open browser", mode="command")
    assert response.handled is True
    assert response.reply == "Done."


def test_command_mode_keeps_commands_one_shot() -> None:
    backend = RecordingBackend()
    command_mode = CommandMode(backend, RecordingLogPrinter(), _gate())
    command_mode.process_command("open browser", "command")
    command_mode.process_command("close browser", "command")
    assert backend.requests[1].session_id == ""


def test_command_mode_propagates_session_id_for_conversation() -> None:
    backend = RecordingBackend()
    command_mode = CommandMode(backend, RecordingLogPrinter(), _gate())
    command_mode.process_command("hello", "conversation")
    command_mode.process_command("again", "conversation")
    assert backend.requests[1].session_id == "next-session"


def test_confirmation_reply_skips_agent() -> None:
    backend = RecordingBackend()
    mode = CommandMode(backend, RecordingLogPrinter(), _gate(resolved=KernelResponse(True, "Confirmed.")))
    assert mode.process_command("yes", "command").reply == "Confirmed."
    assert backend.requests == []


def test_new_question_replaces_agent_reply() -> None:
    backend = RecordingBackend()
    mode = CommandMode(backend, RecordingLogPrinter(), _gate(question="Close window 'X'? Say 'Tusk, yes' to confirm."))
    assert mode.process_command("close X", "command").reply == "Close window 'X'? Say 'Tusk, yes' to confirm."
    assert backend.requests[0].user_text == "close X"
