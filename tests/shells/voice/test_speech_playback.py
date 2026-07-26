import subprocess
import time

import shells.voice.stages.speech_playback as playback_module
from shells.voice.stages.speech_playback import SpeechPlayback
from tusk.shared.interrupt import InterruptToken


class _FakeProcess:
    def __init__(self, polls_to_finish: int, fail_writes: bool = False) -> None:
        self._polls_left = polls_to_finish
        self._fail_writes = fail_writes
        self.terminated = False
        self.closed = False
        self.written = b""
        self.stdin = self

    def write(self, data: bytes) -> None:
        if self._fail_writes:
            raise OSError("broken pipe")
        self.written += data

    def close(self) -> None:
        self.closed = True

    def __enter__(self) -> "_FakeProcess":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        self.close()
        return False

    def wait(self, timeout: float) -> int:
        if self.terminated:
            return 0
        self._polls_left -= 1
        if self._polls_left <= 0:
            return 0
        raise subprocess.TimeoutExpired("paplay", timeout)

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.terminated = True


def _patch_popen(monkeypatch, process: _FakeProcess) -> list[tuple]:
    calls: list[tuple] = []
    def popen(command, stdin=None):
        calls.append((command, stdin))
        return process
    monkeypatch.setattr(playback_module.subprocess, "Popen", popen)
    return calls


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

    def __enter__(self) -> "_FakeStretchProcess":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return False

    def communicate(self) -> tuple:
        return self._output, b""


def test_playback_pipes_wav_bytes_to_paplay(monkeypatch) -> None:
    process = _FakeProcess(polls_to_finish=1)
    calls = _patch_popen(monkeypatch, process)
    SpeechPlayback(poll_seconds=0.01).play(b"WAVDATA")
    assert calls[0][0] == ["paplay"]
    assert calls[0][1] == subprocess.PIPE
    _await_written(process)
    assert process.written == b"WAVDATA"


def test_playback_completes_without_terminate_when_uninterrupted(monkeypatch) -> None:
    process = _FakeProcess(polls_to_finish=3)
    _patch_popen(monkeypatch, process)
    SpeechPlayback(InterruptToken(), poll_seconds=0.01).play(b"WAVDATA")
    assert not process.terminated


def test_playback_terminates_when_token_interrupted(monkeypatch) -> None:
    process = _FakeProcess(polls_to_finish=1000)
    _patch_popen(monkeypatch, process)
    token = InterruptToken()
    token.interrupt()
    SpeechPlayback(token, poll_seconds=0.01).play(b"WAVDATA")
    assert process.terminated


def test_feed_closes_stdin_when_write_fails() -> None:
    process = _FakeProcess(polls_to_finish=1, fail_writes=True)
    playback_module._feed(process, b"WAVDATA")
    assert process.closed


def _await_written(process: object) -> None:
    for _ in range(100):
        if process.written:
            return
        time.sleep(0.01)


def test_playback_speed_one_skips_ffmpeg(monkeypatch) -> None:
    process = _FakeProcess(polls_to_finish=1)
    calls = _patch_popen(monkeypatch, process)
    SpeechPlayback(speed=1.0, poll_seconds=0.01).play(b"WAVDATA")
    assert len(calls) == 1
    assert calls[0][0] == ["paplay"]


def test_playback_speed_stretches_through_ffmpeg(monkeypatch) -> None:
    paplay_process = _FakeProcess(polls_to_finish=1)
    stretch_process = _FakeStretchProcess(output=b"STRETCHED")
    calls: list[tuple] = []

    def popen(command, **kwargs):
        calls.append((command, kwargs))
        return stretch_process if command[0] == "ffmpeg" else paplay_process

    monkeypatch.setattr(playback_module.subprocess, "Popen", popen)
    SpeechPlayback(speed=2.0, poll_seconds=0.01).play(b"WAVDATA")
    assert len(calls) == 2
    assert calls[0][0][0] == "ffmpeg"
    assert "atempo=2.0" in " ".join(calls[0][0])
    _await_written(paplay_process)
    assert paplay_process.written == b"STRETCHED"


def test_playback_falls_back_to_original_bytes_when_ffmpeg_exits_non_zero(monkeypatch) -> None:
    paplay_process = _FakeProcess(polls_to_finish=1)
    stretch_process = _FakeStretchProcess(output=b"", returncode=1)

    def popen(command, **kwargs):
        return stretch_process if command[0] == "ffmpeg" else paplay_process

    monkeypatch.setattr(playback_module.subprocess, "Popen", popen)
    SpeechPlayback(speed=2.0, poll_seconds=0.01).play(b"WAVDATA")
    _await_written(paplay_process)
    assert paplay_process.written == b"WAVDATA"


def test_playback_falls_back_to_original_bytes_when_ffmpeg_missing(monkeypatch) -> None:
    paplay_process = _FakeProcess(polls_to_finish=1)

    def popen(command, **kwargs):
        if command[0] == "ffmpeg":
            raise OSError("ffmpeg not found")
        return paplay_process

    monkeypatch.setattr(playback_module.subprocess, "Popen", popen)
    SpeechPlayback(speed=2.0, poll_seconds=0.01).play(b"WAVDATA")
    _await_written(paplay_process)
    assert paplay_process.written == b"WAVDATA"


def test_atempo_filter_chain_within_native_range() -> None:
    assert SpeechPlayback._atempo_filter_chain(1.5) == "atempo=1.5"
    assert SpeechPlayback._atempo_filter_chain(2.0) == "atempo=2.0"


def test_atempo_filter_chain_above_native_range() -> None:
    assert SpeechPlayback._atempo_filter_chain(3.0) == "atempo=2.0,atempo=1.5"
    assert SpeechPlayback._atempo_filter_chain(4.0) == "atempo=2.0,atempo=2.0"
