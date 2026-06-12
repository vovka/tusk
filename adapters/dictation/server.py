import json
import sys
import uuid

try:
    from dictation_session_store import DictationSessionStore
    from dictation_tool_schema_catalog import DictationToolSchemaCatalog
except ImportError:  # pragma: no cover
    from adapters.dictation.dictation_session_store import DictationSessionStore
    from adapters.dictation.dictation_tool_schema_catalog import DictationToolSchemaCatalog

class DictationServer:
    def __init__(self, sessions: DictationSessionStore | None = None) -> None:
        self._sessions = sessions or DictationSessionStore()
        self._schemas = DictationToolSchemaCatalog().build()

    def serve(self) -> None:
        for line in sys.stdin:
            self._handle_line(line)

    def _handle_line(self, line: str) -> None:
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            return
        if "id" not in request:
            return
        self._write(request["id"], self._payload(request))

    def _call(self, name: str, arguments: dict) -> dict:
        handler = getattr(self, f"_tool_{name}", None)
        if handler is None:
            return self._error_content(f"unknown tool: {name}")
        payload = handler(arguments)
        return {"content": [{"type": "text", "text": payload["message"]}], "isError": not payload["success"], "data": payload.get("data")}

    def _safe_call(self, name: str, arguments: dict) -> dict:
        try:
            return self._call(name, arguments)
        except Exception as exc:
            return self._error_content(f"tool {name} failed: {exc}")

    def _error_content(self, message: str) -> dict:
        return {"content": [{"type": "text", "text": message}], "isError": True, "data": None}

    def _tool_start_dictation(self, arguments: dict) -> dict:
        # ponytail: prune only here — sessions are only created here, so growth stays bounded.
        self._sessions.prune_stale()
        session_id = str(uuid.uuid4())
        self._sessions.set(session_id, "")
        return {"success": True, "message": "dictation started", "data": {"session_id": session_id}}

    def _tool_process_segment(self, arguments: dict) -> dict:
        session_id = arguments["session_id"]
        text = arguments["text"].strip()
        previous = self._sessions.get(session_id)
        segment = self._segment(previous, text)
        self._sessions.set(session_id, f"{previous}{segment}")
        return self._update_payload(segment)

    def _tool_stop_dictation(self, arguments: dict) -> dict:
        self._sessions.pop(arguments["session_id"])
        return {"success": True, "message": "dictation stopped"}

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
            return {"tools": self._schemas}
        if method == "tools/call":
            return self._safe_call(params.get("name", ""), params.get("arguments", {}))
        return {}

    def _segment(self, previous: str, text: str) -> str:
        if not previous or not text or text[0] in ",.!?:;)]}":
            return text
        return f" {text}"

    def _update_payload(self, text: str) -> dict:
        data = self._edit_data(text)
        return {"success": True, "message": "dictation updated", "data": data}

    def _edit_data(self, text: str) -> dict:
        return {
            "operation": "insert",
            "text": text,
            "replace_chars": 0,
            "should_stop": False,
        }


def main() -> None:
    DictationServer().serve()


if __name__ == "__main__":
    main()
