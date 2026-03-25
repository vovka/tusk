try:
    from gnome_application_tools import GnomeApplicationTools
    from gnome_clipboard_tools import GnomeClipboardTools
    from gnome_context_tools import GnomeContextTools
    from gnome_input_tools import GnomeInputTools
    from gnome_tool_schema_catalog import GnomeToolSchemaCatalog
    from gnome_window_tools import GnomeWindowTools
except ImportError:  # pragma: no cover
    from adapters.gnome.gnome_application_tools import GnomeApplicationTools
    from adapters.gnome.gnome_clipboard_tools import GnomeClipboardTools
    from adapters.gnome.gnome_context_tools import GnomeContextTools
    from adapters.gnome.gnome_input_tools import GnomeInputTools
    from adapters.gnome.gnome_tool_schema_catalog import GnomeToolSchemaCatalog
    from adapters.gnome.gnome_window_tools import GnomeWindowTools

__all__ = ["GnomeToolRouter"]


class GnomeToolRouter:
    def __init__(self, apps: object, clipboard: object, context: object, input_simulator: object, text_paster: object) -> None:
        self._schemas = GnomeToolSchemaCatalog().build()
        self._handlers = self._build_handlers(apps, clipboard, context, input_simulator, text_paster)

    def schemas(self) -> dict[str, dict]:
        return self._schemas

    def call(self, name: str, arguments: dict) -> dict:
        data = self._handlers[name](arguments)
        return {"content": [{"type": "text", "text": data["message"]}], "isError": not data["success"], "data": data.get("data")}

    def _build_handlers(self, apps: object, clipboard: object, context: object, input_simulator: object, text_paster: object) -> dict[str, object]:
        application, clipboard_tools, context_tools, input_tools, window_tools = self._tool_groups(
            apps,
            clipboard,
            context,
            input_simulator,
            text_paster,
        )
        return self._merged_handlers(application, clipboard_tools, context_tools, input_tools, window_tools)

    def _tool_groups(self, apps: object, clipboard: object, context: object, input_simulator: object, text_paster: object) -> tuple[object, ...]:
        return (
            GnomeApplicationTools(apps),
            GnomeClipboardTools(clipboard),
            GnomeContextTools(context),
            GnomeInputTools(input_simulator, text_paster),
            GnomeWindowTools(),
        )

    def _merged_handlers(
        self,
        application: GnomeApplicationTools,
        clipboard_tools: GnomeClipboardTools,
        context_tools: GnomeContextTools,
        input_tools: GnomeInputTools,
        window_tools: GnomeWindowTools,
    ) -> dict[str, object]:
        return {
            **self._application_handlers(application),
            **self._clipboard_handlers(clipboard_tools),
            **self._context_handlers(context_tools),
            **self._input_handlers(input_tools),
            **self._window_handlers(window_tools),
        }

    def _application_handlers(self, application: GnomeApplicationTools) -> dict[str, object]:
        return {"launch_application": application.launch_application, "open_uri": application.open_uri, "search_applications": application.search_applications}

    def _clipboard_handlers(self, clipboard_tools: GnomeClipboardTools) -> dict[str, object]:
        return {"read_clipboard": clipboard_tools.read_clipboard, "write_clipboard": clipboard_tools.write_clipboard}

    def _context_handlers(self, context_tools: GnomeContextTools) -> dict[str, object]:
        return {"get_desktop_context": context_tools.get_desktop_context, "get_active_window": context_tools.get_active_window, "list_windows": context_tools.list_windows}

    def _input_handlers(self, input_tools: GnomeInputTools) -> dict[str, object]:
        return {"press_keys": input_tools.press_keys, "type_text": input_tools.type_text, "replace_recent_text": input_tools.replace_recent_text, "mouse_click": input_tools.mouse_click, "mouse_move": input_tools.mouse_move, "mouse_drag": input_tools.mouse_drag, "mouse_scroll": input_tools.mouse_scroll}

    def _window_handlers(self, window_tools: GnomeWindowTools) -> dict[str, object]:
        return {
            "close_window": window_tools.close_window,
            "focus_window": window_tools.focus_window,
            "maximize_window": window_tools.maximize_window,
            "minimize_window": window_tools.minimize_window,
            "move_resize_window": window_tools.move_resize_window,
            "switch_workspace": window_tools.switch_workspace,
        }
