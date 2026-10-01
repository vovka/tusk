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
    assert WaylandWindowTools(FakeBus()).list_windows() == [("7", "Notes - gedit"), ("9", "Terminal")]


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
