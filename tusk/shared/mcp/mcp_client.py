import json
import shlex
import sys

from tusk.shared.mcp.mcp_stdio_transport import MCPStdioTransport
from tusk.shared.schemas.tools.mcp_tool_result import MCPToolResult
from tusk.shared.schemas.tools.mcp_tool_schema import MCPToolSchema

__all__ = ["MCPClient"]


class MCPClient:
    def __init__(self, response_timeout_seconds: float = 30.0) -> None:
        self._transport: MCPStdioTransport | None = None
        self._timeout = response_timeout_seconds
        self._next_id = 0

    def connect_stdio(self, command: list[str], cwd: str, env: dict | None = None) -> None:
        self._transport = MCPStdioTransport(self._normalize_command(command), cwd, env, self._timeout)
        try:
            self._request("initialize", {"protocolVersion": "2024-11-05", "capabilities": {}})
        except RuntimeError:
            self._transport.stop()
            self._transport = None
            raise

    def connect_http(self, url: str) -> None:
        raise NotImplementedError(f"HTTP transport is not implemented: {url}")

    def list_tools(self) -> list[MCPToolSchema]:
        payload = self._request("tools/list", {})
        return [
            MCPToolSchema(
                name=item["name"],
                description=item.get("description", ""),
                input_schema=item.get("inputSchema", {"type": "object", "properties": {}}),
            )
            for item in payload.get("tools", [])
        ]

    def call_tool(self, name: str, arguments: dict) -> MCPToolResult:
        payload = self._request("tools/call", {"name": name, "arguments": arguments})
        content = payload.get("content", [])
        text = " ".join(item.get("text", "") for item in content if item.get("type") == "text")
        return MCPToolResult(text.strip(), bool(payload.get("isError")), payload.get("data"))

    def shutdown(self) -> None:
        if self._transport is not None:
            self._transport.stop()

    def is_running(self) -> bool:
        return self._transport is not None and self._transport.is_running()

    def _request(self, method: str, params: dict) -> dict:
        self._next_id += 1
        message = {"jsonrpc": "2.0", "id": self._next_id, "method": method, "params": params}
        return self._decoded(self._exchange(json.dumps(message), method), method)

    def _exchange(self, payload: str, method: str) -> str:
        assert self._transport is not None
        try:
            self._transport.write_line(payload)
        except BrokenPipeError as exc:
            raise RuntimeError(self._failure_text(f"MCP server pipe closed during {method}")) from exc
        return self._read(method)

    def _read(self, method: str) -> str:
        assert self._transport is not None
        line = self._transport.read_line()
        if line is None:
            raise RuntimeError(self._failure_text(f"MCP server timed out during {method}"))
        if not line:
            raise RuntimeError(self._failure_text(f"MCP server exited during {method}"))
        return line

    def _decoded(self, line: str, method: str) -> dict:
        try:
            response = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RuntimeError(self._failure_text(f"invalid JSON from MCP server during {method}: {exc}")) from exc
        return response.get("result", {})

    def _failure_text(self, summary: str) -> str:
        assert self._transport is not None
        stderr = self._transport.stderr_text()
        return f"{summary}: {stderr}" if stderr else summary

    def _normalize_command(self, command: list[str]) -> list[str]:
        if len(command) == 1:
            return shlex.split(command[0])
        if command[0] == "python":
            return [sys.executable, *command[1:]]
        return command
