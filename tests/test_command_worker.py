import threading
import types

from shells.voice.command_worker import CommandWorker
from tusk.shared.interrupt import InterruptToken
from tusk.shared.schemas.kernel_response import KernelResponse


def test_enqueue_returns_while_submitter_is_busy() -> None:
    started, release = threading.Event(), threading.Event()
    seen: list[str] = []
    worker = CommandWorker(None, _playback([]), _log(), InterruptToken())
    worker.start(_blocking_submit(started, release, seen))
    worker.enqueue("first")
    assert started.wait(timeout=1.0)
    worker.enqueue("second")
    release.set()
    assert _eventually(lambda: seen == ["first", "second"])


def test_flush_drops_pending_commands() -> None:
    started, release = threading.Event(), threading.Event()
    seen: list[str] = []
    worker = CommandWorker(None, _playback([]), _log(), InterruptToken())
    worker.start(_blocking_submit(started, release, seen))
    worker.enqueue("first")
    assert started.wait(timeout=1.0)
    worker.enqueue("second")
    worker.flush()
    release.set()
    assert _eventually(lambda: seen == ["first"])


def test_current_speech_text_is_set_only_while_speaking() -> None:
    played: list[str | None] = []
    box: dict[str, CommandWorker] = {}
    worker = CommandWorker(_tts(), _playback(played, box), _log(), InterruptToken())
    box["worker"] = worker
    worker.start(lambda text: KernelResponse(True, "hello"))
    worker.enqueue("speak")
    assert _eventually(lambda: played == ["hello"])
    assert worker.current_speech_text is None


def test_worker_survives_submit_failure() -> None:
    logs: list[tuple[str, str]] = []
    seen: list[str] = []
    worker = CommandWorker(None, _playback([]), _log(logs), InterruptToken())
    worker.start(_flaky_submit(seen))
    worker.enqueue("bad")
    worker.enqueue("good")
    assert _eventually(lambda: seen == ["bad", "good"])
    assert any(tag == "ERROR" for tag, message in logs)


def _blocking_submit(started: threading.Event, release: threading.Event, seen: list[str]) -> object:
    def submit(text: str) -> KernelResponse:
        started.set()
        release.wait(timeout=1.0)
        seen.append(text)
        return KernelResponse(True, "")

    return submit


def _flaky_submit(seen: list[str]) -> object:
    def submit(text: str) -> KernelResponse:
        seen.append(text)
        if text == "bad":
            raise RuntimeError("boom")
        return KernelResponse(True, "")

    return submit


def _eventually(condition: object) -> bool:
    done = threading.Event()
    for _ in range(20):
        if condition():
            return True
        done.wait(timeout=0.05)
    return False


def _tts() -> object:
    return types.SimpleNamespace(synthesize=lambda text: b"WAVDATA")


def _playback(played: list[str | None], box: dict[str, CommandWorker] | None = None) -> object:
    return types.SimpleNamespace(play=lambda wav: played.append(_current_text(box)))


def _current_text(box: dict[str, CommandWorker] | None) -> str | None:
    return None if box is None else box["worker"].current_speech_text


def _log(entries: list[tuple[str, str]] | None = None) -> object:
    return types.SimpleNamespace(log=lambda tag, message, *args: _capture(entries, tag, message))


def _capture(entries: list[tuple[str, str]] | None, tag: str, message: str) -> None:
    if entries is not None:
        entries.append((tag, message))
