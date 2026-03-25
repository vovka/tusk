import json
import sys

try:
    from app_catalog import AppCatalog
    from gnome_clipboard_provider import GnomeClipboardProvider
    from gnome_context_provider import GnomeContextProvider
    from gnome_input_simulator import GnomeInputSimulator
    from gnome_tool_router import GnomeToolRouter
    from gnome_text_paster import GnomeTextPaster
except ImportError:  # pragma: no cover
    from adapters.gnome.app_catalog import AppCatalog
    from adapters.gnome.gnome_clipboard_provider import GnomeClipboardProvider
    from adapters.gnome.gnome_context_provider import GnomeContextProvider
    from adapters.gnome.gnome_input_simulator import GnomeInputSimulator
    from adapters.gnome.gnome_tool_router import GnomeToolRouter
    from adapters.gnome.gnome_text_paster import GnomeTextPaster


class GnomeServer:
    def __init__(self) -> None:
        self._apps = AppCatalog()
        self._clipboard = GnomeClipboardProvider()
        self._context = GnomeContextProvider(self._apps)
        self._input = GnomeInputSimulator()
        self._paster = GnomeTextPaster()
        self._router = GnomeToolRouter(self._apps, self._clipboard, self._context, self._input, self._paster)

    def serve(self) -> None:
        for line in sys.stdin:
            request = json.loads(line)
            self._write(request["id"], self._payload(request))

    def _call(self, name: str, arguments: dict) -> dict:
        return self._router.call(name, arguments)

    def _payload(self, request: dict) -> dict:
        method = request.get("method")
        params = request.get("params", {})
        if method == "initialize":
            return {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}}
        if method == "tools/list":
            return {"tools": list(self._router.schemas().values())}
        if method == "tools/call":
            return self._call(params["name"], params.get("arguments", {}))
        return {}

    def _tool_search_applications(self, arguments: dict) -> dict:
        return self._router._handlers["search_applications"](arguments)

    def _tool_list_windows(self, arguments: dict) -> dict:
        return self._router._handlers["list_windows"](arguments)

    def _tool_get_active_window(self, arguments: dict) -> dict:
        return self._router._handlers["get_active_window"](arguments)

    def _write(self, request_id: int, payload: dict) -> None:
        response = {"jsonrpc": "2.0", "id": request_id, "result": payload}
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


def main() -> None:
    GnomeServer().serve()


if __name__ == "__main__":
    main()
