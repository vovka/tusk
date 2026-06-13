import json
import os
import sys
import uuid

try:
    from buffer_model import BufferModel
    from coding_edit_planner import CodingEditPlanner
    from coding_tool_schema_catalog import CodingToolSchemaCatalog
except ImportError:  # pragma: no cover
    from adapters.coding.buffer_model import BufferModel
    from adapters.coding.coding_edit_planner import CodingEditPlanner
    from adapters.coding.coding_tool_schema_catalog import CodingToolSchemaCatalog


class CodingServer:
    def __init__(self, planner: object) -> None:
        self._sessions: dict[str, BufferModel] = {}
        self._planner = planner
        self._schemas = CodingToolSchemaCatalog().build()

    def serve(self) -> None:
        for line in sys.stdin:
            request = json.loads(line)
            self._write(request["id"], self._payload(request))

    def _call(self, name: str, arguments: dict) -> dict:
        payload = getattr(self, f"_tool_{name}")(arguments)
        return {"content": [{"type": "text", "text": payload["message"]}], "isError": not payload["success"], "data": payload.get("data")}

    def _tool_start_coding_session(self, arguments: dict) -> dict:
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = BufferModel.from_text(arguments.get("initial_buffer", ""))
        return {"success": True, "message": "coding started", "data": {"session_id": session_id}}

    def _tool_process_intent(self, arguments: dict) -> dict:
        session_id = arguments["session_id"]
        operations, model = self._apply_intent(self._sessions[session_id], arguments["intent"])
        self._sessions[session_id] = model
        return {"success": True, "message": "coding updated", "data": {"operations": operations, "should_stop": False}}

    def _tool_stop_coding_session(self, arguments: dict) -> dict:
        self._sessions.pop(arguments["session_id"], None)
        return {"success": True, "message": "coding stopped"}

    def _apply_intent(self, model: BufferModel, intent: str) -> tuple[list[dict], BufferModel]:
        applied: list[dict] = []
        for operation in self._planner.plan(intent, model.to_text()):
            model = model.with_edit(operation)
            applied.append({**operation, "full_buffer": model.to_text()})
        return applied, model

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


def _default_planner() -> CodingEditPlanner:  # pragma: no cover
    from tusk.providers.llm import ConfigurableLLMFactory

    factory = ConfigurableLLMFactory(os.environ.get("GROQ_API_KEY", ""), os.environ.get("OPENROUTER_API_KEY", ""))
    return CodingEditPlanner(factory.create("groq", os.environ.get("CODING_AGENT_MODEL", "llama-3.3-70b-versatile")))


def main() -> None:  # pragma: no cover
    CodingServer(_default_planner()).serve()


if __name__ == "__main__":  # pragma: no cover
    main()
