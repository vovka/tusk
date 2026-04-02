__all__ = ["GnomeContextTools"]


class GnomeContextTools:
    def __init__(self, context_provider: object) -> None:
        self._context = context_provider

    def get_desktop_context(self, arguments: dict) -> dict:
        return {"success": True, "message": "context", "data": self._context.get_context_dict()}

    def get_active_window(self, arguments: dict) -> dict:
        context = self._context.get_context()
        for window in context.open_windows:
            if window.title == context.active_window_title:
                return {"success": True, "message": self._active_message(window)}
        return {"success": True, "message": self._fallback_message(context)}

    def list_windows(self, arguments: dict) -> dict:
        windows = self._context.get_context().open_windows
        if not windows:
            return {"success": True, "message": "open windows:\n  none"}
        return {"success": True, "message": self._window_list(windows)}

    def _active_message(self, window: object) -> str:
        return f"active window: {window.title} -> {window.application} [{window.width}x{window.height} at {window.x},{window.y}]"

    def _fallback_message(self, context: object) -> str:
        return f"active window: {context.active_window_title} -> {context.active_application}"

    def _window_list(self, windows: list[object]) -> str:
        lines = "\n".join(f"  {item.title} -> {item.application} [{item.width}x{item.height} at {item.x},{item.y}]" for item in windows)
        return f"open windows:\n{lines}"
