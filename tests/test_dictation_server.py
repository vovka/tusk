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


def _update(operation: str, text: str, replace_chars: int) -> dict:
    return {
        "operation": operation,
        "text": text,
        "replace_chars": replace_chars,
        "should_stop": False,
    }
