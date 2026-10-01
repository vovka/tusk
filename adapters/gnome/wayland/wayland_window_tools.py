import json

from adapters.gnome.tools.window_tools import WindowTools
from adapters.gnome.wayland.shell_bus import ShellBus

__all__ = ["WaylandWindowTools"]


class WaylandWindowTools(WindowTools):
    """Window actions by title, resolved (exact match first, unique substring otherwise) to tusk-shell ids."""

    def __init__(self, bus: ShellBus) -> None:
        self._bus = bus

    def close_window(self, arguments: dict) -> dict:
        return self._call_window(arguments, "Close", "closed")

    def focus_window(self, arguments: dict) -> dict:
        return self._call_window(arguments, "Focus", "focused")

    def maximize_window(self, arguments: dict) -> dict:
        return self._call_window(arguments, "Maximize", "maximized")

    def minimize_window(self, arguments: dict) -> dict:
        return self._call_window(arguments, "Minimize", "minimized")

    def move_resize_window(self, arguments: dict) -> dict:
        title = self._title(arguments)
        geometry = title if isinstance(title, dict) else self._parsed_geometry(arguments)
        if isinstance(geometry, dict):
            return geometry
        return self._call_window(arguments, "MoveResize", "moved/resized", [int(value) for value in geometry.split(",")])

    def tile_window(self, arguments: dict) -> dict:
        side = self._side(arguments)
        if isinstance(side, dict):
            return side
        return self._call_window(arguments, "TileLeft" if side == "left" else "TileRight", f"tiled {side}")

    def switch_workspace(self, arguments: dict) -> dict:
        self._bus.call("SwitchWorkspace", [int(arguments["workspace_number"])])
        return {"success": True, "message": f"workspace: {arguments['workspace_number']}"}

    def list_windows(self) -> list[tuple[str, str]]:
        return [(str(item["id"]), item["title"]) for item in json.loads(self._bus.call_string("ListWindows"))]

    def _listed_windows(self) -> list[tuple[str, str]]:
        return self.list_windows()

    def _call_window(self, arguments: dict, method: str, verb: str, extra: list[int] | None = None) -> dict:
        target = self._target(arguments)
        if isinstance(target, dict):
            return target
        self._bus.call(method, [int(target[0]), *(extra or [])])
        return {"success": True, "message": f"{verb}: {target[1]}"}
