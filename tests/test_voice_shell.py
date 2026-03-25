import types

from shells.voice import voice_shell
from tusk.kernel.schemas.kernel_response import KernelResponse


def test_voice_shell_logs_reply_from_kernel(monkeypatch) -> None:
    logged: list[tuple] = []
    monkeypatch.setattr(voice_shell, "AudioCapture", lambda *args: object())
    monkeypatch.setattr(voice_shell, "UtteranceDetector", lambda *args: _detector())
    shell = voice_shell.VoiceShell(_config(), types.SimpleNamespace(log=lambda *args: logged.append(args)))
    shell.start(types.SimpleNamespace(submit_utterance=lambda *args: KernelResponse(True, "Hello from TUSK")))
    assert logged == [("TUSK", "Hello from TUSK")]


def _config() -> object:
    return types.SimpleNamespace(audio_sample_rate=16000, audio_frame_duration_ms=30, vad_aggressiveness=2)


def _detector() -> object:
    utterance = types.SimpleNamespace(audio_frames=b"audio")
    return types.SimpleNamespace(stream_utterances=lambda: iter([utterance]))
