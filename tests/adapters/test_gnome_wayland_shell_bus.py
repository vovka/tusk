import types

import adapters.gnome.wayland.shell_bus as shell_bus_module
from adapters.gnome.wayland.shell_bus import ShellBus


def test_shell_bus_formats_gvariant_arguments(monkeypatch: object) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(shell_bus_module.subprocess, "run", _recorder(calls, "()\n"))
    ShellBus().call("KeyCombo", [["Control_L", "c"], 5, True, 'a"b'])
    assert calls[0][:3] == ["gdbus", "call", "--session"]
    assert calls[0][-5:] == ["org.tusk.Shell.KeyCombo", '["Control_L", "c"]', "5", "true", '"a\\"b"']


def test_shell_bus_parses_string_reply(monkeypatch: object) -> None:
    monkeypatch.setattr(shell_bus_module.subprocess, "run", _recorder([], "('[{\"id\": 1}]',)\n"))
    assert ShellBus().call_string("ListWindows") == '[{"id": 1}]'


def test_shell_bus_raises_on_failure(monkeypatch: object) -> None:
    monkeypatch.setattr(shell_bus_module.subprocess, "run", _recorder([], "", 1, "no such window"))
    try:
        ShellBus().call("Close", [3])
    except RuntimeError as exc:
        assert "no such window" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")


def _recorder(calls: list[list[str]], stdout: str, returncode: int = 0, stderr: str = "") -> object:
    def run(argv: list[str], **kwargs: object) -> object:
        calls.append(list(argv))
        return types.SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)
    return run
