import subprocess

from tusk.interfaces.context_provider import ContextProvider
from tusk.schemas.desktop_context import DesktopContext, WindowInfo

__all__ = ["GnomeContextProvider"]


class GnomeContextProvider(ContextProvider):
    def get_context(self) -> DesktopContext:
        windows = self._list_windows()
        active_title = self._get_active_window_title()
        active_app = self._resolve_active_app(active_title, windows)
        return DesktopContext(
            active_window_title=active_title,
            active_application=active_app,
            open_windows=windows,
        )

    def _list_windows(self) -> list[WindowInfo]:
        result = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True)
        return [
            self._parse_window_line(line)
            for line in result.stdout.splitlines()
            if line.strip()
        ]

    def _get_active_window_title(self) -> str:
        result = subprocess.run(
            ["xdotool", "getactivewindow", "getwindowname"],
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    def _parse_window_line(self, line: str) -> WindowInfo:
        parts = line.split(None, 3)
        window_id = parts[0] if len(parts) > 0 else ""
        title = parts[3] if len(parts) > 3 else ""
        return WindowInfo(window_id=window_id, title=title, application=title, is_active=False)

    def _resolve_active_app(self, active_title: str, windows: list[WindowInfo]) -> str:
        for window in windows:
            if window.title == active_title:
                return window.application
        return active_title
