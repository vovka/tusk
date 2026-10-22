import json

from tusk.shared.mcp.mcp_stdio_transport import MCPStdioTransport

__all__ = ["Client"]


class Client:
    """One persistent `codex mcp-server` process spoken to over stdio JSON-RPC.

    codex rejects an `initialize` without clientInfo, so the handshake here is
    stricter than the shared MCPClient's: clientInfo plus the spec-mandated
    `notifications/initialized` follow-up. codex also emits `codex/event`
    notifications between a request and its response; those (and any stale
    replies) are skipped, which is what makes the shared MCPClient unusable here.
    """

    def __init__(self, command: list[str], cwd: str, timeout_seconds: float) -> None:
        self._transport = MCPStdioTransport(command, cwd, None, timeout_seconds)
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
        return self._read_response(self._next_id, method)

    def _notify(self, method: str) -> None:
        self._write({"jsonrpc": "2.0", "method": method}, method)

    def _write(self, message: dict, method: str) -> None:
        try:
            self._transport.write_line(json.dumps(message))
        except BrokenPipeError as error:
            raise RuntimeError(self._with_stderr(f"codex mcp-server pipe closed during {method}")) from error

    def _read_response(self, request_id: int, method: str) -> dict:
        while True:
            message = self._decoded(self._line(method), method)
            if isinstance(message, dict) and message.get("id") == request_id:
                return self._result(message, method)

    def _line(self, method: str) -> str:
        line = self._transport.read_line()
        if line is None:
            raise TimeoutError(f"codex mcp-server timed out during {method}")
        if not line.strip():
            raise RuntimeError(self._with_stderr(f"codex mcp-server exited during {method}"))
        return line

    def _decoded(self, line: str, method: str) -> dict:
        try:
            return json.loads(line)
        except json.JSONDecodeError as error:
            raise RuntimeError(f"invalid JSON from codex mcp-server during {method}: {error}") from error

    def _result(self, message: dict, method: str) -> dict:
        error = message.get("error")
        if error is not None:
            raise RuntimeError(f"codex mcp-server error during {method}: {error.get('message', error)}")
        return message.get("result", {})

    def _with_stderr(self, summary: str) -> str:
        stderr = self._transport.stderr_text()[:300]
        return f"{summary}: {stderr}" if stderr else summary
