import os
import sys
import uuid
from typing import TextIO

from adapters.coding.coding_edit_planner import CodingEditPlanner
from adapters.coding.coding_tool_schema_catalog import CodingToolSchemaCatalog
from tusk.shared.mcp.mcp_stdio_server import MCPStdioServer


class CodingServer:
    def __init__(
        self, planner: object,
        input_stream: TextIO = sys.stdin, output_stream: TextIO = sys.stdout,
    ) -> None:
        self._sessions: dict[str, str] = {}
        self._planner = planner
        self._schemas = CodingToolSchemaCatalog().build()
        self._rpc = MCPStdioServer("coding", lambda: self._schemas, self._call, input_stream, output_stream)

    def serve(self) -> None:
        self._rpc.serve()

    def _call(self, name: str, arguments: dict) -> dict:
        payload = getattr(self, f"_tool_{name}")(arguments)
        return {"content": [{"type": "text", "text": payload["message"]}], "isError": not payload["success"], "data": payload.get("data")}

    def _tool_start_coding_session(self, arguments: dict) -> dict:
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = arguments.get("initial_buffer", "")
        return {"success": True, "message": "coding started", "data": {"session_id": session_id}}

    def _tool_process_intent(self, arguments: dict) -> dict:
        session_id = arguments["session_id"]
        old_buffer = self._sessions[session_id]
        new_buffer = self._planner.plan(arguments["intent"], old_buffer)
        if new_buffer is None:
            return {"success": False, "message": "couldn't plan that edit"}
        self._sessions[session_id] = new_buffer
        operations = [_replace_operation(old_buffer, new_buffer)]
        return {"success": True, "message": "coding updated", "data": {"operations": operations, "should_stop": False}}

    def _tool_stop_coding_session(self, arguments: dict) -> dict:
        self._sessions.pop(arguments["session_id"], None)
        return {"success": True, "message": "coding stopped"}

def _replace_operation(old_buffer: str, new_buffer: str) -> dict:
    return {
        "kind": "replace",
        "target_start": 1,
        "target_end": len(old_buffer.split("\n")),
        "new_text": new_buffer,
        "full_buffer": new_buffer,
    }


def _default_planner() -> CodingEditPlanner:  # pragma: no cover
    from tusk.providers.llm import ConfigurableLLMFactory

    factory = ConfigurableLLMFactory(os.environ.get("GROQ_API_KEY", ""), os.environ.get("OPENROUTER_API_KEY", ""))
    return CodingEditPlanner(factory.create("groq", os.environ.get("CODING_AGENT_MODEL", "llama-3.3-70b-versatile")))


def main() -> None:  # pragma: no cover
    CodingServer(_default_planner()).serve()


if __name__ == "__main__":  # pragma: no cover
    main()
