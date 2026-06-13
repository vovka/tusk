from adapters.coding.server import CodingServer


def test_start_coding_session_seeds_buffer_and_returns_session_id() -> None:
    server = CodingServer(_planner([]))
    data = server._tool_start_coding_session({"initial_buffer": "a\nb"})["data"]
    assert data["session_id"]
    assert server._sessions[data["session_id"]].to_text() == "a\nb"


def test_process_intent_applies_planned_ops_and_attaches_full_buffer() -> None:
    server = CodingServer(_planner([_op()]))
    session_id = server._tool_start_coding_session({"initial_buffer": "a\nb"})["data"]["session_id"]
    update = server._tool_process_intent({"session_id": session_id, "intent": "change b"})
    assert update["data"]["operations"][0]["full_buffer"] == "a\nB"


def test_process_intent_keeps_model_in_lockstep_across_calls() -> None:
    server = CodingServer(_planner([_op()]))
    session_id = server._tool_start_coding_session({"initial_buffer": "a\nb"})["data"]["session_id"]
    server._tool_process_intent({"session_id": session_id, "intent": "change b"})
    assert server._sessions[session_id].to_text() == "a\nB"


def test_stop_coding_session_clears_state() -> None:
    server = CodingServer(_planner([]))
    session_id = server._tool_start_coding_session({"initial_buffer": ""})["data"]["session_id"]
    server._tool_stop_coding_session({"session_id": session_id})
    assert session_id not in server._sessions


def _op() -> dict:
    return {"kind": "replace", "target_start": 2, "target_end": 2, "new_text": "B"}


def _planner(operations: list[dict]) -> object:
    import types

    return types.SimpleNamespace(plan=lambda intent, buffer_text: operations)
