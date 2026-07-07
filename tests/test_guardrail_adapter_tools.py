import types

from adapters.gnome.gnome_application_tools import GnomeApplicationTools
from adapters.gnome.server import GnomeServer


def test_search_applications_ranks_exact_name_first() -> None:
    server = GnomeServer()
    handler = _search_handler(server)
    result = handler({"query": "firefox"})
    assert "Firefox -> firefox" in result["message"].splitlines()[1]


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
