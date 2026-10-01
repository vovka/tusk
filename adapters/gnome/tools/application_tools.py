import os
import socket
import subprocess
import time
from typing import Callable

from adapters.gnome.tools.launched_window_guard import LaunchedWindowGuard

__all__ = ["ApplicationTools"]

_SOCKET_PATH = "/tmp/tusk/launch.sock"
_POLL_INTERVAL_SECONDS = 0.5
_POLL_TIMEOUT_SECONDS = 10.0


class ApplicationTools:
    def __init__(
        self,
        app_catalog: object,
        sleep: Callable[[float], None] = time.sleep,
        window_lister: Callable[[], list[tuple[str, str, str]]] = lambda: [],
        launched: LaunchedWindowGuard | None = None,
    ) -> None:
        self._apps = app_catalog
        self._sleep = sleep
        self._window_lister = window_lister
        self._launched = launched

    # Latency: bounded worst case, adds up to 10s to the launch path while polling for the new window.
    def launch_application(self, arguments: dict) -> dict:
        requested = arguments["application_name"]
        app = self._resolve(requested)
        if app is None:
            return {"success": False, "message": self._no_match_message(requested)}
        before = self._window_lister()
        response = self._launch(app.exec_cmd)
        if not response.startswith("ok"):
            return {"success": False, "message": response.strip()}
        return self._verified_launch(requested, app, before)

    def open_uri(self, arguments: dict) -> dict:
        subprocess.Popen(["xdg-open", arguments["uri"]])
        return {"success": True, "message": f"opened: {arguments['uri']}"}

    def search_applications(self, arguments: dict) -> dict:
        query = arguments["query"].strip()
        if not query:
            return {"success": False, "message": "search_applications requires a non-empty query"}
        matches = self._apps.search(query)
        if not matches:
            return {"success": False, "message": f"no applications found for: {query}"}
        return {"success": True, "message": self._search_message(query, matches)}

    def _launch(self, application_name: str) -> str:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.connect(_SOCKET_PATH)
            sock.sendall(application_name.encode("utf-8"))
            return sock.recv(256).decode("utf-8")

    def _resolve(self, application_name: str) -> object | None:
        matches = self._apps.search(application_name, limit=1)
        return matches[0] if matches else None

    def _no_match_message(self, requested: str) -> str:
        candidates = self._apps.suggest(requested)
        suffix = f"; closest: {', '.join(candidates)}" if candidates else ""
        return f"no applications found for: {requested}{suffix}"

    def _search_message(self, query: str, matches: list[object]) -> str:
        lines = "\n".join(f"{item.name} -> {item.exec_cmd}" for item in matches)
        return f"application matches for {query!r}:\n{lines}"

    def _verified_launch(self, requested: str, app: object, before: list[tuple[str, str, str]]) -> dict:
        window = self._poll_for_app_window(app, {item[0] for item in before})
        window = window or next((item for item in before if _belongs(app, item[2])), None)
        if window is None:
            return {"success": False, "message": self._missing_window_message(requested, app, before)}
        if self._launched is not None:
            self._launched.remember(window[0], window[1])
        return {"success": True, "message": f'launched: {requested}, window "{window[1]}" of {app.name} open'}

    def _missing_window_message(self, requested: str, app: object, before: list[tuple[str, str, str]]) -> str:
        known = {item[0] for item in before}
        strays = [f'"{item[1]}" ({item[2]})' for item in self._window_lister() if item[0] not in known]
        suffix = f"; other new windows: {', '.join(strays)}" if strays else ""
        return f"launched {requested} but no {app.name} window appeared within 10s{suffix}"

    def _poll_for_app_window(self, app: object, before: set[str]) -> tuple[str, str, str] | None:
        elapsed = 0.0
        while True:
            window = self._new_app_window(app, before)
            if window is not None or elapsed >= _POLL_TIMEOUT_SECONDS:
                return window
            self._sleep(_POLL_INTERVAL_SECONDS)
            elapsed += _POLL_INTERVAL_SECONDS

    def _new_app_window(self, app: object, before: set[str]) -> tuple[str, str, str] | None:
        return next((item for item in self._window_lister() if item[0] not in before and _belongs(app, item[2])), None)


def _belongs(app: object, wm_class: str) -> bool:
    # Unknown class cannot be checked; otherwise any WM_CLASS part must overlap the command or desktop id.
    names = {os.path.basename(app.exec_cmd).casefold(), app.desktop_id.removesuffix(".desktop").casefold()} - {""}
    parts = [part.casefold() for part in wm_class.split(".") if part]
    if not parts or wm_class == "N/A":
        return True
    return any(part in name or name in part for part in parts for name in names)
