from adapters.gnome.app_catalog import AppCatalog
from adapters.gnome.gnome_clipboard_provider import GnomeClipboardProvider
from adapters.gnome.tools.application_tools import ApplicationTools
from adapters.gnome.tools.clipboard_tools import ClipboardTools
from adapters.gnome.tools.context_tools import ContextTools
from adapters.gnome.tools.input_tools import InputTools
from adapters.gnome.tools.launched_window_guard import LaunchedWindowGuard
from adapters.gnome.tools.tool_schema_catalog import ToolSchemaCatalog
from adapters.gnome.wayland.wayland_context_provider import WaylandContextProvider
from adapters.gnome.wayland.wayland_window_tools import WaylandWindowTools
from adapters.gnome.x11.context_provider import X11ContextProvider
from adapters.gnome.x11.input_simulator import X11InputSimulator
from adapters.gnome.x11.window_tools import WindowTools
from adapters.gnome.x11.windows import X11Windows

__all__ = ["GnomeToolRouter"]

ContextProvider = X11ContextProvider | WaylandContextProvider
WindowLister = X11Windows | WaylandWindowTools


class GnomeToolRouter:
    def __init__(
        self,
        apps: AppCatalog,
        clipboard: GnomeClipboardProvider,
        context: ContextProvider,
        input_simulator: X11InputSimulator,
        window_tools: WindowTools,
        windows: WindowLister,
    ) -> None:
        self._window_tools = window_tools
        self._windows = windows
        self._schemas = ToolSchemaCatalog().build()
        self._handlers = self._build_handlers(apps, clipboard, context, input_simulator)

    def schemas(self) -> dict[str, dict]:
        return self._schemas

    def call(self, name: str, arguments: dict) -> dict:
        data = self._handlers[name](arguments)
        return {"content": [{"type": "text", "text": data["message"]}], "isError": not data["success"], "data": data.get("data")}

    def _build_handlers(
        self,
        apps: AppCatalog,
        clipboard: GnomeClipboardProvider,
        context: ContextProvider,
        input_simulator: X11InputSimulator,
    ) -> dict[str, object]:
        launched = LaunchedWindowGuard(self._windows)
        return self._merged_handlers(
            ApplicationTools(apps, window_lister=self._windows.list_windows, launched=launched),
            ClipboardTools(clipboard),
            ContextTools(context),
            InputTools(input_simulator, launched),
            self._window_tools,
        )

    def _merged_handlers(
        self,
        application: ApplicationTools,
        clipboard_tools: ClipboardTools,
        context_tools: ContextTools,
        input_tools: InputTools,
        window_tools: WindowTools,
    ) -> dict[str, object]:
        return {
            **self._application_handlers(application),
            **self._clipboard_handlers(clipboard_tools),
            **self._context_handlers(context_tools),
            **self._input_handlers(input_tools),
            **self._window_handlers(window_tools),
        }

    def _application_handlers(self, application: ApplicationTools) -> dict[str, object]:
        return {"launch_application": application.launch_application, "open_uri": application.open_uri, "search_applications": application.search_applications}

    def _clipboard_handlers(self, clipboard_tools: ClipboardTools) -> dict[str, object]:
        return {"read_clipboard": clipboard_tools.read_clipboard, "write_clipboard": clipboard_tools.write_clipboard}

    def _context_handlers(self, context_tools: ContextTools) -> dict[str, object]:
        return {"get_desktop_context": context_tools.get_desktop_context, "get_active_window": context_tools.get_active_window, "list_windows": context_tools.list_windows}

    def _input_handlers(self, input_tools: InputTools) -> dict[str, object]:
        return {"press_keys": input_tools.press_keys, "type_text": input_tools.type_text, "replace_recent_text": input_tools.replace_recent_text, "mouse_click": input_tools.mouse_click, "mouse_move": input_tools.mouse_move, "mouse_drag": input_tools.mouse_drag, "mouse_scroll": input_tools.mouse_scroll}

    def _window_handlers(self, window_tools: WindowTools) -> dict[str, object]:
        return {
            "close_window": window_tools.close_window,
            "focus_window": window_tools.focus_window,
            "maximize_window": window_tools.maximize_window,
            "minimize_window": window_tools.minimize_window,
            "move_resize_window": window_tools.move_resize_window,
            "tile_window": window_tools.tile_window,
            "switch_workspace": window_tools.switch_workspace,
        }
