from tusk.kernel.agent.backends.agent_request import AgentRequest
from tusk.kernel.agent.backends.codex_mcp.result_mapper import ResultMapper


def mapper() -> ResultMapper:
    return ResultMapper("codex_mcp")


def request(session_id: str = "") -> AgentRequest:
    return AgentRequest("open gedit", "command", session_id, metadata={"request_id": "r-1"})


def test_success_maps_structured_content_and_thread_id_to_session_id() -> None:
    payload = {"structuredContent": {"threadId": "t-9", "content": "done"}}
    result = mapper().success(request(), payload)
    assert result.handled is True
    assert result.reply == "done"
    assert result.session_id == "t-9"
    assert result.metadata["backend"] == "codex_mcp"
    assert result.metadata["mode"] == "command"
    assert result.raw_output is payload


def test_success_falls_back_to_content_text_items() -> None:
    payload = {"content": [{"type": "text", "text": "hello"}, {"type": "text", "text": "there"}]}
    result = mapper().success(request("t-1"), payload)
    assert result.reply == "hello there"
    assert result.session_id == "t-1"


def test_success_with_is_error_payload_returns_failed_result() -> None:
    payload = {"isError": True, "content": [{"type": "text", "text": "denied"}]}
    result = mapper().success(request(), payload)
    assert result.handled is False
    assert result.status == "failed"
    assert "denied" in result.reply


def test_success_with_empty_payload_returns_failed_result() -> None:
    result = mapper().success(request(), {})
    assert result.handled is False
    assert "empty response" in result.reply


def test_failure_preserves_session_id_and_status() -> None:
    result = mapper().failure(request("t-3"), "Codex MCP timed out", "timeout")
    assert result.handled is False
    assert result.status == "timeout"
    assert result.session_id == "t-3"
    assert result.metadata["backend"] == "codex_mcp"
