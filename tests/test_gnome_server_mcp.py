import io

from adapters.gnome.server import GnomeServer


NOTIFY = '{"jsonrpc":"2.0","method":"notifications/initialized"}'
INIT = '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'


def test_serve_skips_jsonrpc_notifications_without_id(monkeypatch, capsys) -> None:
    """MCP clients (codex) send `notifications/initialized` (no id) after initialize;
    it must not crash the server or get a response."""
    monkeypatch.setattr("sys.stdin", io.StringIO(NOTIFY + "\n" + INIT + "\n"))
    GnomeServer().serve()
    responses = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert len(responses) == 1 and '"id": 1' in responses[0]


def test_initialize_result_includes_server_info() -> None:
    """rmcp-based MCP clients (codex) require serverInfo in the initialize result."""
    result = GnomeServer()._initialize_result()
    assert result["serverInfo"]["name"] == "gnome"
    assert result["protocolVersion"] == "2024-11-05"
    assert "tools" in result["capabilities"]
