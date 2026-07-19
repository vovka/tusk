import socket
import subprocess
import time
from typing import Callable

__all__ = ["ApplicationTools"]

_SOCKET_PATH = "/tmp/tusk/launch.sock"
_POLL_INTERVAL_SECONDS = 0.5
_POLL_TIMEOUT_SECONDS = 10.0


class ApplicationTools:
    def __init__(self, app_catalog: object, sleep: Callable[[float], None] = time.sleep) -> None:
        self._apps = app_catalog
        self._sleep = sleep

    # Latency: bounded worst case, adds up to 10s to the launch path while polling for the new window.
    def launch_application(self, arguments: dict) -> dict:
        requested = arguments["application_name"]
        command = self._resolve(requested)
        if command is None:
            return {"success": False, "message": f"no applications found for: {requested}"}
        before_ids = self._window_ids()
        response = self._launch(command)
        if not response.startswith("ok"):
            return {"success": False, "message": self._message(requested, response)}
        return {"success": True, "message": self._launched_message(requested, before_ids)}

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

    def _resolve(self, application_name: str) -> str | None:
        matches = self._apps.search(application_name, limit=1)
        return matches[0].exec_cmd if matches else None

    def _message(self, requested: str, response: str) -> str:
        return f"launched: {requested}" if response.startswith("ok") else response.strip()

    def _search_message(self, query: str, matches: list[object]) -> str:
        lines = "\n".join(f"{item.name} -> {item.exec_cmd}" for item in matches)
        return f"application matches for {query!r}:\n{lines}"

    def _launched_message(self, requested: str, before_ids: set[str]) -> str:
        title = self._poll_for_new_window(before_ids)
        if title is None:
            return f"launched: {requested} (no new window appeared within 10s)"
        return f'launched: {requested}, window "{title}" open'

    def _poll_for_new_window(self, before: set[str]) -> str | None:
        elapsed = 0.0
        while True:
            title = self._new_window_title(before)
            if title is not None:
                return title
            if elapsed >= _POLL_TIMEOUT_SECONDS:
                return None
            self._sleep(_POLL_INTERVAL_SECONDS)
            elapsed += _POLL_INTERVAL_SECONDS

    def _new_window_title(self, before: set[str]) -> str | None:
        for window_id, title in self._list_windows():
            if window_id not in before:
                return title
        return None

    def _list_windows(self) -> list[tuple[str, str]]:
        try:
            result = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True, check=False)
        except FileNotFoundError:
            return []
        if result.returncode != 0:
            return []
        return [self._parse_window_line(line) for line in result.stdout.splitlines() if line.strip()]

    def _parse_window_line(self, line: str) -> tuple[str, str]:
        columns = line.split(None, 3)
        return columns[0], columns[3] if len(columns) > 3 else ""

    def _window_ids(self) -> set[str]:
        return {window_id for window_id, _ in self._list_windows()}
