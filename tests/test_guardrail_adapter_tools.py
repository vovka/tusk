import types

from adapters.gnome.server import GnomeServer
from tusk.kernel.schemas.desktop_context import DesktopContext, WindowInfo


def test_search_applications_ranks_exact_name_first() -> None:
    server = GnomeServer()
    server._apps = types.SimpleNamespace(
        list_dicts=lambda: [],
        list_apps=lambda: [
            types.SimpleNamespace(name="Firefox", exec_cmd="firefox"),
            types.SimpleNamespace(name="Firefox Developer Edition", exec_cmd="firefox-developer-edition"),
        ],
    )
    result = server._tool_search_applications({"query": "firefox"})
    assert "Firefox -> firefox" in result["message"].splitlines()[1]


def test_list_windows_and_active_window_tools() -> None:
    server = GnomeServer()
    context = DesktopContext(
        "Editor",
        "gedit",
        open_windows=[WindowInfo("1", "Editor", "gedit", True, 10, 20, 800, 600)],
    )
    server._context = types.SimpleNamespace(get_context=lambda: context, get_context_dict=lambda: {})
    listed = server._tool_list_windows({})
    active = server._tool_get_active_window({})
    assert "Editor -> gedit [800x600 at 10,20]" in listed["message"]
    assert "active window: Editor -> gedit [800x600 at 10,20]" == active["message"]
