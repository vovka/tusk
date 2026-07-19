import subprocess
import types

import adapters.gnome.tools.window_tools as window_tools_module
from adapters.gnome.tools.window_tools import WindowTools

_WINDOW_LIST = "0x01 0 host *Unsaved Document 1 - gedit\n0x02 1 host Tilix: vovka\n"


def _run_recorder(calls: list[list[str]], returncode: int = 0, stdout: str = _WINDOW_LIST) -> object:
    def run(argv: list[str], **kwargs: object) -> object:
        calls.append(list(argv))
        return types.SimpleNamespace(returncode=returncode, stdout=stdout)
    return run


def _patch_run(monkeypatch: object, calls: list[list[str]], returncode: int = 0, stdout: str = _WINDOW_LIST) -> None:
    monkeypatch.setattr(window_tools_module.subprocess, "run", _run_recorder(calls, returncode, stdout))


def test_move_resize_converts_x11_geometry_to_wmctrl_form(monkeypatch: object) -> None:
    calls: list[list[str]] = []
    _patch_run(monkeypatch, calls)
    result = WindowTools().move_resize_window({"window_title": "gedit", "geometry": "1440x1800+1440+0"})
    assert result["success"] is True
    assert calls[-1][-1] == "0,1440,0,1440,1800"


def test_move_resize_converts_negative_x11_offset_to_wmctrl_form(monkeypatch: object) -> None:
    calls: list[list[str]] = []
    _patch_run(monkeypatch, calls)
    result = WindowTools().move_resize_window({"window_title": "gedit", "geometry": "1440x1800-1440+0"})
    assert result["success"] is True
    assert calls[-1][-1] == "0,-1440,0,1440,1800"


def test_move_resize_strips_leading_plus_from_x11_offset(monkeypatch: object) -> None:
    calls: list[list[str]] = []
    _patch_run(monkeypatch, calls)
    result = WindowTools().move_resize_window({"window_title": "gedit", "geometry": "1440x1800+1440+0"})
    assert result["success"] is True
    assert calls[-1][-1] == "0,1440,0,1440,1800"


def test_move_resize_fails_when_geometry_missing(monkeypatch: object) -> None:
    calls: list[list[str]] = []
    _patch_run(monkeypatch, calls)
    result = WindowTools().move_resize_window({"window_title": "gedit"})
    assert result["success"] is False
    assert result["message"] == "missing argument: geometry"


def test_move_resize_passes_comma_geometry_through(monkeypatch: object) -> None:
    calls: list[list[str]] = []
    _patch_run(monkeypatch, calls)
    result = WindowTools().move_resize_window({"window_title": "gedit", "geometry": "0,0,1440,1800"})
    assert result["success"] is True
    assert calls[-1][-1] == "0,0,0,1440,1800"


def test_move_resize_rejects_unparseable_geometry(monkeypatch: object) -> None:
    calls: list[list[str]] = []
    _patch_run(monkeypatch, calls)
    result = WindowTools().move_resize_window({"window_title": "gedit", "geometry": "left half"})
    assert result["success"] is False
    assert "X,Y,WIDTH,HEIGHT" in result["message"]


def test_move_resize_reports_wmctrl_failure(monkeypatch: object) -> None:
    calls: list[list[str]] = []
    _patch_run(monkeypatch, calls, returncode=1)
    result = WindowTools().move_resize_window({"window_title": "gedit", "geometry": "0,0,10,10"})
    assert result["success"] is False


def test_move_resize_fails_for_missing_window(monkeypatch: object) -> None:
    calls: list[list[str]] = []
    _patch_run(monkeypatch, calls, stdout="0x01 0 host Tilix: vovka\n")
    result = WindowTools().move_resize_window({"window_title": "GLED", "geometry": "0,0,10,10"})
    assert result["success"] is False
    assert "not found" in result["message"]


def test_focus_fails_for_missing_window(monkeypatch: object) -> None:
    calls: list[list[str]] = []
    _patch_run(monkeypatch, calls, stdout="0x01 0 host Tilix: vovka\n")
    result = WindowTools().focus_window({"window_title": "GLED"})
    assert result["success"] is False
    assert "not found" in result["message"]


def test_maximize_succeeds_for_listed_window(monkeypatch: object) -> None:
    calls: list[list[str]] = []
    _patch_run(monkeypatch, calls)
    result = WindowTools().maximize_window({"window_title": "Unsaved Document 1 - gedit"})
    assert result["success"] is True


def test_minimize_searches_only_visible_windows_with_escaped_title(monkeypatch: object) -> None:
    calls: list[list[str]] = []
    _patch_run(monkeypatch, calls, stdout="12345\n")
    result = WindowTools().minimize_window({"window_title": "*Unsaved Document 1 - gedit"})
    assert result["success"] is True
    search = next(argv for argv in calls if argv[:2] == ["xdotool", "search"])
    assert "--onlyvisible" in search
    assert search[-1] == "\\*Unsaved\\ Document\\ 1\\ \\-\\ gedit"
