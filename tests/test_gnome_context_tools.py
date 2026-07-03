from adapters.gnome.desktop_context import DesktopContext
from adapters.gnome.gnome_context_tools import GnomeContextTools
from adapters.gnome.window_info import WindowInfo


class StubContextProvider:
    def __init__(self, context: DesktopContext) -> None:
        self._context = context

    def get_context(self) -> DesktopContext:
        return self._context


def _context() -> DesktopContext:
    windows = [
        WindowInfo("0x1", "Системний монітор", "gnome-system-monitor", False, 0, 0, 800, 600),
        WindowInfo("0x2", "notes.txt - gedit", "gedit", True, 10, 10, 640, 480),
    ]
    return DesktopContext("notes.txt - gedit", "gedit", windows, [])


def test_get_desktop_context_message_contains_active_window_and_window_list() -> None:
    """MCP clients see only `message`; the real desktop state must be in it.
    Regression: codex received the literal string 'context' and typed blind."""
    result = GnomeContextTools(StubContextProvider(_context())).get_desktop_context({})

    assert result["success"] is True
    assert "active window: notes.txt - gedit -> gedit" in result["message"]
    assert "Системний монітор" in result["message"]


def test_get_desktop_context_keeps_data_for_kernel_clients() -> None:
    result = GnomeContextTools(StubContextProvider(_context())).get_desktop_context({})

    assert result["data"]["active_window_title"] == "notes.txt - gedit"
    assert result["data"]["open_windows"][0]["title"] == "Системний монітор"
