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
            if "id" not in request:
                continue
            self._write(request["id"], self._payload(request))

    def _call(self, name: str, arguments: dict) -> dict:
        return self._router.call(name, arguments)

    def _payload(self, request: dict) -> dict:
        try:
            return self._safe_payload(request)
        except Exception as exc:
            return {"content": [{"type": "text", "text": f"adapter error: {exc}"}], "isError": True}

    def _safe_payload(self, request: dict) -> dict:
        method = request.get("method")
        params = request.get("params", {})
        if method == "initialize":
            return self._initialize_result()
        if method == "tools/list":
            return {"tools": list(self._router.schemas().values())}
        if method == "tools/call":
            return self._call(params["name"], params.get("arguments", {}))
        return {}

    def _initialize_result(self) -> dict:
        info = {"name": "gnome", "version": "1.0.0"}
        return {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": info}

    def _write(self, request_id: int, payload: dict) -> None:
        response = {"jsonrpc": "2.0", "id": request_id, "result": payload}
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


def main() -> None:
    GnomeServer().serve()


if __name__ == "__main__":
    main()
