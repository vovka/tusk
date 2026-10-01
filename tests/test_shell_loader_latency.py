import types

from shell_loader import ShellLoader


def test_voice_shell_receives_speech_end_callback() -> None:
    on_speech_end = lambda seconds_ago: None
    loader = ShellLoader(types.SimpleNamespace(), object(), object(), object(), on_speech_end)
    loader._stt_engine = lambda: object()
    loader._build_worker = lambda: types.SimpleNamespace(recent_speech="")
    loader._gatekeeper = lambda worker: None
    shell = loader._build_voice(lambda *args, **kwargs: kwargs)
    assert shell["on_speech_end"] is on_speech_end
