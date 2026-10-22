import types

import pytest

from composition.shell_loader import _SHELL_CLASSES, ShellLoader
from shells.voice.voice_shell import VoiceShell
from tusk.shared.interfaces.shell import Shell


def _loader(shells: list[str], log: object | None = None) -> ShellLoader:
    config = types.SimpleNamespace(shells=shells)
    kernel = types.SimpleNamespace(submit=lambda text: None)
    return ShellLoader(config, kernel, log or types.SimpleNamespace(log=lambda *a: None), reporter=object())


def test_ordering_puts_tray_last_without_disturbing_the_rest() -> None:
    assert _loader(["tray", "cli", "voice"])._ordered_names() == ["cli", "voice", "tray"]
    assert _loader(["voice", "cli"])._ordered_names() == ["voice", "cli"]


def test_start_logs_ready_and_runs_last_shell_on_main_thread() -> None:
    started: list[object] = []
    logs: list[tuple] = []
    loader = _loader(["cli"], types.SimpleNamespace(log=lambda *a: logs.append(a)))
    loader._load_class = lambda name: lambda: types.SimpleNamespace(start=started.append)
    loader.start()
    assert ("READY", "TUSK is ready.", "startup") in logs and started == [loader._kernel.submit]


def test_voice_shell_comes_from_builder_and_becomes_tray_control(monkeypatch) -> None:
    shell = types.SimpleNamespace(kind="voice")
    monkeypatch.setattr("composition.shell_loader.VoiceShellBuilder", lambda *args: types.SimpleNamespace(build=lambda: shell))
    loader = _loader(["voice", "tray"])
    loader._load_class = lambda name: _tray_class()
    shells = [loader._build(name) for name in loader._ordered_names()]
    assert shells[0] is shell and shells[1].control is shell


def test_builder_receives_loader_collaborators_and_speech_end_callback(monkeypatch) -> None:
    seen: list[tuple] = []
    monkeypatch.setattr("composition.shell_loader.VoiceShellBuilder", lambda *args: seen.append(args) or types.SimpleNamespace(build=lambda: None))
    config, kernel, log, reporter, on_speech_end = object(), object(), object(), object(), lambda seconds_ago: None
    ShellLoader(config, kernel, log, reporter, on_speech_end)._build("voice")
    assert seen == [(config, kernel, log, reporter, on_speech_end)]


def test_registry_resolves_every_class_backed_shell() -> None:
    names = {name: _loader(["cli"])._load_class(name).__name__ for name in ("cli", "emulator", "tray")}
    assert names == {"cli": "CLIShell", "emulator": "EmulatorShell", "tray": "TrayShell"}


def test_every_shell_implements_the_shell_abc() -> None:
    assert all(issubclass(cls, Shell) for cls in (*_SHELL_CLASSES.values(), VoiceShell))


def test_unknown_shell_name_is_rejected() -> None:
    with pytest.raises(ValueError):
        _loader(["cli"])._load_class("bogus")


def _tray_class() -> object:
    return lambda reporter, control, event, config: types.SimpleNamespace(kind="tray", control=control)
