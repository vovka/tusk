import json
import shlex
import subprocess
import sys

from tusk.shared.schemas.mcp_tool_result import MCPToolResult
from tusk.shared.schemas.mcp_tool_schema import MCPToolSchema

__all__ = ["MCPClient"]


class MCPClient:
    def __init__(self) -> None:
        self._process: subprocess.Popen | None = None
        self._next_id = 0

    async def connect_stdio(self, command: list[str], cwd: str, env: dict | None = None) -> None:
        self._process = subprocess.Popen(
            self._normalize_command(command),
            cwd=cwd,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self._request("initialize", {"protocolVersion": "2024-11-05", "capabilities": {}})

    async def connect_http(self, url: str) -> None:
        raise NotImplementedError(f"HTTP transport is not implemented: {url}")

    async def list_tools(self) -> list[MCPToolSchema]:
        payload = self._request("tools/list", {})
        return [
            MCPToolSchema(
                name=item["name"],
                description=item.get("description", ""),
                input_schema=item.get("inputSchema", {"type": "object", "properties": {}}),
            )
            for item in payload.get("tools", [])
        ]

    async def call_tool(self, name: str, arguments: dict) -> MCPToolResult:
        payload = self._request("tools/call", {"name": name, "arguments": arguments})
        content = payload.get("content", [])
        text = " ".join(item.get("text", "") for item in content if item.get("type") == "text")
        return MCPToolResult(text.strip(), bool(payload.get("isError")), payload.get("data"))

    async def shutdown(self) -> None:
        if self._process is None:
            return
        if self._process.poll() is None:
            self._process.terminate()
            self._process.wait(timeout=1.0)

    def _request(self, method: str, params: dict) -> dict:
        self._next_id += 1
        message = {"jsonrpc": "2.0", "id": self._next_id, "method": method, "params": params}
        self._write(message)
        line = self._read_line(method)
        if not line:
            raise RuntimeError(self._stderr() or f"MCP server exited during {method}")
        response = json.loads(line)
        return response.get("result", {})

    def _normalize_command(self, command: list[str]) -> list[str]:
        if len(command) == 1:
            return shlex.split(command[0])
        if command[0] == "python":
            return [sys.executable, *command[1:]]
        return command

    def _write(self, message: dict) -> None:
        assert self._process is not None and self._process.stdin is not None
        self._process.stdin.write(json.dumps(message) + "\n")
        self._process.stdin.flush()

    def _read_line(self, method: str) -> str:
        assert self._process is not None and self._process.stdout is not None
        return self._process.stdout.readline()

    def _stderr(self) -> str:
        if self._process is None or self._process.stderr is None:
            return ""
        return self._process.stderr.read().strip()
