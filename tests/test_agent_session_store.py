import tempfile

from tusk.lib.agent.file_agent_session_store import FileAgentSessionStore


def _store() -> FileAgentSessionStore:
    return FileAgentSessionStore(tempfile.mkdtemp(prefix="tusk-test-"))


def test_create_session_id_is_unique() -> None:
    store = _store()
    assert store.create_session_id() != store.create_session_id()


def test_has_session_returns_false_for_unknown() -> None:
    assert _store().has_session("unknown") is False


def test_start_session_makes_session_exist() -> None:
    store = _store()
    sid = store.create_session_id()
    store.start_session(sid, "conversation", "", "", {})
    assert store.has_session(sid) is True


def test_append_and_read_messages() -> None:
    store = _store()
    sid = store.create_session_id()
    store.start_session(sid, "test", "", "", {})
    store.append_event(sid, "message_appended", {"role": "user", "content": "hello"})
    messages = store.conversation_messages(sid)
    assert messages == [{"role": "user", "content": "hello"}]


def test_session_digest_contains_events() -> None:
    store = _store()
    sid = store.create_session_id()
    store.start_session(sid, "test", "", "", {})
    store.append_event(sid, "message_appended", {"message": "hello world"})
    digest = store.session_digest(sid)
    assert "hello world" in digest


def test_final_result_returns_none_without_finish() -> None:
    store = _store()
    sid = store.create_session_id()
    store.start_session(sid, "test", "", "", {})
    assert store.final_result(sid) is None


def test_final_result_returns_result_after_finish() -> None:
    store = _store()
    sid = store.create_session_id()
    store.start_session(sid, "test", "", "", {})
    store.append_event(sid, "session_finished", {
        "status": "done", "session_id": sid, "summary": "ok", "text": "done", "payload": {}, "artifact_refs": [],
    })
    result = store.final_result(sid)
    assert result is not None
    assert result.status == "done"
    assert result.summary == "ok"
