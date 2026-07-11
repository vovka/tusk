import threading
import time
import types

from shells.voice.command_worker import CommandWorker
from shells.voice.stages.chunked_speaker import ChunkedSpeaker
from tusk.shared.interrupt import InterruptToken
from tusk.shared.schemas.kernel_response import KernelResponse


def make_worker(submit, tts=None, playback=None, token=None, logs=None, ack_enabled=True) -> CommandWorker:
    log = types.SimpleNamespace(log=lambda *args: logs.append(args) if logs is not None else None)
    playback = playback or types.SimpleNamespace(play=lambda wav: None)
    speaker = ChunkedSpeaker(tts, playback, log)
    worker = CommandWorker(submit, speaker, log, token or InterruptToken(), ack_enabled)
    worker.start()
    return worker


def recording_submit(submits: list[str]):
    def submit(text: str) -> KernelResponse:
        submits.append(text)
        return KernelResponse(True, "a reply")
    return submit


def blocking_submit(release: threading.Event, submits: list[str], started: threading.Event | None = None):
    def submit(text: str) -> KernelResponse:
        if started is not None:
            started.set()
        assert release.wait(timeout=5.0)
        submits.append(text)
        return KernelResponse(True, "a reply")
    return submit


def failing_then_recording_submit(submits: list[str]):
    def submit(text: str) -> KernelResponse:
        if text == "boom":
            raise RuntimeError("kernel exploded")
        submits.append(text)
        return KernelResponse(True, "a reply")
    return submit


def interrupting_submit(token: InterruptToken, reply: str):
    def submit(text: str) -> KernelResponse:
        token.interrupt()
        return KernelResponse(True, reply)
    return submit


def working_tts() -> object:
    return types.SimpleNamespace(synthesize_chunks=lambda text: iter([b"WAVDATA"]))


def broken_tts() -> object:
    def synthesize_chunks(text: str):
        raise RuntimeError("tts unavailable")
        yield b""

    return types.SimpleNamespace(synthesize_chunks=synthesize_chunks)


def await_condition(condition, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return
        time.sleep(0.005)
    raise AssertionError("condition not met within timeout")
