import json

from tusk.kernel.agent_backends.codex_mcp_response_reader import CodexMcpResponseReader
from tusk.shared.mcp.mcp_stdio_transport import MCPStdioTransport

__all__ = ["CodexMcpClient"]


class CodexMcpClient:
    """One persistent `codex mcp-server` process spoken to over stdio JSON-RPC.

    codex rejects an `initialize` without clientInfo, so the handshake here is
    stricter than the shared MCPClient's: clientInfo plus the spec-mandated
    `notifications/initialized` follow-up.
    """

    def __init__(self, command: list[str], cwd: str, timeout_seconds: float) -> None:
        self._transport = MCPStdioTransport(command, cwd, None, timeout_seconds)
        self._reader = CodexMcpResponseReader(self._transport)
        self._next_id = 0
        self._handshake()

    def call_tool(self, name: str, arguments: dict) -> dict:
        return self._request("tools/call", {"name": name, "arguments": arguments})

    def is_running(self) -> bool:
        return self._transport.is_running()

    def stop(self) -> None:
        self._transport.stop()

    def _handshake(self) -> None:
        params = {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "tusk", "version": "1.0"},
        }
        self._request("initialize", params)
        self._notify("notifications/initialized")

    def _request(self, method: str, params: dict) -> dict:
        self._next_id += 1
        message = {"jsonrpc": "2.0", "id": self._next_id, "method": method, "params": params}
        self._write(message, method)
        return self._reader.read(self._next_id, method)

    def _notify(self, method: str) -> None:
        self._write({"jsonrpc": "2.0", "method": method}, method)

    def _write(self, message: dict, method: str) -> None:
        try:
            self._transport.write_line(json.dumps(message))
        except BrokenPipeError as error:
            raise RuntimeError(self._pipe_failure(method)) from error

    def _pipe_failure(self, method: str) -> str:
        stderr = self._transport.stderr_text()[:300]
        summary = f"codex mcp-server pipe closed during {method}"
        return f"{summary}: {stderr}" if stderr else summary
