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


def _popen(calls: list[list[str]], writes: list[bytes], polls: list[int | None]) -> object:
    def create(args: list[str], **kwargs: object) -> object:
        calls.append(args)
        stdin = types.SimpleNamespace(write=writes.append, close=lambda: None)
        return types.SimpleNamespace(stdin=stdin, poll=lambda: polls.pop(0), terminate=lambda: None, wait=lambda timeout: None)

    return create


def _interrupting_popen(events: list[str]) -> object:
    def create(*args: object, **kwargs: object) -> object:
        stdin = types.SimpleNamespace(write=lambda wav: None, close=lambda: None)
        return types.SimpleNamespace(stdin=stdin, poll=lambda: None, terminate=lambda: events.append("terminate"), wait=lambda timeout: None)

    return create
