import re
import subprocess
from typing import Callable

__all__ = ["WindowTools"]

_COMMA_GEOMETRY = re.compile(r"^-?\d+,-?\d+,\d+,\d+$")
_X11_GEOMETRY = re.compile(r"^(\d+)x(\d+)([+-]\d+)([+-]\d+)$")
_MAXIMIZED = "maximized_vert,maximized_horz"


class WindowTools:
    def close_window(self, arguments: dict) -> dict:
        return self._act(arguments, "closed", lambda window_id: [["wmctrl", "-i", "-c", window_id]])

    def focus_window(self, arguments: dict) -> dict:
        return self._act(arguments, "focused", lambda window_id: [["wmctrl", "-i", "-a", window_id]])

    def maximize_window(self, arguments: dict) -> dict:
        return self._act(arguments, "maximized", lambda window_id: [["wmctrl", "-i", "-r", window_id, "-b", f"add,{_MAXIMIZED}"]])

    def minimize_window(self, arguments: dict) -> dict:
        return self._act(arguments, "minimized", lambda window_id: [["xdotool", "windowminimize", str(int(window_id, 16))]])

    def move_resize_window(self, arguments: dict) -> dict:
        target = self._target(arguments)
        geometry = target if isinstance(target, dict) else self._parsed_geometry(arguments)
        if isinstance(geometry, dict):
            return geometry
        result = subprocess.run(["wmctrl", "-i", "-r", target[0], "-e", f"0,{geometry}"], check=False)
        if result.returncode != 0:
            return {"success": False, "message": f"wmctrl rejected geometry {geometry!r}"}
        return {"success": True, "message": f"moved/resized: {target[1]}"}

    def tile_window(self, arguments: dict) -> dict:
        side = self._side(arguments)
        size = side if isinstance(side, dict) else self._display_size()
        if isinstance(size, dict):
            return size
        half_width, height = size[0] // 2, size[1]
        geometry = f"0,{0 if side == 'left' else half_width},0,{half_width},{height}"
        return self._act(arguments, f"tiled {side}", lambda window_id: self._tile_commands(window_id, geometry))

    def _tile_commands(self, window_id: str, geometry: str) -> list[list[str]]:
        unmaximize = ["wmctrl", "-i", "-r", window_id, "-b", f"remove,{_MAXIMIZED}"]
        return [unmaximize, ["wmctrl", "-i", "-r", window_id, "-e", geometry]]

    def switch_workspace(self, arguments: dict) -> dict:
        subprocess.run(["wmctrl", "-s", arguments["workspace_number"]], check=False)
        return {"success": True, "message": f"workspace: {arguments['workspace_number']}"}

    def _act(self, arguments: dict, verb: str, commands: Callable[[str], list[list[str]]]) -> dict:
        target = self._target(arguments)
        if isinstance(target, dict):
            return target
        for command in commands(target[0]):
            subprocess.run(command, check=False)
        return {"success": True, "message": f"{verb}: {target[1]}"}

    def _target(self, arguments: dict) -> tuple[str, str] | dict:
        title = self._title(arguments)
        if isinstance(title, dict):
            return title
        window_id = self._resolve(title, self._listed_windows())
        return window_id if isinstance(window_id, dict) else (window_id, title)

    def _resolve(self, title: str, windows: list[tuple[str, str]]) -> str | dict:
        # Exact (case-insensitive) title first; a substring must be unique so we never act on the wrong window.
        lowered = title.lower()
        matches = [item for item in windows if item[1].lower() == lowered]
        matches = matches or [item for item in windows if lowered in item[1].lower()]
        if not matches:
            return {"success": False, "message": f"window not found: {title}"}
        if len(matches) > 1:
            candidates = "; ".join(item[1] for item in matches)
            return {"success": False, "message": f"ambiguous window title {title!r}: {candidates}"}
        return matches[0][0]

    def _listed_windows(self) -> list[tuple[str, str]]:
        result = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True, check=False)
        listed = (line.split(None, 3) for line in result.stdout.splitlines())
        return [(columns[0], columns[3]) for columns in listed if len(columns) == 4]

    def _display_size(self) -> tuple[int, int] | dict:
        # ponytail: whole X screen incl. panels and all monitors; use the work area if multi-monitor matters.
        result = subprocess.run(["xdotool", "getdisplaygeometry"], capture_output=True, text=True, check=False)
        parts = result.stdout.split()
        if result.returncode != 0 or len(parts) != 2:
            return {"success": False, "message": "cannot read display size from xdotool getdisplaygeometry"}
        return int(parts[0]), int(parts[1])

    def _side(self, arguments: dict) -> str | dict:
        side = str(arguments.get("side", "")).strip().lower()
        return side if side in ("left", "right") else {"success": False, "message": f"bad side {side!r}: use left or right"}

    def _wmctrl_geometry(self, geometry: str) -> str | None:
        # models produce either X,Y,W,H or X11 WxH+X+Y; wmctrl -e only understands the former
        if _COMMA_GEOMETRY.match(geometry):
            return geometry
        match = _X11_GEOMETRY.match(geometry)
        if match is None:
            return None
        width, height, x, y = match.groups()
        return f"{int(x)},{int(y)},{width},{height}"

    def _parsed_geometry(self, arguments: dict) -> str | dict:
        raw_geometry = arguments.get("geometry")
        if not raw_geometry:
            return {"success": False, "message": "missing argument: geometry"}
        geometry = self._wmctrl_geometry(str(raw_geometry).strip())
        if geometry is None:
            return {"success": False, "message": f"bad geometry {raw_geometry!r}: use X,Y,WIDTH,HEIGHT in pixels"}
        return geometry

    def _title(self, arguments: dict) -> str | dict:
        title = str(arguments.get("window_title", "")).strip()
        return title or {"success": False, "message": "missing argument: window_title"}
