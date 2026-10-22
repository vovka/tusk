import types

import adapters.gnome.x11.window_tools as window_tools_module
from adapters.gnome.x11.window_tools import WindowTools
from adapters.gnome.wayland.wayland_window_tools import WaylandWindowTools
from tests.adapters.wayland_fake_bus import FakeBus

_SIMILAR = "0x01 0 host gedit\n0x02 0 host gedit - notes\n"
_AMBIGUOUS = "0x01 0 host a.txt - gedit\n0x02 0 host b.txt - gedit\n"


def _patch_run(monkeypatch: object, calls: list[list[str]], stdout: str, returncode: int = 0) -> None:
    def run(argv: list[str], **kwargs: object) -> object:
        calls.append(list(argv))
        return types.SimpleNamespace(returncode=returncode, stdout=stdout)
    monkeypatch.setattr(window_tools_module.subprocess, "run", run)


def test_x11_close_prefers_exact_title_and_acts_by_id(monkeypatch: object) -> None:
    calls: list[list[str]] = []
    _patch_run(monkeypatch, calls, _SIMILAR)
    assert WindowTools().close_window({"window_title": "GEDIT"})["success"] is True
    assert calls[-1] == ["wmctrl", "-i", "-c", "0x01"]


def test_x11_ambiguous_title_fails_without_acting(monkeypatch: object) -> None:
    calls: list[list[str]] = []
    _patch_run(monkeypatch, calls, _AMBIGUOUS)
    result = WindowTools().maximize_window({"window_title": "gedit"})
    assert result == {"success": False, "message": "ambiguous window title 'gedit': a.txt - gedit; b.txt - gedit"}
    assert calls == [["wmctrl", "-l"]]


def test_x11_maximize_acts_by_id(monkeypatch: object) -> None:
    calls: list[list[str]] = []
    _patch_run(monkeypatch, calls, _SIMILAR)
    WindowTools().maximize_window({"window_title": "notes"})
    assert calls[-1] == ["wmctrl", "-i", "-r", "0x02", "-b", "add,maximized_vert,maximized_horz"]


def test_x11_minimize_passes_decimal_id_to_xdotool(monkeypatch: object) -> None:
    calls: list[list[str]] = []
    _patch_run(monkeypatch, calls, _SIMILAR)
    WindowTools().minimize_window({"window_title": "notes"})
    assert calls[-1] == ["xdotool", "windowminimize", "2"]


def test_x11_tile_reports_unreadable_display_size(monkeypatch: object) -> None:
    calls: list[list[str]] = []
    _patch_run(monkeypatch, calls, "", returncode=1)
    result = WindowTools().tile_window({"window_title": "gedit", "side": "left"})
    assert result == {"success": False, "message": "cannot read display size from xdotool getdisplaygeometry"}


def test_wayland_ambiguous_title_fails_without_acting() -> None:
    windows = [{"id": 1, "title": "a.txt - gedit"}, {"id": 2, "title": "b.txt - gedit"}]
    bus = FakeBus(windows)
    result = WaylandWindowTools(bus).tile_window({"window_title": "gedit", "side": "left"})
    assert result["success"] is False and "ambiguous" in result["message"]
    assert bus.calls == []


def test_wayland_exact_title_wins_over_substring() -> None:
    bus = FakeBus([{"id": 1, "title": "gedit - notes"}, {"id": 2, "title": "Gedit"}])
    WaylandWindowTools(bus).close_window({"window_title": "gedit"})
    assert bus.calls == [("Close", [2])]
