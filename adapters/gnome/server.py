import json
import socket
import subprocess
import sys

try:
    from app_catalog import AppCatalog
    from gnome_clipboard_provider import GnomeClipboardProvider
    from gnome_context_provider import GnomeContextProvider
    from gnome_input_simulator import GnomeInputSimulator
    from gnome_text_paster import GnomeTextPaster
except ImportError:  # pragma: no cover
    from adapters.gnome.app_catalog import AppCatalog
    from adapters.gnome.gnome_clipboard_provider import GnomeClipboardProvider
    from adapters.gnome.gnome_context_provider import GnomeContextProvider
    from adapters.gnome.gnome_input_simulator import GnomeInputSimulator
    from adapters.gnome.gnome_text_paster import GnomeTextPaster

_SOCKET_PATH = "/tmp/tusk/launch.sock"


class GnomeServer:
    def __init__(self) -> None:
        self._apps = AppCatalog()
        self._clipboard = GnomeClipboardProvider()
        self._context = GnomeContextProvider(self._apps)
        self._input = GnomeInputSimulator()
        self._paster = GnomeTextPaster()
        self._tools = self._build_tools()

    def serve(self) -> None:
        for line in sys.stdin:
            request = json.loads(line)
            method = request.get("method")
            params = request.get("params", {})
            if method == "initialize":
                payload = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}}
            elif method == "tools/list":
                payload = {"tools": list(self._tools.values())}
            elif method == "tools/call":
                payload = self._call(params["name"], params.get("arguments", {}))
            else:
                payload = {}
            self._write(request["id"], payload)

    def _build_tools(self) -> dict:
        names = [
            ("launch_application", "Launch an application", {"application_name": "string"}),
            ("close_window", "Close a window", {"window_title": "string"}),
            ("focus_window", "Focus a window", {"window_title": "string"}),
            ("maximize_window", "Maximize a window", {"window_title": "string"}),
            ("minimize_window", "Minimize a window", {"window_title": "string"}),
            ("move_resize_window", "Move and resize a window", {"window_title": "string", "geometry": "string"}),
            ("switch_workspace", "Switch workspace", {"workspace_number": "string"}),
            ("press_keys", "Press keys", {"keys": "string"}),
            ("type_text", "Type text", {"text": "string"}),
            ("replace_recent_text", "Replace recent text", {"replace_chars": "string", "text": "string"}),
            ("mouse_click", "Mouse click", {"x": "string", "y": "string", "button": "string", "clicks": "string"}),
            ("mouse_move", "Mouse move", {"x": "string", "y": "string"}),
            ("mouse_drag", "Mouse drag", {"from_x": "string", "from_y": "string", "to_x": "string", "to_y": "string", "button": "string"}),
            ("mouse_scroll", "Mouse scroll", {"direction": "string", "clicks": "string"}),
            ("read_clipboard", "Read clipboard", {}),
            ("write_clipboard", "Write clipboard", {"text": "string"}),
            ("open_uri", "Open URI", {"uri": "string"}),
            ("get_desktop_context", "Get desktop context", {}),
            ("get_active_window", "Get the active window title, app name, and geometry", {}),
            ("list_windows", "List the currently open windows with app names and geometry", {}),
            ("search_applications", "Search installed desktop applications by name or exec command", {"query": "string"}),
        ]
        return {
            name: {
                "name": name,
                "description": description,
                "inputSchema": {
                    "type": "object",
                    "properties": {key: {"type": value} for key, value in fields.items()},
                },
            }
            for name, description, fields in names
        }

    def _call(self, name: str, arguments: dict) -> dict:
        data = getattr(self, f"_tool_{name}")(arguments)
        return {"content": [{"type": "text", "text": data["message"]}], "isError": not data["success"], "data": data.get("data")}

    def _tool_launch_application(self, arguments: dict) -> dict:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.connect(_SOCKET_PATH)
            sock.sendall(arguments["application_name"].encode("utf-8"))
            response = sock.recv(256).decode("utf-8")
        return {"success": response.startswith("ok"), "message": f"launched: {arguments['application_name']}"}

    def _tool_close_window(self, arguments: dict) -> dict:
        subprocess.run(["wmctrl", "-c", arguments["window_title"]], check=False)
        return {"success": True, "message": f"closed: {arguments['window_title']}"}

    def _tool_focus_window(self, arguments: dict) -> dict:
        subprocess.run(["wmctrl", "-a", arguments["window_title"]], check=False)
        return {"success": True, "message": f"focused: {arguments['window_title']}"}

    def _tool_maximize_window(self, arguments: dict) -> dict:
        title = arguments["window_title"]
        subprocess.run(["wmctrl", "-r", title, "-b", "add,maximized_vert,maximized_horz"], check=False)
        return {"success": True, "message": f"maximized: {title}"}

    def _tool_minimize_window(self, arguments: dict) -> dict:
        result = subprocess.run(["xdotool", "search", "--name", arguments["window_title"]], capture_output=True, text=True, check=False)
        lines = result.stdout.strip().splitlines()
        if not lines:
            return {"success": False, "message": f"window not found: {arguments['window_title']}"}
        subprocess.run(["xdotool", "windowminimize", lines[0]], check=False)
        return {"success": True, "message": f"minimized: {arguments['window_title']}"}

    def _tool_move_resize_window(self, arguments: dict) -> dict:
        title = arguments["window_title"]
        geometry = arguments["geometry"]
        subprocess.run(["wmctrl", "-r", title, "-e", f"0,{geometry}"], check=False)
        return {"success": True, "message": f"moved/resized: {title}"}

    def _tool_switch_workspace(self, arguments: dict) -> dict:
        number = arguments["workspace_number"]
        subprocess.run(["wmctrl", "-s", number], check=False)
        return {"success": True, "message": f"workspace: {number}"}

    def _tool_press_keys(self, arguments: dict) -> dict:
        self._input.press_keys(arguments["keys"])
        return {"success": True, "message": f"pressed: {arguments['keys']}"}

    def _tool_type_text(self, arguments: dict) -> dict:
        self._input.type_text(arguments["text"])
        return {"success": True, "message": "typed"}

    def _tool_replace_recent_text(self, arguments: dict) -> dict:
        self._paster.replace(int(arguments["replace_chars"]), arguments["text"])
        return {"success": True, "message": "replaced"}

    def _tool_mouse_click(self, arguments: dict) -> dict:
        self._input.mouse_click(int(arguments["x"]), int(arguments["y"]), int(arguments.get("button", "1")), int(arguments.get("clicks", "1")))
        return {"success": True, "message": "clicked"}

    def _tool_mouse_move(self, arguments: dict) -> dict:
        self._input.mouse_move(int(arguments["x"]), int(arguments["y"]))
        return {"success": True, "message": "moved"}

    def _tool_mouse_drag(self, arguments: dict) -> dict:
        self._input.mouse_drag(
            int(arguments["from_x"]),
            int(arguments["from_y"]),
            int(arguments["to_x"]),
            int(arguments["to_y"]),
            int(arguments.get("button", "1")),
        )
        return {"success": True, "message": "dragged"}

    def _tool_mouse_scroll(self, arguments: dict) -> dict:
        self._input.mouse_scroll(arguments["direction"], int(arguments.get("clicks", "1")))
        return {"success": True, "message": "scrolled"}

    def _tool_read_clipboard(self, arguments: dict) -> dict:
        text = self._clipboard.read()
        return {"success": bool(text), "message": text or "clipboard empty", "data": {"text": text}}

    def _tool_write_clipboard(self, arguments: dict) -> dict:
        self._clipboard.write(arguments["text"])
        return {"success": True, "message": "clipboard written"}

    def _tool_open_uri(self, arguments: dict) -> dict:
        subprocess.Popen(["xdg-open", arguments["uri"]])
        return {"success": True, "message": f"opened: {arguments['uri']}"}

    def _tool_get_desktop_context(self, arguments: dict) -> dict:
        return {"success": True, "message": "context", "data": self._context.get_context_dict()}

    def _tool_get_active_window(self, arguments: dict) -> dict:
        context = self._context.get_context()
        for window in context.open_windows:
            if window.title == context.active_window_title:
                message = f"active window: {window.title} -> {window.application} [{window.width}x{window.height} at {window.x},{window.y}]"
                return {"success": True, "message": message}
        return {"success": True, "message": f"active window: {context.active_window_title} -> {context.active_application}"}

    def _tool_list_windows(self, arguments: dict) -> dict:
        windows = self._context.get_context().open_windows
        if not windows:
            return {"success": True, "message": "open windows:\n  none"}
        lines = "\n".join(f"  {item.title} -> {item.application} [{item.width}x{item.height} at {item.x},{item.y}]" for item in windows)
        return {"success": True, "message": f"open windows:\n{lines}"}

    def _tool_search_applications(self, arguments: dict) -> dict:
        query = arguments["query"].strip()
        if not query:
            return {"success": False, "message": "search_applications requires a non-empty query"}
        matches = self._apps.search(query) if hasattr(self._apps, "search") else _search_apps(self._apps.list_apps(), query)
        if not matches:
            return {"success": False, "message": f"no applications found for: {query}"}
        lines = "\n".join(f"{item.name} -> {item.exec_cmd}" for item in matches)
        return {"success": True, "message": f"application matches for {query!r}:\n{lines}"}

    def _write(self, request_id: int, payload: dict) -> None:
        response = {"jsonrpc": "2.0", "id": request_id, "result": payload}
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


def main() -> None:
    GnomeServer().serve()


def _search_apps(apps: list[object], query: str) -> list[object]:
    ranked = []
    for item in apps:
        name = item.name.casefold()
        command = item.exec_cmd.casefold().split("/")[-1]
        score = 0 if name == query.casefold() else 1 if command == query.casefold() else 2 if name.startswith(query.casefold()) else 3 if command.startswith(query.casefold()) else 4 if query.casefold() in name else 5 if query.casefold() in command else None
        if score is not None:
            ranked.append(((score, name, command), item))
    return [item for _, item in sorted(ranked, key=lambda pair: pair[0])[:10]]


if __name__ == "__main__":
    main()
