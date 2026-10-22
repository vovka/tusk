import io
import json

from adapters.gnome.server import build_server

NOTIFY = '{"jsonrpc":"2.0","method":"notifications/initialized"}'
INIT = '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'


def _responses(*lines: str) -> list[str]:
    output = io.StringIO()
    build_server(io.StringIO("\n".join(lines) + "\n"), output).serve()
    return [line for line in output.getvalue().splitlines() if line.strip()]


def test_serve_skips_jsonrpc_notifications_without_id() -> None:
    """MCP clients (codex) send `notifications/initialized` (no id) after initialize;
    it must not crash the server or get a response."""
    responses = _responses(NOTIFY, INIT)
    assert len(responses) == 1 and '"id": 1' in responses[0]


def test_initialize_result_includes_server_info() -> None:
    """rmcp-based MCP clients (codex) require serverInfo in the initialize result."""
    result = json.loads(_responses(INIT)[0])["result"]
    assert result["serverInfo"]["name"] == "gnome"
    assert result["protocolVersion"] == "2024-11-05"
    assert "tools" in result["capabilities"]
