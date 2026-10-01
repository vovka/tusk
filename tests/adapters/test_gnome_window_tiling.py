import types

import adapters.gnome.tools.window_tools as window_tools_module
from adapters.gnome.tools.window_tools import WindowTools

_WINDOW_LIST = "0x01 0 host *Unsaved Document 1 - gedit\n"


def _patch_run(monkeypatch: object, calls: list[list[str]], stdout: str = _WINDOW_LIST) -> None:
    def run(argv: list[str], **kwargs: object) -> object:
        calls.append(list(argv))
        return types.SimpleNamespace(returncode=0, stdout=stdout)
    monkeypatch.setattr(window_tools_module.subprocess, "run", run)



def test_tile_window_left_unmaximizes_then_uses_left_half(monkeypatch: object) -> None:
    calls: list[list[str]] = []
    _patch_run(monkeypatch, calls, )
    monkeypatch.setattr(window_tools_module.WindowTools, "_display_size", lambda self: (2880, 1800))
    result = WindowTools().tile_window({"window_title": "gedit", "side": "left"})
    assert result == {"success": True, "message": "tiled left: gedit"}
    assert calls[-2] == ["wmctrl", "-i", "-r", "0x01", "-b", "remove,maximized_vert,maximized_horz"]
    assert calls[-1] == ["wmctrl", "-i", "-r", "0x01", "-e", "0,0,0,1440,1800"]


def test_tile_window_right_uses_right_half(monkeypatch: object) -> None:
    calls: list[list[str]] = []
    _patch_run(monkeypatch, calls)
    monkeypatch.setattr(window_tools_module.WindowTools, "_display_size", lambda self: (2880, 1800))
    WindowTools().tile_window({"window_title": "gedit", "side": "right"})
    assert calls[-1][-1] == "0,1440,0,1440,1800"


def test_tile_window_rejects_bad_side(monkeypatch: object) -> None:
    calls: list[list[str]] = []
    _patch_run(monkeypatch, calls)
    result = WindowTools().tile_window({"window_title": "gedit", "side": "up"})
    assert result == {"success": False, "message": "bad side 'up': use left or right"}


def test_display_size_reads_xdotool_geometry(monkeypatch: object) -> None:
    calls: list[list[str]] = []
    _patch_run(monkeypatch, calls, stdout="2880 1800\n")
    assert WindowTools()._display_size() == (2880, 1800)
    assert calls == [["xdotool", "getdisplaygeometry"]]
