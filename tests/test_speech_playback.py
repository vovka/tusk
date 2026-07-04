import threading
import types

import shells.voice.stages.speech_playback as playback_module
from shells.voice.stages.speech_playback import SpeechPlayback
from tusk.shared.interrupt import InterruptToken


def test_playback_pipes_wav_bytes_to_paplay(monkeypatch) -> None:
    calls: list[list[str]] = []
    writes: list[bytes] = []
    monkeypatch.setattr(playback_module.subprocess, "Popen", _popen(calls, writes, [0]))
    SpeechPlayback().play(b"WAVDATA")
    assert calls == [["paplay"]]
    assert writes == [b"WAVDATA"]


def test_playback_terminates_when_interrupted(monkeypatch) -> None:
    token = InterruptToken()
    events: list[str] = []
    monkeypatch.setattr(playback_module.subprocess, "Popen", _interrupting_popen(events))
    token.interrupt()
    SpeechPlayback(token).play(b"WAVDATA")
    assert "terminate" in events


def test_playback_polls_interrupt_while_write_blocks(monkeypatch) -> None:
    token = InterruptToken()
    events: list[str] = []
    release = threading.Event()
    monkeypatch.setattr(playback_module.subprocess, "Popen", _blocking_write_popen(events, release))
    thread = _play_async(token)
    assert _eventually(lambda: "write-started" in events)
    token.interrupt()
    assert _eventually(lambda: "terminate" in events)
    release.set()
    thread.join(timeout=1.0)


def test_playback_kills_when_terminate_times_out(monkeypatch) -> None:
    token = InterruptToken()
    events: list[str] = []
    monkeypatch.setattr(playback_module.subprocess, "Popen", _timeout_popen(events))
    token.interrupt()
    SpeechPlayback(token).play(b"WAVDATA")
    assert events == ["terminate", "kill", "wait"]


def _play_async(token: InterruptToken) -> threading.Thread:
    thread = threading.Thread(target=lambda: SpeechPlayback(token, poll_interval=0.01).play(b"WAVDATA"), daemon=True)
    thread.start()
    return thread


def _popen(calls: list[list[str]], writes: list[bytes], polls: list[int | None]) -> object:
    def create(args: list[str], **kwargs: object) -> object:
        calls.append(args)
        stdin = types.SimpleNamespace(write=writes.append, close=lambda: None)
        return types.SimpleNamespace(stdin=stdin, poll=lambda: polls.pop(0), terminate=lambda: None, wait=lambda timeout: None)

    return create


def _blocking_write_popen(events: list[str], release: threading.Event) -> object:
    def create(*args: object, **kwargs: object) -> object:
        stdin = types.SimpleNamespace(write=_blocking_write(events, release), close=lambda: None)
        return types.SimpleNamespace(stdin=stdin, poll=lambda: None, terminate=lambda: events.append("terminate"), wait=lambda timeout: None)

    return create


def _blocking_write(events: list[str], release: threading.Event) -> object:
    def write(wav: bytes) -> None:
        events.append("write-started")
        release.wait(timeout=2.0)

    return write


def _timeout_popen(events: list[str]) -> object:
    def create(*args: object, **kwargs: object) -> object:
        stdin = types.SimpleNamespace(write=lambda wav: None, close=lambda: None)
        return types.SimpleNamespace(stdin=stdin, poll=lambda: None, terminate=lambda: events.append("terminate"), kill=lambda: events.append("kill"), wait=_timeout_wait(events))

    return create


def _timeout_wait(events: list[str]) -> object:
    def wait(timeout: float | None = None) -> None:
        if timeout is not None:
            raise playback_module.subprocess.TimeoutExpired("paplay", timeout)
        events.append("wait")

    return wait


def _interrupting_popen(events: list[str]) -> object:
    def create(*args: object, **kwargs: object) -> object:
        stdin = types.SimpleNamespace(write=lambda wav: None, close=lambda: None)
        return types.SimpleNamespace(stdin=stdin, poll=lambda: None, terminate=lambda: events.append("terminate"), wait=lambda timeout: None)

    return create


def _eventually(condition: object) -> bool:
    done = threading.Event()
    for _ in range(20):
        if condition():
            return True
        done.wait(timeout=0.05)
    return False
