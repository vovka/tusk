from tests.recording_backend import RecordingBackend
from tusk.kernel.core.command_mode import CommandMode
from tusk.shared.logging.interfaces.log_printer import LogPrinter


class _NullLog(LogPrinter):
    def log(self, tag: str, message: str, group: str | None = None) -> None:
        return None

    def show_wait(self, label: str, group: str = "wait") -> None:
        return None

    def clear_wait(self) -> None:
        return None


def test_command_kind_becomes_agent_request_mode() -> None:
    backend = RecordingBackend()
    CommandMode(backend, _NullLog()).process_command("open gedit", "command")
    assert backend.requests[0].mode == "command"


def test_kind_defaults_to_conversation() -> None:
    backend = RecordingBackend()
    CommandMode(backend, _NullLog()).process_command("hello there")
    assert backend.requests[0].mode == "conversation"
