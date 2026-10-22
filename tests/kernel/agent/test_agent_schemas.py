from tusk.kernel.agent.agent_run_request import AgentRunRequest
from tusk.kernel.agent.agent_result import AgentResult


def test_run_request_defaults() -> None:
    request = AgentRunRequest("do something")
    assert request.profile_id == "default"
    assert request.session_id == ""
    assert request.runtime_tool_names == ()


def test_result_reply_text_prefers_text() -> None:
    result = AgentResult("done", "s1", "summary", text="full text")
    assert result.reply_text() == "full text"


def test_result_reply_text_falls_back_to_summary() -> None:
    result = AgentResult("done", "s1", "summary")
    assert result.reply_text() == "summary"


def test_result_to_dict_includes_all_fields() -> None:
    result = AgentResult("done", "s1", "ok", text="text", payload={"key": "val"})
    data = result.to_dict()
    assert data["status"] == "done"
    assert data["session_id"] == "s1"
    assert data["payload"] == {"key": "val"}
