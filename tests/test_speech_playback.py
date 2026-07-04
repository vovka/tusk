import subprocess
import time

import shells.voice.stages.speech_playback as playback_module
from shells.voice.stages.speech_playback import SpeechPlayback
from tusk.shared.interrupt import InterruptToken


class _FakeProcess:
    def __init__(self, polls_to_finish: int) -> None:
        self._polls_left = polls_to_finish
        self.terminated = False
        self.written = b""
        self.stdin = self

    def write(self, data: bytes) -> None:
        self.written += data

    def close(self) -> None:
        pass

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


def _await_written(process: _FakeProcess) -> None:
    for _ in range(100):
        if process.written:
            return
        time.sleep(0.01)
