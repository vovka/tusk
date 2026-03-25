from tusk.kernel.schemas.desktop_context import DesktopContext

__all__ = ["DesktopContextMessageBuilder"]

_MAX_STEPS = 12
_MAX_APPS = 40
_MAX_NAME = 40


class DesktopContextMessageBuilder:
    def build(self, context: DesktopContext) -> str:
        windows = self._windows(context)
        apps = self._apps(context)
        return "\n".join(self._lines(context, windows, apps))

    def _lines(self, context: DesktopContext, windows: str, apps: str) -> list[str]:
        return [
            "Desktop context:",
            f"Active window: {context.active_window_title}",
            f"Open windows:\n{windows}{self._window_tail(context)}",
            f"Available apps:\n{apps}{self._app_tail(context)}",
        ]

    def _windows(self, context: DesktopContext) -> str:
        items = context.open_windows[:_MAX_STEPS]
        lines = [f"  {item.title[:80]} [{item.width}x{item.height} at {item.x},{item.y}]" for item in items]
        return "\n".join(lines) or "  none"

    def _apps(self, context: DesktopContext) -> str:
        items = context.available_applications[:_MAX_APPS]
        lines = [f"  {item.name[:_MAX_NAME]}" for item in items]
        return "\n".join(lines) or "  none"

    def _window_tail(self, context: DesktopContext) -> str:
        return self._tail(len(context.open_windows) - _MAX_STEPS)

    def _app_tail(self, context: DesktopContext) -> str:
        return self._tail(len(context.available_applications) - _MAX_APPS)

    def _tail(self, remaining: int) -> str:
        return f"\n  ... and {remaining} more" if remaining > 0 else ""
