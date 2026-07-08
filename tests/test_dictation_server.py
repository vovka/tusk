import io
import json

from adapters.dictation.dictation_session_store import DictationSessionStore
from adapters.dictation.server import DictationServer


def test_process_segment_inserts_text_verbatim() -> None:
    server = DictationServer()
    session_id = server._tool_start_dictation({})["data"]["session_id"]
    update = server._tool_process_segment({"session_id": session_id, "text": "tell me a joke"})
    assert update["data"]["text"] == "tell me a joke"


def test_process_segment_inserts_followup_text_instead_of_replacing() -> None:
    server = DictationServer()
    session_id = server._tool_start_dictation({})["data"]["session_id"]
    server._tool_process_segment({"session_id": session_id, "text": "hello"})
    update = server._tool_process_segment({"session_id": session_id, "text": "world"})
    assert update["data"] == _update("insert", " world", 0)


def test_process_segment_treats_stop_phrase_as_literal_text() -> None:
    server = DictationServer()
    session_id = server._tool_start_dictation({})["data"]["session_id"]
    update = server._tool_process_segment({"session_id": session_id, "text": "Stop dictation mode, please."})
    assert update["message"] == "dictation updated"
    assert update["data"] == _update("insert", "Stop dictation mode, please.", 0)


def test_stop_dictation_clears_session_state() -> None:
    server = DictationServer()
    session_id = server._tool_start_dictation({})["data"]["session_id"]
    server._tool_stop_dictation({"session_id": session_id})
    assert session_id not in server._sessions


def test_unknown_tool_returns_error_payload() -> None:
    result = DictationServer()._call("bogus", {})
    assert result["isError"] is True
    assert "unknown tool" in result["content"][0]["text"]


def test_malformed_request_line_is_skipped() -> None:
    output = io.StringIO()
    DictationServer(input_stream=io.StringIO("this is not json\n"), output_stream=output).serve()
    assert output.getvalue() == ""


def test_non_dict_request_line_is_skipped() -> None:
    output = io.StringIO()
    DictationServer(input_stream=io.StringIO("123\n"), output_stream=output).serve()
    assert output.getvalue() == ""


def test_process_segment_on_unknown_session_returns_error() -> None:
    payload = DictationServer()._tool_process_segment({"session_id": "missing", "text": "hi"})
    assert payload["success"] is False
    assert "missing" in payload["message"]


def test_tool_crash_is_answered_as_error() -> None:
    line = json.dumps({"jsonrpc": "2.0", "id": 7, "method": "tools/call", "params": {"name": "process_segment", "arguments": {}}})
    output = io.StringIO()
    DictationServer(input_stream=io.StringIO(line + "\n"), output_stream=output).serve()
    response = json.loads(output.getvalue())
    assert response["id"] == 7
    assert response["result"]["isError"] is True


def test_stale_sessions_are_pruned_on_new_activity() -> None:
    clock = {"now": 0.0}
    store = DictationSessionStore(time_source=lambda: clock["now"], max_age_seconds=10.0)
    server = DictationServer(sessions=store)
    session_id = server._tool_start_dictation({})["data"]["session_id"]
    clock["now"] = 20.0
    server._tool_start_dictation({})
    assert session_id not in server._sessions


def _update(operation: str, text: str, replace_chars: int) -> dict:
    return {
        "operation": operation,
        "text": text,
        "replace_chars": replace_chars,
        "should_stop": False,
    }


def test_serve_answers_tools_list_over_injected_streams() -> None:
    request = '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
    output = io.StringIO()
    DictationServer(input_stream=io.StringIO(request + "\n"), output_stream=output).serve()
    tools = json.loads(output.getvalue())["result"]["tools"]
    assert {tool["name"] for tool in tools} == {"start_dictation", "process_segment", "stop_dictation"}
