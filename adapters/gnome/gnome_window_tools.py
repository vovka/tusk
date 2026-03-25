import subprocess

__all__ = ["GnomeWindowTools"]


class GnomeWindowTools:
    def close_window(self, arguments: dict) -> dict:
        title = self._title(arguments)
        if isinstance(title, dict):
            return title
        subprocess.run(["wmctrl", "-c", title], check=False)
        return {"success": True, "message": f"closed: {title}"}

    def focus_window(self, arguments: dict) -> dict:
        title = self._title(arguments)
        if isinstance(title, dict):
            return title
        subprocess.run(["wmctrl", "-a", title], check=False)
        return {"success": True, "message": f"focused: {title}"}

    def maximize_window(self, arguments: dict) -> dict:
        title = self._title(arguments)
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
        title = arguments["window_title"]
        subprocess.run(["wmctrl", "-r", title, "-e", f"0,{arguments['geometry']}"], check=False)
        return {"success": True, "message": f"moved/resized: {title}"}

    def switch_workspace(self, arguments: dict) -> dict:
        subprocess.run(["wmctrl", "-s", arguments["workspace_number"]], check=False)
        return {"success": True, "message": f"workspace: {arguments['workspace_number']}"}

    def _window_ids(self, window_title: str) -> list[str]:
        result = subprocess.run(["xdotool", "search", "--name", window_title], capture_output=True, text=True, check=False)
        return result.stdout.strip().splitlines()

    def _title(self, arguments: dict) -> str | dict:
        title = str(arguments.get("window_title", "")).strip()
        return title or {"success": False, "message": "missing argument: window_title"}
