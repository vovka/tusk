from tusk.kernel.agent.agent_run_request import AgentRunRequest
from tusk.kernel.agent.agent_result import AgentResult
from tusk.shared.schemas.tool_call import ToolCall


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


def test_tool_call_normalizes_functions_done_alias() -> None:
    call = ToolCall("functions.done", {"status": "done"})
    assert call.tool_name == "done"


def test_tool_call_normalizes_name_wrapped_functions_done_alias() -> None:
    call = ToolCall("name=functions.done]", {"status": "done"})
    assert call.tool_name == "done"


def test_tool_call_normalizes_equal_prefixed_functions_done_alias() -> None:
    call = ToolCall("=functions.done", {"status": "done"})
    assert call.tool_name == "done"


def test_tool_call_normalizes_tool_done_alias() -> None:
    call = ToolCall("tool:done", {"status": "done"})
    assert call.tool_name == "done"


def test_tool_call_normalizes_legacy_finish_alias() -> None:
    call = ToolCall("finish_agent_run", {"status": "done"})
    assert call.tool_name == "done"


def test_tool_call_normalizes_bare_gnome_tool_aliases() -> None:
    assert ToolCall("press_keys").tool_name == "gnome.press_keys"
    assert ToolCall("type_text").tool_name == "gnome.type_text"
    assert ToolCall("write_clipboard").tool_name == "gnome.write_clipboard"
