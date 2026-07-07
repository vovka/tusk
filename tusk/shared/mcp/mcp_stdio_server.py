import json
import sys
from collections.abc import Callable
from typing import TextIO

__all__ = ["MCPStdioServer"]


class MCPStdioServer:
    """JSON-RPC 2.0 stdio request loop shared by all adapter servers."""

    def __init__(
        self,
        server_name: str,
        list_schemas: Callable[[], list[dict]],
        call_tool: Callable[[str, dict], dict],
        input_stream: TextIO = sys.stdin,
        output_stream: TextIO = sys.stdout,
    ) -> None:
        self._server_name = server_name
        self._list_schemas = list_schemas
        self._call_tool = call_tool
        self._input = input_stream
        self._output = output_stream

    def serve(self) -> None:
        for line in self._input:
            self._handle_line(line)

    def _handle_line(self, line: str) -> None:
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            return
        if not isinstance(request, dict) or "id" not in request:
            return
        self._write(request["id"], self._payload(request))

    def _payload(self, request: dict) -> dict:
        try:
            return self._dispatch(request)
        except Exception as exc:
            return {"content": [{"type": "text", "text": f"adapter error: {exc}"}], "isError": True, "data": None}

    def _dispatch(self, request: dict) -> dict:
        method = request.get("method")
        params = request.get("params", {})
        if method == "initialize":
            return self._initialize_result()
        if method == "tools/list":
            return {"tools": self._list_schemas()}
        if method == "tools/call":
            return self._call_tool(params.get("name", ""), params.get("arguments", {}))
        return {}

    def _initialize_result(self) -> dict:
        info = {"name": self._server_name, "version": "1.0.0"}
        return {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": info}

    def _write(self, request_id: int, payload: dict) -> None:
        response = {"jsonrpc": "2.0", "id": request_id, "result": payload}
        self._output.write(json.dumps(response) + "\n")
        self._output.flush()
