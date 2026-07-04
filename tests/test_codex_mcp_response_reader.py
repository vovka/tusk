import json

import pytest

from tusk.kernel.agent_backends.codex_mcp_response_reader import CodexMcpResponseReader


class ScriptedTransport:
    def __init__(self, lines: list[str | None], stderr: str = "") -> None:
        self._lines = list(lines)
        self._stderr = stderr

    def read_line(self) -> str | None:
        return self._lines.pop(0)

    def stderr_text(self) -> str:
        return self._stderr


def response(request_id: int, result: dict) -> str:
    return json.dumps({"jsonrpc": "2.0", "id": request_id, "result": result})


def test_reader_skips_codex_event_notifications() -> None:
    notification = json.dumps({"jsonrpc": "2.0", "method": "codex/event", "params": {}})
    transport = ScriptedTransport([notification, notification, response(7, {"ok": True})])
    assert CodexMcpResponseReader(transport).read(7, "tools/call") == {"ok": True}


def test_reader_skips_responses_with_mismatched_id() -> None:
    transport = ScriptedTransport([response(6, {"stale": True}), response(7, {"ok": True})])
    assert CodexMcpResponseReader(transport).read(7, "tools/call") == {"ok": True}


def test_reader_raises_timeout_error_on_read_timeout() -> None:
    with pytest.raises(TimeoutError, match="timed out during tools/call"):
        CodexMcpResponseReader(ScriptedTransport([None])).read(1, "tools/call")


def test_reader_raises_runtime_error_on_eof_with_stderr() -> None:
    transport = ScriptedTransport([""], stderr="boom diagnostics")
    with pytest.raises(RuntimeError, match="exited during initialize.*boom"):
        CodexMcpResponseReader(transport).read(1, "initialize")


def test_reader_raises_runtime_error_on_invalid_json() -> None:
    with pytest.raises(RuntimeError, match="invalid JSON"):
        CodexMcpResponseReader(ScriptedTransport(["not json"])).read(1, "tools/call")


def test_reader_raises_runtime_error_on_error_response() -> None:
    error = json.dumps({"jsonrpc": "2.0", "id": 3, "error": {"code": -32601, "message": "nope"}})
    with pytest.raises(RuntimeError, match="error during tools/call: nope"):
        CodexMcpResponseReader(ScriptedTransport([error])).read(3, "tools/call")
