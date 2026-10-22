import pytest

from tusk.shared.mcp import mcp_client
from tusk.shared.mcp.mcp_client import MCPClient


class _HangingTransport:
    def __init__(self) -> None:
        self.stopped = False

    def write_line(self, payload: str) -> None:
        pass

    def read_line(self) -> str | None:
        return None

    def stderr_text(self) -> str:
        return ""

    def stop(self) -> None:
        self.stopped = True

    def is_running(self) -> bool:
        return not self.stopped


def test_connect_stdio_stops_transport_when_initialize_fails(monkeypatch) -> None:
    transport = _HangingTransport()
    monkeypatch.setattr(mcp_client, "MCPStdioTransport", lambda *args: transport)
    client = MCPClient(response_timeout_seconds=0.01)
    with pytest.raises(RuntimeError):
        client.connect_stdio(["python", "server.py"], ".")
    assert transport.stopped is True
    assert client.is_running() is False
