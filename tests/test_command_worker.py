import threading
import time
import types

from shells.voice.command_worker import CommandWorker
from tusk.shared.interrupt import InterruptToken
from tusk.shared.schemas.kernel_response import KernelResponse


def test_enqueue_returns_before_submit_completes() -> None:
    release = threading.Event()
    submits: list[str] = []
    worker = _worker(_blocking_submit(release, submits))
    worker.enqueue("open Firefox")
    assert submits == []
    release.set()
    _await(lambda: submits == ["open Firefox"])


def test_commands_run_sequentially_in_order() -> None:
    submits: list[str] = []
    worker = _worker(_recording_submit(submits))
    worker.enqueue("first")
    worker.enqueue("second")
    _await(lambda: submits == ["first", "second"])


def test_flush_drops_queued_commands() -> None:
    release, started = threading.Event(), threading.Event()
    submits: list[str] = []
    worker = _worker(_blocking_submit(release, submits, started))
    worker.enqueue("running")
    assert started.wait(timeout=5.0)
    worker.enqueue("queued")
    worker.flush()
    release.set()
    _await(lambda: submits == ["running"] and not worker.is_busy)
    assert submits == ["running"]


def test_is_busy_only_while_processing() -> None:
    release = threading.Event()
    worker = _worker(_blocking_submit(release, []))
    assert not worker.is_busy
    worker.enqueue("open Firefox")
    _await(lambda: worker.is_busy)
    release.set()
    _await(lambda: not worker.is_busy)


def test_current_speech_text_set_only_while_speaking() -> None:
    seen: list[str | None] = []
    playback = types.SimpleNamespace(play=lambda wav: seen.append(worker.current_speech_text))
    worker = _worker(_recording_submit([]), tts=_tts(), playback=playback)
    worker.enqueue("hi")
    _await(lambda: bool(seen))
    assert seen == ["a reply"]
    _await(lambda: worker.current_speech_text is None)


def test_token_cleared_when_job_starts() -> None:
    token = InterruptToken()
    token.interrupt()
    worker = _worker(_recording_submit([]), token=token)
    worker.enqueue("hi")
    _await(lambda: not token.is_interrupted)


def test_worker_logs_reply_and_survives_tts_failure() -> None:
    logs: list[tuple] = []
    worker = _worker(_recording_submit([]), tts=_broken_tts(), logs=logs)
    worker.enqueue("hi")
    _await(lambda: any(entry[0] == "ERROR" for entry in logs))
    assert ("TUSK", "a reply") in logs


def _worker(submit, tts=None, playback=None, token=None, logs=None) -> CommandWorker:
    log = types.SimpleNamespace(log=lambda *args: logs.append(args) if logs is not None else None)
    playback = playback or types.SimpleNamespace(play=lambda wav: None)
    worker = CommandWorker(submit, tts, playback, log, token or InterruptToken())
    worker.start()
    return worker


def _recording_submit(submits: list[str]):
    def submit(text: str) -> KernelResponse:
        submits.append(text)
        return KernelResponse(True, "a reply")
    return submit


def _blocking_submit(release: threading.Event, submits: list[str], started: threading.Event | None = None):
    def submit(text: str) -> KernelResponse:
        if started is not None:
            started.set()
        assert release.wait(timeout=5.0)
        submits.append(text)
        return KernelResponse(True, "a reply")
    return submit


def _tts() -> object:
    return types.SimpleNamespace(synthesize=lambda text: b"WAVDATA")


def _broken_tts() -> object:
    def synthesize(text: str) -> bytes:
        raise RuntimeError("tts unavailable")
    return types.SimpleNamespace(synthesize=synthesize)


def _await(condition, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return
        time.sleep(0.005)
    raise AssertionError("condition not met within timeout")
