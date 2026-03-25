import subprocess
from dataclasses import asdict, dataclass

try:
    from app_catalog import AppCatalog
except ImportError:  # pragma: no cover
    from adapters.gnome.app_catalog import AppCatalog

__all__ = ["GnomeContextProvider"]


@dataclass(frozen=True)
class WindowInfo:
    window_id: str
    title: str
    application: str
    is_active: bool
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0


@dataclass(frozen=True)
class DesktopContext:
    active_window_title: str
    active_application: str
    open_windows: list[WindowInfo]
    available_applications: list[object]


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
        # wmctrl -l -G: window_id desktop x y w h host title
        parts = line.split(None, 8)
        window_id = parts[0] if len(parts) > 0 else ""
        title = parts[8] if len(parts) > 8 else ""
        return WindowInfo(
            window_id=window_id,
            title=title,
            application=title,
            is_active=False,
            x=int(parts[2]) if len(parts) > 2 else 0,
            y=int(parts[3]) if len(parts) > 3 else 0,
            width=int(parts[4]) if len(parts) > 4 else 0,
            height=int(parts[5]) if len(parts) > 5 else 0,
        )

    def _resolve_active_app(self, active_title: str, windows: list[WindowInfo]) -> str:
        for window in windows:
            if window.title == active_title:
                return window.application
        return active_title
