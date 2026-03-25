import json
import sys
import uuid

try:
    from dictation_refiner import DictationRefiner
    from dictation_tool_schema_catalog import DictationToolSchemaCatalog
except ImportError:  # pragma: no cover
    from adapters.dictation.dictation_refiner import DictationRefiner
    from adapters.dictation.dictation_tool_schema_catalog import DictationToolSchemaCatalog

_STOP_WORDS = {"stop dictation", "finish dictation", "end dictation"}


class DictationServer:
    def __init__(self) -> None:
        self._sessions: dict[str, str] = {}
        self._refiner = DictationRefiner()
        self._schemas = DictationToolSchemaCatalog().build()

    def serve(self) -> None:
        for line in sys.stdin:
            request = json.loads(line)
            self._write(request["id"], self._payload(request))

    def _call(self, name: str, arguments: dict) -> dict:
        payload = getattr(self, f"_tool_{name}")(arguments)
        return {"content": [{"type": "text", "text": payload["message"]}], "isError": not payload["success"], "data": payload.get("data")}

    def _tool_start_dictation(self, arguments: dict) -> dict:
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = ""
        return {"success": True, "message": "dictation started", "data": {"session_id": session_id}}

    def _tool_process_segment(self, arguments: dict) -> dict:
        session_id = arguments["session_id"]
        text = arguments["text"].strip()
        if text.lower() in _STOP_WORDS:
            return self._stop_payload(session_id)
        previous = self._sessions.get(session_id, "")
        cleaned = self._refiner.refine(self._combined(previous, text))
        self._sessions[session_id] = cleaned
        return self._update_payload(previous, cleaned)

    def _tool_stop_dictation(self, arguments: dict) -> dict:
        self._sessions.pop(arguments["session_id"], None)
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
            return self._call(params["name"], params.get("arguments", {}))
        return {}

    def _stop_payload(self, session_id: str) -> dict:
        data = {"operation": "replace", "text": self._sessions.get(session_id, ""), "replace_chars": 0, "should_stop": True}
        return {"success": True, "message": "dictation stopped", "data": data}

    def _combined(self, previous: str, text: str) -> str:
        return f"{previous} {text}".strip()

    def _update_payload(self, previous: str, cleaned: str) -> dict:
        data = self._edit_data(previous, cleaned)
        return {"success": True, "message": "dictation updated", "data": data}

    def _edit_data(self, previous: str, cleaned: str) -> dict:
        return {
            "operation": "replace" if previous else "insert",
            "text": cleaned,
            "replace_chars": len(previous) if previous else 0,
            "should_stop": False,
        }


def main() -> None:
    DictationServer().serve()


if __name__ == "__main__":
    main()
