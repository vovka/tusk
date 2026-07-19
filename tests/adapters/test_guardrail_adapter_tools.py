import subprocess
import types

from adapters.gnome.tools.application_tools import ApplicationTools
from adapters.gnome.gnome_tool_router import GnomeToolRouter
from adapters.gnome.server import build_router


def test_search_applications_ranks_exact_name_first() -> None:
    handler = _search_handler(build_router())
    result = handler({"query": "firefox"})
    assert "Firefox -> firefox" in result["message"].splitlines()[1]


def test_launch_application_resolves_display_name_to_exec(monkeypatch) -> None:
    monkeypatch.setattr(subprocess, "run", lambda command, **kwargs: subprocess.CompletedProcess(command, 0, "", ""))
    calls: list[str] = []
    tools = _application_tools(calls)
    result = tools.launch_application({"application_name": "Firefox"})
    assert calls == ["firefox"]
    assert result == {"success": True, "message": "launched: Firefox (no new window appeared within 10s)"}


def _search_result() -> dict:
    return {"success": True, "message": "application matches for 'firefox':\nFirefox -> firefox"}


def _search_handler(router: GnomeToolRouter) -> object:
    tools = types.SimpleNamespace(
        launch_application=lambda args: {},
        open_uri=lambda args: {},
        search_applications=lambda arguments: _search_result(),
    )
    return router._application_handlers(tools)["search_applications"]


def _application_tools(calls: list[str]) -> ApplicationTools:
    apps = types.SimpleNamespace(search=lambda query, limit=10: [types.SimpleNamespace(name="Firefox", exec_cmd="firefox")])
    tools = ApplicationTools(apps, sleep=lambda seconds: None)
    tools._launch = lambda application_name: _launch_response(calls, application_name)  # type: ignore[method-assign]
    return tools


def _launch_response(calls: list[str], application_name: str) -> str:
    calls.append(application_name)
    return "ok\n"
