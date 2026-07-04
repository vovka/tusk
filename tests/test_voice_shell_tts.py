import threading
import types

from shells.voice.command_worker import CommandWorker
from tusk.shared.interrupt import InterruptToken
from tusk.shared.schemas.kernel_response import KernelResponse


def test_command_worker_speaks_replies() -> None:
    spoken: list[str] = []
    played: list[bytes] = []
    worker = _worker(_tts(spoken), _playback(played))
    worker.start(lambda text: KernelResponse(True, "hello there"))
    worker.enqueue("hello")
    assert _eventually(lambda: played == [b"WAVDATA"])
    assert spoken == ["hello there"]


def test_command_worker_survives_tts_failures() -> None:
    logs: list[tuple] = []
    worker = _worker(_broken_tts(), _playback([]), logs)
    worker.start(lambda text: KernelResponse(True, "hello"))
    worker.enqueue("hello")
    assert _eventually(lambda: any(entry[0] == "ERROR" for entry in logs))
    assert any(entry[0] == "ERROR" for entry in logs)


def test_command_worker_stays_silent_without_tts_engine() -> None:
    played: list[bytes] = []
    worker = _worker(None, _playback(played))
    worker.start(lambda text: KernelResponse(True, "hello"))
    worker.enqueue("hello")
    assert _eventually(lambda: worker.is_busy is False)
    assert played == []


def _worker(tts_engine: object | None, playback: object, logs: list | None = None) -> CommandWorker:
    log = types.SimpleNamespace(log=lambda *args: logs.append(args) if logs is not None else None)
    return CommandWorker(tts_engine, playback, log, InterruptToken())


def _tts(spoken: list[str]) -> object:
    return types.SimpleNamespace(synthesize=lambda text: spoken.append(text) or b"WAVDATA")


def _broken_tts() -> object:
    def synthesize(text: str) -> bytes:
        raise RuntimeError("tts unavailable")

    return types.SimpleNamespace(synthesize=synthesize)


def _playback(played: list[bytes]) -> object:
    return types.SimpleNamespace(play=lambda wav_bytes: played.append(wav_bytes))


def _eventually(condition: object) -> bool:
    pause = threading.Event()
    for _ in range(20):
        if condition():
            return True
        pause.wait(timeout=0.05)
    return False
