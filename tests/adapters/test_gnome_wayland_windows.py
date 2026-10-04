import types

from adapters.gnome.wayland.wayland_context_provider import WaylandContextProvider
from adapters.gnome.wayland.wayland_window_tools import WaylandWindowTools
from tests.adapters.wayland_fake_bus import FakeBus


def test_context_lists_windows_and_active_title() -> None:
    context = WaylandContextProvider(types.SimpleNamespace(list_apps=lambda: []), FakeBus()).get_context()
    assert context.active_window_title == "Notes - gedit"
    assert context.active_application == "gedit"
    assert context.open_windows[1].window_id == "9"
    assert context.open_windows[0].height == 4


def test_window_tools_close_resolves_title_substring_to_id() -> None:
    bus = FakeBus()
    result = WaylandWindowTools(bus).close_window({"window_title": "gedit"})
    assert result == {"success": True, "message": "closed: gedit"}
    assert bus.calls == [("Close", [7])]


def test_window_tools_reports_missing_window() -> None:
    bus = FakeBus()
    result = WaylandWindowTools(bus).focus_window({"window_title": "firefox"})
    assert result == {"success": False, "message": "window not found: firefox"}
    assert bus.calls == []


def test_window_tools_move_resize_accepts_x11_geometry() -> None:
    bus = FakeBus()
    WaylandWindowTools(bus).move_resize_window({"window_title": "term", "geometry": "800x600+10+20"})
    assert bus.calls == [("MoveResize", [9, 10, 20, 800, 600])]


def test_window_tools_switch_workspace() -> None:
    bus = FakeBus()
    WaylandWindowTools(bus).switch_workspace({"workspace_number": "2"})
    assert bus.calls == [("SwitchWorkspace", [2])]


def test_window_tools_lists_ids_and_titles_for_launch_polling() -> None:
    assert WaylandWindowTools(FakeBus()).list_windows() == [("7", "Notes - gedit", "gedit"), ("9", "Terminal", "tilix")]


def test_window_tools_report_active_window_and_focus_by_id() -> None:
    bus = FakeBus()
    tools = WaylandWindowTools(bus)
    assert tools.active_window_id() == "7"
    tools.focus("9")
    assert bus.calls == [("Focus", [9])]


def _recorder(calls: list[list[str]], stdout: str, returncode: int = 0, stderr: str = "") -> object:
    def run(argv: list[str], **kwargs: object) -> object:
        calls.append(list(argv))
        return types.SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)
    return run


def test_build_router_selects_wayland_backend(monkeypatch: object) -> None:
    from adapters.gnome.server import build_router
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    router = build_router()
    assert isinstance(router._window_tools, WaylandWindowTools)


def test_build_router_keeps_x11_backend(monkeypatch: object) -> None:
    from adapters.gnome.server import build_router
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    assert not isinstance(build_router()._window_tools, WaylandWindowTools)


def test_window_tools_tile_right_calls_extension() -> None:
    bus = FakeBus()
    result = WaylandWindowTools(bus).tile_window({"window_title": "gedit", "side": "right"})
    assert result == {"success": True, "message": "tiled right: gedit"}
    assert bus.calls == [("TileRight", [7])]


def test_window_tools_tile_rejects_bad_side() -> None:
    bus = FakeBus()
    assert WaylandWindowTools(bus).tile_window({"window_title": "gedit", "side": ""})["success"] is False
    assert bus.calls == []


def test_get_active_window_reports_focused_wayland_window() -> None:
    from adapters.gnome.tools.context_tools import ContextTools
    provider = WaylandContextProvider(types.SimpleNamespace(list_apps=lambda: []), FakeBus())
    message = ContextTools(provider).get_active_window({})["message"]
    assert message == "active window: Notes - gedit -> gedit [3x4 at 1,2]"
