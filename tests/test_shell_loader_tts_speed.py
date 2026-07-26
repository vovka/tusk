import shell_loader
from tests.test_shell_loader import _loader, _patch_stt, _voice_class


def _patch_speech_playback_capture(monkeypatch, captured: list[float]) -> None:
    real_playback = shell_loader.SpeechPlayback
    monkeypatch.setattr(
        shell_loader, "SpeechPlayback",
        lambda token, speed=1.0: captured.append(speed) or real_playback(token, speed=speed),
    )


def test_speech_playback_receives_configured_tts_speed(monkeypatch) -> None:
    _patch_stt(monkeypatch, object())
    captured: list[float] = []
    _patch_speech_playback_capture(monkeypatch, captured)
    loader = _loader(["voice"])
    loader._config.tts_speed = 2.0
    loader._gatekeeper = lambda worker: None
    loader._load_class = lambda name: _voice_class()
    loader._build("voice")
    assert captured == [2.0]
