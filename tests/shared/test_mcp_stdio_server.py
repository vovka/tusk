import io
import json

from tusk.shared.mcp import MCPStdioServer


def _serve(lines: list[str], call_tool=None) -> list[dict]:
    output = io.StringIO()
    server = MCPStdioServer(
        "demo",
        list_schemas=lambda: [{"name": "ping"}],
        call_tool=call_tool or (lambda name, args: {"content": [{"type": "text", "text": "pong"}], "isError": False}),
        input_stream=io.StringIO("\n".join(lines) + "\n"),
        output_stream=output,
    )
    server.serve()
    return [json.loads(line) for line in output.getvalue().splitlines()]


def _request(request_id: int, method: str, params: dict | None = None) -> str:
    return json.dumps({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}})


def test_initialize_reports_protocol_and_server_info() -> None:
    responses = _serve([_request(1, "initialize")])
    result = responses[0]["result"]
    assert result["protocolVersion"] == "2024-11-05"
    assert result["serverInfo"]["name"] == "demo"


def test_tools_list_returns_schemas() -> None:
    responses = _serve([_request(1, "tools/list")])
    assert responses[0]["result"]["tools"] == [{"name": "ping"}]


def test_tools_call_routes_name_and_arguments() -> None:
    seen: list[tuple[str, dict]] = []

    def call_tool(name: str, arguments: dict) -> dict:
        seen.append((name, arguments))
        return {"content": [], "isError": False}

    _serve([_request(1, "tools/call", {"name": "ping", "arguments": {"x": 1}})], call_tool)
    assert seen == [("ping", {"x": 1})]


def test_unknown_method_returns_empty_result() -> None:
    responses = _serve([_request(1, "bogus/method")])
    assert responses[0]["result"] == {}


def test_malformed_json_and_notifications_are_skipped() -> None:
    responses = _serve(["not json", json.dumps({"method": "notify"}), _request(2, "tools/list")])
    assert len(responses) == 1
    assert responses[0]["id"] == 2


def test_tool_exception_becomes_error_payload() -> None:
    def call_tool(name: str, arguments: dict) -> dict:
        raise RuntimeError("boom")

    responses = _serve([_request(1, "tools/call", {"name": "ping"})], call_tool)
    result = responses[0]["result"]
    assert result["isError"] is True
    assert "boom" in result["content"][0]["text"]
