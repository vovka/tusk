import json

from adapters.gnome.tools.window_tools import WindowTools
from adapters.gnome.wayland.shell_bus import ShellBus

__all__ = ["WaylandWindowTools"]


class WaylandWindowTools(WindowTools):
    """Window actions by title substring, resolved to tusk-shell window ids."""

    def __init__(self, bus: ShellBus) -> None:
        self._bus = bus

    def close_window(self, arguments: dict) -> dict:
        return self._act(arguments, "Close", "closed")

    def focus_window(self, arguments: dict) -> dict:
        return self._act(arguments, "Focus", "focused")

    def maximize_window(self, arguments: dict) -> dict:
        return self._act(arguments, "Maximize", "maximized")

    def minimize_window(self, arguments: dict) -> dict:
        return self._act(arguments, "Minimize", "minimized")

    def move_resize_window(self, arguments: dict) -> dict:
        title = self._title(arguments)
        geometry = title if isinstance(title, dict) else self._parsed_geometry(arguments)
        if isinstance(geometry, dict):
            return geometry
        return self._act(arguments, "MoveResize", "moved/resized", [int(value) for value in geometry.split(",")])

    def tile_window(self, arguments: dict) -> dict:
        side = self._side(arguments)
        if isinstance(side, dict):
            return side
        return self._act(arguments, "TileLeft" if side == "left" else "TileRight", f"tiled {side}")

    def switch_workspace(self, arguments: dict) -> dict:
        self._bus.call("SwitchWorkspace", [int(arguments["workspace_number"])])
        return {"success": True, "message": f"workspace: {arguments['workspace_number']}"}

    def list_windows(self) -> list[tuple[str, str]]:
        return [(str(item["id"]), item["title"]) for item in json.loads(self._bus.call_string("ListWindows"))]

    def _act(self, arguments: dict, method: str, verb: str, extra: list[int] | None = None) -> dict:
        title = self._title(arguments)
        if isinstance(title, dict):
            return title
        window_id = self._window_id(title)
        if window_id is None:
            return {"success": False, "message": f"window not found: {title}"}
        self._bus.call(method, [window_id, *(extra or [])])
        return {"success": True, "message": f"{verb}: {title}"}

    def _window_id(self, title: str) -> int | None:
        matches = (window_id for window_id, window_title in self.list_windows() if title.lower() in window_title.lower())
        return next((int(window_id) for window_id in matches), None)
