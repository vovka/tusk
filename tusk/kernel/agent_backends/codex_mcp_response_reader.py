import json

__all__ = ["CodexMcpResponseReader"]


class CodexMcpResponseReader:
    """Reads id-correlated JSON-RPC responses from a codex mcp-server transport.

    codex emits `codex/event` notifications between a request and its response;
    those (and any stale replies) are skipped instead of being mistaken for the
    response, which is what makes the shared MCPClient unusable here.
    """

    def __init__(self, transport: object) -> None:
        self._transport = transport

    def read(self, request_id: int, method: str) -> dict:
        while True:
            message = self._decoded(self._line(method), method)
            if not self._matches(message, request_id):
                continue
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

    def _matches(self, message: dict, request_id: int) -> bool:
        return isinstance(message, dict) and message.get("id") == request_id

    def _result(self, message: dict, method: str) -> dict:
        error = message.get("error")
        if error is not None:
            raise RuntimeError(f"codex mcp-server error during {method}: {error.get('message', error)}")
        return message.get("result", {})

    def _with_stderr(self, summary: str) -> str:
        stderr = self._transport.stderr_text()[:300]
        return f"{summary}: {stderr}" if stderr else summary
