import types
from unittest.mock import patch

from adapters.gnome.gnome_clipboard_provider import GnomeClipboardProvider


def test_uses_xclip_on_x11(monkeypatch) -> None:
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")
    assert _read_argv() == ["xclip", "-selection", "clipboard", "-o"]
    assert _write_argv() == ["xclip", "-selection", "clipboard"]


def test_uses_wl_clipboard_on_wayland_session_type(monkeypatch) -> None:
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    assert _read_argv()[0] == "wl-paste"
    assert _write_argv() == ["wl-copy"]


def test_uses_wl_clipboard_when_wayland_display_set(monkeypatch) -> None:
    monkeypatch.delenv("XDG_SESSION_TYPE", raising=False)
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    assert _write_argv() == ["wl-copy"]


def test_read_returns_empty_when_clipboard_tool_missing(monkeypatch) -> None:
    with patch("adapters.gnome.gnome_clipboard_provider.subprocess.run", side_effect=FileNotFoundError):
        assert GnomeClipboardProvider().read() == ""


def test_write_survives_missing_clipboard_tool(monkeypatch) -> None:
    with patch("adapters.gnome.gnome_clipboard_provider.subprocess.run", side_effect=FileNotFoundError):
        GnomeClipboardProvider().write("hi")


def _read_argv() -> list[str]:
    captured: list[str] = []
    with patch("adapters.gnome.gnome_clipboard_provider.subprocess.run", side_effect=_capture(captured)):
        GnomeClipboardProvider().read()
    return captured


def _write_argv() -> list[str]:
    captured: list[str] = []
    with patch("adapters.gnome.gnome_clipboard_provider.subprocess.run", side_effect=_capture(captured)):
        GnomeClipboardProvider().write("hi")
    return captured


def _capture(captured: list[str]) -> object:
    def run(args: list[str], **kwargs: object) -> object:
        captured[:] = args
        return types.SimpleNamespace(stdout="", returncode=0)

    return run
