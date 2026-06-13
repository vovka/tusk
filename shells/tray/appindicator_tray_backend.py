from shells.tray.interfaces.tray_backend import TrayBackend
from shells.tray.tray_menu_item import TrayMenuItem

try:
    import pystray
    from PIL import Image
except ImportError:  # pragma: no cover
    pystray = None
    Image = None

__all__ = ["AppIndicatorTrayBackend"]


class AppIndicatorTrayBackend(TrayBackend):
    def __init__(self, name: str = "tusk") -> None:
        if pystray is None:
            raise RuntimeError("pystray is not installed")
        self._icon = pystray.Icon(name)

    def run(self) -> None:
        self._icon.run()

    def stop(self) -> None:
        self._icon.stop()

    def set_icon(self, name: str) -> None:
        self._icon.icon = Image.open(name)

    def set_tooltip(self, text: str) -> None:
        self._icon.title = text

    def set_menu(self, items: tuple[TrayMenuItem, ...]) -> None:
        self._icon.menu = pystray.Menu(*[self._convert(item) for item in items])

    def _convert(self, item: TrayMenuItem) -> object:
        if item.children:
            submenu = pystray.Menu(*[self._convert(child) for child in item.children])
            return pystray.MenuItem(item.label, submenu)
        return pystray.MenuItem(item.label, self._callback(item.action), enabled=item.enabled)

    def _callback(self, action: object) -> object:
        if action is None:
            return None
        return lambda icon, menu_item: action()
