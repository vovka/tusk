import socket
import subprocess

__all__ = ["GnomeApplicationTools"]

_SOCKET_PATH = "/tmp/tusk/launch.sock"


class GnomeApplicationTools:
    def __init__(self, app_catalog: object) -> None:
        self._apps = app_catalog

    def launch_application(self, arguments: dict) -> dict:
        requested = arguments["application_name"]
        command = self._resolve(requested)
        if command is None:
            return {"success": False, "message": f"no applications found for: {requested}"}
        response = self._launch(command)
        return {"success": response.startswith("ok"), "message": self._message(requested, response)}

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
