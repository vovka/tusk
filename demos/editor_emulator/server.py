import json
import sys
from pathlib import Path

try:
    from emulated_editor import EmulatedEditor
except ImportError:  # pragma: no cover
    from demos.editor_emulator.emulated_editor import EmulatedEditor

_SNAPSHOT_PATH = Path(__file__).resolve().parents[2] / ".tusk_runtime" / "editor_emulator_buffer.txt"


class EditorEmulatorServer:
    def __init__(self, editor: EmulatedEditor, snapshot_path: Path) -> None:
        self._editor = editor
        self._snapshot_path = snapshot_path

    def serve(self) -> None:
        for line in sys.stdin:
            request = json.loads(line)
            self._write(request["id"], self._payload(request))

    def _write(self, request_id: int, payload: dict) -> None:
        response = {"jsonrpc": "2.0", "id": request_id, "result": payload}
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()

    def _payload(self, request: dict) -> dict:
        method = request.get("method")
        params = request.get("params", {})
        if method == "initialize":
            return {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}}
        if method == "tools/list":
            return {"tools": self._schemas()}
        if method == "tools/call":
            return self._call(params["name"], params.get("arguments", {}))
        return {}

    def _call(self, name: str, arguments: dict) -> dict:
        payload = getattr(self, f"_tool_{name}")(arguments)
        self._snapshot()
        return {"content": [{"type": "text", "text": payload["message"]}], "isError": False, "data": payload.get("data")}

    def _tool_press_keys(self, arguments: dict) -> dict:
        self._editor.press_keys(arguments["keys"])
        return {"message": f"pressed {arguments['keys']}"}

    def _tool_type_text(self, arguments: dict) -> dict:
        self._editor.type_text(arguments["text"])
        return {"message": "typed"}

    def _tool_read_clipboard(self, arguments: dict) -> dict:
        return {"message": "clipboard read", "data": {"text": self._editor.clipboard}}

    def _tool_write_clipboard(self, arguments: dict) -> dict:
        self._editor.write_clipboard(arguments["text"])
        return {"message": "clipboard written"}

    def _schemas(self) -> list[dict]:
        return [
            self._schema("press_keys", {"keys": "string"}),
            self._schema("type_text", {"text": "string"}),
            self._schema("read_clipboard", {}),
            self._schema("write_clipboard", {"text": "string"}),
        ]

    def _schema(self, name: str, properties: dict[str, str]) -> dict:
        fields = {key: {"type": value} for key, value in properties.items()}
        return {"name": name, "description": name.replace("_", " "), "inputSchema": {"type": "object", "properties": fields}}

    def _snapshot(self) -> None:
        self._snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        self._snapshot_path.write_text(self._editor.buffer, encoding="utf-8")


def main() -> None:  # pragma: no cover
    EditorEmulatorServer(EmulatedEditor(), _SNAPSHOT_PATH).serve()


if __name__ == "__main__":  # pragma: no cover
    main()
