import types

from shells.voice.voice_shell import VoiceShell
from tusk.shared.schemas.kernel_response import KernelResponse


def test_voice_shell_speaks_replies() -> None:
    spoken: list[str] = []
    played: list[bytes] = []
    shell = _shell(_tts(spoken), _playback(played), [KernelResponse(True, "hello there")])
    shell.start(lambda text: None)
    assert spoken == ["hello there"]
    assert played == [b"WAVDATA"]


def test_voice_shell_survives_tts_failures() -> None:
    logs: list[tuple] = []
    shell = _shell(_broken_tts(), _playback([]), [KernelResponse(True, "hello")], logs)
    shell.start(lambda text: None)
    assert any(entry[0] == "ERROR" for entry in logs)


def test_voice_shell_stays_silent_without_tts_engine() -> None:
    played: list[bytes] = []
    shell = _shell(None, _playback(played), [KernelResponse(True, "hello")])
    shell.start(lambda text: None)
    assert played == []


def _shell(tts_engine: object | None, playback: object, responses: list[KernelResponse], logs: list | None = None) -> VoiceShell:
    log = types.SimpleNamespace(log=lambda *args: logs.append(args) if logs is not None else None)
    pipeline = types.SimpleNamespace(run=lambda submit: iter(responses))
    return VoiceShell(None, log, pipeline=pipeline, tts_engine=tts_engine, playback=playback)


def _tts(spoken: list[str]) -> object:
    return types.SimpleNamespace(synthesize=lambda text: spoken.append(text) or b"WAVDATA")


def _broken_tts() -> object:
    def synthesize(text: str) -> bytes:
        raise RuntimeError("tts unavailable")

    return types.SimpleNamespace(synthesize=synthesize)


def _playback(played: list[bytes]) -> object:
    return types.SimpleNamespace(play=lambda wav_bytes: played.append(wav_bytes))
