import threading
import types

from shells.voice.command_worker import CommandWorker
from shells.voice.queued_command import QueuedCommand
from tusk.shared.interrupt import InterruptToken
from tusk.shared.schemas.kernel_response import KernelResponse


def test_enqueue_clears_stale_interrupt_before_new_job() -> None:
    token = InterruptToken()
    token.interrupt()
    worker = CommandWorker(None, _playback(), _log(), token)
    worker.enqueue("next")
    assert token.is_interrupted is False


def test_handle_skips_command_interrupted_before_execution() -> None:
    token = InterruptToken()
    seen: list[str] = []
    token.interrupt()
    worker = CommandWorker(None, _playback(), _log(), token)
    worker._handle(QueuedCommand("next"), lambda text: seen.append(text) or KernelResponse(True, ""))
    assert seen == []


def test_enqueue_while_busy_preserves_running_interrupt() -> None:
    started, release = threading.Event(), threading.Event()
    token = InterruptToken()
    worker = CommandWorker(None, _playback(), _log(), token)
    worker.start(_blocking_submit(started, release))
    worker.enqueue("first")
    assert started.wait(timeout=1.0)
    token.interrupt()
    worker.enqueue("second")
    assert token.is_interrupted is True
    release.set()


def _blocking_submit(started: threading.Event, release: threading.Event) -> object:
    def submit(text: str) -> KernelResponse:
        started.set()
        release.wait(timeout=1.0)
        return KernelResponse(True, "")

    return submit


def _playback() -> object:
    return types.SimpleNamespace(play=lambda wav: None)


def _log() -> object:
    return types.SimpleNamespace(log=lambda *args: None)
