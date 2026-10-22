import sys
import uuid
from typing import TextIO

from adapters.dictation.dictation_session_store import DictationSessionStore
from tusk.shared.mcp.mcp_stdio_server import MCPStdioServer, tool_result, tool_schema

TOOL_SCHEMAS = [
    tool_schema("start_dictation", "start dictation", {}),
    tool_schema("process_segment", "process segment", {"session_id": "string", "text": "string"}),
    tool_schema("stop_dictation", "stop dictation", {"session_id": "string"}),
]


class DictationServer:
    def __init__(
        self, sessions: DictationSessionStore | None = None,
        input_stream: TextIO = sys.stdin, output_stream: TextIO = sys.stdout,
    ) -> None:
        self._sessions = sessions or DictationSessionStore()
        self._rpc = MCPStdioServer("dictation", lambda: TOOL_SCHEMAS, self._call, input_stream, output_stream)

    def serve(self) -> None:
        self._rpc.serve()

    def _call(self, name: str, arguments: dict) -> dict:
        handler = getattr(self, f"_tool_{name}", None)
        if handler is None:
            return tool_result({"success": False, "message": f"unknown tool: {name}"})
        return tool_result(handler(arguments))

    def _tool_start_dictation(self, arguments: dict) -> dict:
        # ponytail: prune only here — sessions are only created here, so growth stays bounded.
        self._sessions.prune_stale()
        session_id = str(uuid.uuid4())
        self._sessions.set(session_id, "")
        return {"success": True, "message": "dictation started", "data": {"session_id": session_id}}

    def _tool_process_segment(self, arguments: dict) -> dict:
        session_id = arguments["session_id"]
        if session_id not in self._sessions:
            return {"success": False, "message": f"session {session_id} not found or expired"}
        text = arguments["text"].strip()
        previous = self._sessions.get(session_id)
        segment = self._segment(previous, text)
        self._sessions.set(session_id, f"{previous}{segment}")
        return self._update_payload(segment)

    def _tool_stop_dictation(self, arguments: dict) -> dict:
        self._sessions.pop(arguments["session_id"])
        return {"success": True, "message": "dictation stopped"}

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
