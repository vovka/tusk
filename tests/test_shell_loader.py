import types

import shell_loader
from shell_loader import ShellLoader
from tusk.shared.interrupt import InterruptToken


def _loader(shells: list[str], log: object | None = None, tts_enabled: bool = False) -> ShellLoader:
    config = types.SimpleNamespace(
        shells=shells, groq_api_key="k", follow_up_timeout_seconds=30, tts_enabled=tts_enabled,
    )
    token = InterruptToken()
    kernel = types.SimpleNamespace(submit=lambda text: None, interrupt_token=token, request_interrupt=token.interrupt)
    return ShellLoader(config, kernel, log or types.SimpleNamespace(log=lambda *a: None), reporter=object())


def test_orders_tray_last_regardless_of_env_position() -> None:
    assert _loader(["tray", "cli", "voice"])._ordered_names() == ["cli", "voice", "tray"]


def test_no_tray_keeps_original_order() -> None:
    assert _loader(["voice", "cli"])._ordered_names() == ["voice", "cli"]


def test_start_logs_ready_and_runs_last_shell_on_main_thread() -> None:
    started: list[object] = []
    logs: list[tuple] = []
    loader = _loader(["cli"], types.SimpleNamespace(log=lambda *a: logs.append(a)))
    loader._load_class = lambda name: lambda: types.SimpleNamespace(start=started.append)
    loader.start()
    assert ("READY", "TUSK is ready.", "startup") in logs and started == [loader._kernel.submit]


def test_tray_receives_voice_shell_as_pipeline_control(monkeypatch) -> None:
    monkeypatch.setattr(shell_loader, "GroqSTT", lambda key: object())
    loader = _loader(["voice", "tray"])
    loader._gatekeeper = lambda worker: None
    loader._load_class = lambda name: _voice_class() if name == "voice" else _tray_class()
    shells = [loader._build(name) for name in loader._ordered_names()]
    assert shells[1].control is shells[0]


def test_voice_shell_receives_tts_engine_when_enabled(monkeypatch) -> None:
    monkeypatch.setattr(shell_loader, "GroqSTT", lambda key: object())
    sentinel = object()
    monkeypatch.setattr(shell_loader, "GroqTTS", lambda key: sentinel)
    loader = _loader(["voice"], tts_enabled=True)
    loader._gatekeeper = lambda worker: None
    loader._load_class = lambda name: _voice_class()
    assert loader._build("voice").tts_engine is sentinel


def _voice_class() -> object:
    def make(
        config, log, stt_engine=None, gatekeeper=None, tts_engine=None, reporter=None,
        command_worker=None, request_interrupt=None, interrupt_token=None,
    ):
        return types.SimpleNamespace(kind="voice", tts_engine=tts_engine)
    return make


def _tray_class() -> object:
    return lambda reporter, control, event, config: types.SimpleNamespace(kind="tray", control=control)
