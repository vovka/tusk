import shells.voice.stages.speech_playback as playback_module
from shells.voice.stages.speech_playback import SpeechPlayback
from tests.shells.voice.test_speech_playback import _FakeProcess, _await_written


class _FakeStretchProcess:
    def __init__(self, output: bytes = b"STRETCHED", returncode: int = 0) -> None:
        self.stdin = self
        self.written = b""
        self._output = output
        self.returncode = returncode

    def write(self, data: bytes) -> None:
        self.written += data

    def close(self) -> None:
        pass

    def communicate(self) -> tuple:
        return self._output, b""


def _patch_ffmpeg_and_paplay(monkeypatch, paplay_process: object, ffmpeg_effect) -> list[tuple]:
    calls: list[tuple] = []

    def popen(command, **kwargs):
        calls.append((command, kwargs))
        return ffmpeg_effect(command) if command[0] == "ffmpeg" else paplay_process

    monkeypatch.setattr(playback_module.subprocess, "Popen", popen)
    return calls


def test_playback_speed_stretches_through_ffmpeg(monkeypatch) -> None:
    paplay_process = _FakeProcess(polls_to_finish=1)
    stretch_process = _FakeStretchProcess(output=b"STRETCHED")
    calls = _patch_ffmpeg_and_paplay(monkeypatch, paplay_process, lambda command: stretch_process)
    SpeechPlayback(speed=2.0, poll_seconds=0.01).play(b"WAVDATA")
    assert len(calls) == 2
    assert calls[0][0][0] == "ffmpeg"
    assert "atempo=2.0" in " ".join(calls[0][0])
    _await_written(paplay_process)
    assert paplay_process.written == b"STRETCHED"


def test_playback_falls_back_to_original_bytes_when_ffmpeg_exits_non_zero(monkeypatch) -> None:
    paplay_process = _FakeProcess(polls_to_finish=1)
    stretch_process = _FakeStretchProcess(output=b"", returncode=1)
    _patch_ffmpeg_and_paplay(monkeypatch, paplay_process, lambda command: stretch_process)
    SpeechPlayback(speed=2.0, poll_seconds=0.01).play(b"WAVDATA")
    _await_written(paplay_process)
    assert paplay_process.written == b"WAVDATA"


def _raise_ffmpeg_missing(command: list[str]) -> object:
    raise OSError("ffmpeg not found")


def test_playback_falls_back_to_original_bytes_when_ffmpeg_missing(monkeypatch) -> None:
    paplay_process = _FakeProcess(polls_to_finish=1)
    _patch_ffmpeg_and_paplay(monkeypatch, paplay_process, _raise_ffmpeg_missing)
    SpeechPlayback(speed=2.0, poll_seconds=0.01).play(b"WAVDATA")
    _await_written(paplay_process)
    assert paplay_process.written == b"WAVDATA"
