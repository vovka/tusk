import re
import subprocess

__all__ = ["WindowTools"]

_COMMA_GEOMETRY = re.compile(r"^-?\d+,-?\d+,\d+,\d+$")
_X11_GEOMETRY = re.compile(r"^(\d+)x(\d+)\+(-?\d+)\+(-?\d+)$")


class WindowTools:
    def close_window(self, arguments: dict) -> dict:
        title = self._present_title(arguments)
        if isinstance(title, dict):
            return title
        subprocess.run(["wmctrl", "-c", title], check=False)
        return {"success": True, "message": f"closed: {title}"}

    def focus_window(self, arguments: dict) -> dict:
        title = self._present_title(arguments)
        if isinstance(title, dict):
            return title
        subprocess.run(["wmctrl", "-a", title], check=False)
        return {"success": True, "message": f"focused: {title}"}

    def maximize_window(self, arguments: dict) -> dict:
        title = self._present_title(arguments)
        if isinstance(title, dict):
            return title
        subprocess.run(["wmctrl", "-r", title, "-b", "add,maximized_vert,maximized_horz"], check=False)
        return {"success": True, "message": f"maximized: {title}"}

    def minimize_window(self, arguments: dict) -> dict:
        lines = self._window_ids(arguments["window_title"])
        if not lines:
            return {"success": False, "message": f"window not found: {arguments['window_title']}"}
        subprocess.run(["xdotool", "windowminimize", lines[0]], check=False)
        return {"success": True, "message": f"minimized: {arguments['window_title']}"}

    def move_resize_window(self, arguments: dict) -> dict:
        title = self._present_title(arguments)
        if isinstance(title, dict):
            return title
        geometry = self._wmctrl_geometry(str(arguments["geometry"]).strip())
        if geometry is None:
            return {"success": False, "message": f"bad geometry {arguments['geometry']!r}: use X,Y,WIDTH,HEIGHT in pixels"}
        result = subprocess.run(["wmctrl", "-r", title, "-e", f"0,{geometry}"], check=False)
        if result.returncode != 0:
            return {"success": False, "message": f"wmctrl rejected geometry {geometry!r}"}
        return {"success": True, "message": f"moved/resized: {title}"}

    def switch_workspace(self, arguments: dict) -> dict:
        subprocess.run(["wmctrl", "-s", arguments["workspace_number"]], check=False)
        return {"success": True, "message": f"workspace: {arguments['workspace_number']}"}

    def _window_ids(self, window_title: str) -> list[str]:
        # xdotool treats --name as a regex and also finds invisible helper windows; escape and restrict
        command = ["xdotool", "search", "--onlyvisible", "--name", re.escape(window_title)]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        return result.stdout.strip().splitlines()

    def _wmctrl_geometry(self, geometry: str) -> str | None:
        # models produce either X,Y,W,H or X11 WxH+X+Y; wmctrl -e only understands the former
        if _COMMA_GEOMETRY.match(geometry):
            return geometry
        match = _X11_GEOMETRY.match(geometry)
        if match is None:
            return None
        width, height, x, y = match.groups()
        return f"{x},{y},{width},{height}"

    def _present_title(self, arguments: dict) -> str | dict:
        title = self._title(arguments)
        if isinstance(title, dict):
            return title
        if not self._window_exists(title):
            return {"success": False, "message": f"window not found: {title}"}
        return title

    def _window_exists(self, title: str) -> bool:
        result = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True, check=False)
        listed = (line.split(None, 3) for line in result.stdout.splitlines())
        return any(title.lower() in columns[3].lower() for columns in listed if len(columns) == 4)

    def _title(self, arguments: dict) -> str | dict:
        title = str(arguments.get("window_title", "")).strip()
        return title or {"success": False, "message": "missing argument: window_title"}
