import types

import pytest

from shells.voice import voice_shell
from tusk.shared.schemas.kernel_response import KernelResponse


def test_voice_shell_logs_reply_from_submitter(monkeypatch) -> None:
    logged: list[tuple] = []
    monkeypatch.setattr(voice_shell, "VoicePipeline", lambda *args: _pipeline())
    log = types.SimpleNamespace(log=lambda *args: logged.append(args))
    shell = voice_shell.VoiceShell(_config(), log, stt_engine=object(), gatekeeper=object())
    shell.start(lambda text: KernelResponse(True, f"Hello from TUSK: {text}"))
    assert logged == [("TUSK", "Hello from TUSK: open Firefox")]


def test_voice_shell_requires_stt_engine() -> None:
    with pytest.raises(ValueError):
        voice_shell.VoiceShell(_config(), _log(), gatekeeper=object())


def test_voice_shell_requires_gatekeeper() -> None:
    with pytest.raises(ValueError):
        voice_shell.VoiceShell(_config(), _log(), stt_engine=object())


def _config() -> object:
    return types.SimpleNamespace(
        audio_sample_rate=16000, audio_frame_duration_ms=30, vad_aggressiveness=2,
        gate_recovery_window_seconds=60.0, gate_recovery_candidate_limit=6,
    )


def _log() -> object:
    return types.SimpleNamespace(log=lambda *args: None)


def _pipeline() -> object:
    return types.SimpleNamespace(run=lambda submit: [submit("open Firefox")])
