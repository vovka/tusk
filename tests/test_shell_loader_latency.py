import types

from shell_loader import ShellLoader
from voice_shell_builder import VoiceShellBuilder


def test_voice_shell_receives_speech_end_callback(monkeypatch) -> None:
    on_speech_end = lambda seconds_ago: None
    loader = ShellLoader(types.SimpleNamespace(stt_app_vocabulary=False), object(), object(), object(), on_speech_end)
    monkeypatch.setattr(VoiceShellBuilder, "stt_engine", lambda self: object())
    monkeypatch.setattr(VoiceShellBuilder, "worker", lambda self: types.SimpleNamespace(recent_speech=""))
    monkeypatch.setattr(VoiceShellBuilder, "gatekeeper", lambda self, worker: None)
    shell = loader._build_voice(lambda *args, **kwargs: kwargs)
    assert shell["on_speech_end"] is on_speech_end
