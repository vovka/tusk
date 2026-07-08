import types

import pytest

import shell_loader
from shell_loader import ShellLoader
from tusk.shared.interrupt import InterruptToken


def _loader(shells: list[str], log: object | None = None, tts_enabled: bool = False, stt_engine: str = "groq") -> ShellLoader:
    config = types.SimpleNamespace(
        shells=shells, groq_api_key="k", follow_up_timeout_seconds=30, tts_enabled=tts_enabled,
        ack_enabled=True, stt_engine=stt_engine, whisper_model_size="base",
    )
    kernel = types.SimpleNamespace(
        submit=lambda text: None,
        interrupt_token=InterruptToken(),
        request_interrupt=lambda: None,
    )
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
    _patch_stt(monkeypatch, object())
    loader = _loader(["voice", "tray"])
    loader._gatekeeper = lambda worker: None
    loader._load_class = lambda name: _voice_class() if name == "voice" else _tray_class()
    shells = [loader._build(name) for name in loader._ordered_names()]
    assert shells[1].control is shells[0]


def test_command_worker_receives_tts_engine_when_enabled(monkeypatch) -> None:
    _patch_stt(monkeypatch, object())
    sentinel = object()
    monkeypatch.setattr(shell_loader, "GroqTTS", lambda key: sentinel)
    loader = _loader(["voice"], tts_enabled=True)
    loader._gatekeeper = lambda worker: None
    loader._load_class = lambda name: _voice_class()
    assert loader._build("voice").worker._tts is sentinel


def test_registry_resolves_every_shell_without_manifests() -> None:
    loader = _loader(["cli"])
    names = {name: loader._load_class(name).__name__ for name in ("cli", "emulator", "tray", "voice")}
    assert names == {"cli": "CLIShell", "emulator": "EmulatorShell", "tray": "TrayShell", "voice": "VoiceShell"}


def test_unknown_shell_name_is_rejected() -> None:
    with pytest.raises(ValueError):
        _loader(["cli"])._load_class("bogus")


def test_voice_shell_receives_configured_stt_engine(monkeypatch) -> None:
    sentinel = object()
    _patch_stt(monkeypatch, sentinel)
    loader = _loader(["voice"], stt_engine="whisper")
    loader._gatekeeper = lambda worker: None
    loader._load_class = lambda name: _voice_class()
    assert loader._build("voice").stt is sentinel


def test_interrupt_callback_requests_kernel_interrupt_and_flushes_worker(monkeypatch) -> None:
    requested: list[bool] = []
    shell = _built_voice_shell(monkeypatch, requested)
    shell.worker.enqueue("queued command")
    shell.on_interrupt()
    assert requested == [True]
    assert not shell.worker.is_busy


def _built_voice_shell(monkeypatch, requested: list[bool]) -> object:
    _patch_stt(monkeypatch, object())
    loader = _loader(["voice"])
    loader._kernel.request_interrupt = lambda: requested.append(True)
    loader._gatekeeper = lambda worker: None
    loader._load_class = lambda name: _voice_class()
    return loader._build("voice")


def _patch_stt(monkeypatch, engine: object) -> None:
    factory = lambda key, size: types.SimpleNamespace(create=lambda name: engine)
    monkeypatch.setattr(shell_loader, "STTEngineFactory", factory)


def _voice_class() -> object:
    def make(config, log, stt_engine=None, gatekeeper=None, worker=None, reporter=None, on_interrupt=None):
        return types.SimpleNamespace(kind="voice", worker=worker, on_interrupt=on_interrupt, stt=stt_engine)
    return make


def _tray_class() -> object:
    return lambda reporter, control, event, config: types.SimpleNamespace(kind="tray", control=control)
