import json

from adapters.gnome.app_catalog import AppCatalog
from adapters.gnome.wayland.shell_bus import ShellBus
from tusk.shared.schemas.desktop.desktop_context import DesktopContext
from tusk.shared.schemas.desktop.window_info import WindowInfo

__all__ = ["WaylandContextProvider"]


class WaylandContextProvider:
    """Builds the desktop context from the tusk-shell extension's window list."""

    def __init__(self, app_catalog: AppCatalog, bus: ShellBus) -> None:
        self._catalog = app_catalog
        self._bus = bus

    def get_context(self) -> DesktopContext:
        windows = [self._window(item) for item in json.loads(self._bus.call_string("ListWindows"))]
        active = next((window for window in windows if window.is_active), None)
        return DesktopContext(
            active_window_title=active.title if active else "",
            active_application=active.application if active else "",
            open_windows=windows,
            available_applications=self._catalog.list_apps(),
        )

    def _window(self, item: dict) -> WindowInfo:
        geometry = (item["x"], item["y"], item["width"], item["height"])
        return WindowInfo(str(item["id"]), item["title"], item["wm_class"] or item["title"], item["focused"], *geometry)
