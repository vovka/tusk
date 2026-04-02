import types

from shells.voice import voice_shell
from tusk.shared.schemas.kernel_response import KernelResponse


def test_voice_shell_logs_reply_from_submitter(monkeypatch) -> None:
    logged: list[tuple] = []
    monkeypatch.setattr(voice_shell, "VoicePipeline", lambda *args: _pipeline())
    shell = voice_shell.VoiceShell(_config(), types.SimpleNamespace(log=lambda *args: logged.append(args)))
    shell.start(lambda text: KernelResponse(True, f"Hello from TUSK: {text}"))
    assert logged == [("TUSK", "Hello from TUSK: open Firefox")]


def _config() -> object:
    return types.SimpleNamespace(audio_sample_rate=16000, audio_frame_duration_ms=30, vad_aggressiveness=2)


def _pipeline() -> object:
    return types.SimpleNamespace(run=lambda submit: [submit("open Firefox")])
