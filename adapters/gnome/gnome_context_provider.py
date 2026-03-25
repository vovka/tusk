import subprocess
from dataclasses import asdict

try:
    from app_catalog import AppCatalog
    from desktop_context import DesktopContext
    from window_info import WindowInfo
except ImportError:  # pragma: no cover
    from adapters.gnome.app_catalog import AppCatalog
    from adapters.gnome.desktop_context import DesktopContext
    from adapters.gnome.window_info import WindowInfo

__all__ = ["GnomeContextProvider"]


class GnomeContextProvider:
    def __init__(self, app_catalog: AppCatalog) -> None:
        self._catalog = app_catalog

    def get_context(self) -> DesktopContext:
        windows = self._list_windows()
        active_title = self._get_active_window_title()
        active_app = self._resolve_active_app(active_title, windows)
        return DesktopContext(
            active_window_title=active_title,
            active_application=active_app,
            open_windows=windows,
            available_applications=self._catalog.list_apps(),
        )

    def get_context_dict(self) -> dict:
        return asdict(self.get_context())

    def _list_windows(self) -> list[WindowInfo]:
        result = subprocess.run(["wmctrl", "-l", "-G"], capture_output=True, text=True)
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
        parts = line.split(None, 8)
        return WindowInfo(*self._window_values(parts))

    def _resolve_active_app(self, active_title: str, windows: list[WindowInfo]) -> str:
        for window in windows:
            if window.title == active_title:
                return window.application
        return active_title

    def _geometry(self, parts: list[str]) -> tuple[int, int, int, int]:
        values = [self._part(parts, index) for index in range(2, 6)]
        return values[0], values[1], values[2], values[3]

    def _part(self, parts: list[str], index: int) -> int:
        return int(parts[index]) if len(parts) > index else 0

    def _title(self, parts: list[str]) -> str:
        return parts[8] if len(parts) > 8 else ""

    def _window_values(self, parts: list[str]) -> tuple[object, ...]:
        geometry = self._geometry(parts)
        title = self._title(parts)
        return parts[0] if parts else "", title, title, False, *geometry
