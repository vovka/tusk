import types

from adapters.gnome.gnome_application_tools import GnomeApplicationTools
from adapters.gnome.server import GnomeServer
from tusk.shared.schemas.desktop_context import DesktopContext, WindowInfo


def test_search_applications_ranks_exact_name_first() -> None:
    server = GnomeServer()
    server._router._handlers["search_applications"] = _search_handler(server)
    result = server._tool_search_applications({"query": "firefox"})
    assert "Firefox -> firefox" in result["message"].splitlines()[1]


def test_list_windows_and_active_window_tools() -> None:
    server = GnomeServer()
    server._router._handlers.update(_context_handlers())
    listed = server._tool_list_windows({})
    active = server._tool_get_active_window({})
    assert "Editor -> gedit [800x600 at 10,20]" in listed["message"]
    assert "active window: Editor -> gedit [800x600 at 10,20]" == active["message"]


def test_launch_application_resolves_display_name_to_exec() -> None:
    calls: list[str] = []
    tools = _application_tools(calls)
    result = tools.launch_application({"application_name": "Firefox"})
    assert calls == ["firefox"]
    assert result == {"success": True, "message": "launched: Firefox"}


def _search_result() -> dict:
    return {"success": True, "message": "application matches for 'firefox':\nFirefox -> firefox"}


def _search_handler(server: GnomeServer) -> object:
    tools = types.SimpleNamespace(
        launch_application=lambda args: {},
        open_uri=lambda args: {},
        search_applications=lambda arguments: _search_result(),
    )
    return server._router._application_handlers(tools)["search_applications"]


def _application_tools(calls: list[str]) -> GnomeApplicationTools:
    apps = types.SimpleNamespace(search=lambda query, limit=10: [types.SimpleNamespace(name="Firefox", exec_cmd="firefox")])
    tools = GnomeApplicationTools(apps)
    tools._launch = lambda application_name: _launch_response(calls, application_name)  # type: ignore[method-assign]
    return tools


def _launch_response(calls: list[str], application_name: str) -> str:
    calls.append(application_name)
    return "ok\n"


def _context_handlers() -> dict[str, object]:
    context = DesktopContext("Editor", "gedit", open_windows=[WindowInfo("1", "Editor", "gedit", True, 10, 20, 800, 600)])
    return {
        "list_windows": lambda arguments: {"success": True, "message": "open windows:\n  Editor -> gedit [800x600 at 10,20]"},
        "get_active_window": lambda arguments: {"success": True, "message": "active window: Editor -> gedit [800x600 at 10,20]"},
        "get_desktop_context": lambda arguments: {"success": True, "message": "context", "data": context},
    }
