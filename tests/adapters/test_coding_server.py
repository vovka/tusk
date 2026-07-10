import types

from adapters.coding.server import CodingServer


def test_start_coding_session_seeds_buffer_and_returns_session_id() -> None:
    server = CodingServer(_planner("a\nb"))
    data = server._tool_start_coding_session({"initial_buffer": "a\nb"})["data"]
    assert data["session_id"]
    assert server._sessions[data["session_id"]] == "a\nb"


def test_process_intent_returns_one_replace_op_spanning_the_old_buffer() -> None:
    server = CodingServer(_planner("a\nB"))
    session_id = server._tool_start_coding_session({"initial_buffer": "a\nb"})["data"]["session_id"]
    update = server._tool_process_intent({"session_id": session_id, "intent": "change b"})
    operation = update["data"]["operations"][0]
    assert operation == {"kind": "replace", "target_start": 1, "target_end": 2, "new_text": "a\nB", "full_buffer": "a\nB"}


def test_process_intent_keeps_session_buffer_in_lockstep_across_calls() -> None:
    server = CodingServer(_planner("a\nB"))
    session_id = server._tool_start_coding_session({"initial_buffer": "a\nb"})["data"]["session_id"]
    server._tool_process_intent({"session_id": session_id, "intent": "change b"})
    assert server._sessions[session_id] == "a\nB"


def test_process_intent_fails_without_mutating_session_when_planner_cannot_plan() -> None:
    server = CodingServer(_planner(None))
    session_id = server._tool_start_coding_session({"initial_buffer": "a\nb"})["data"]["session_id"]
    update = server._tool_process_intent({"session_id": session_id, "intent": "change b"})
    assert update["success"] is False
    assert server._sessions[session_id] == "a\nb"


def test_stop_coding_session_clears_state() -> None:
    server = CodingServer(_planner(""))
    session_id = server._tool_start_coding_session({"initial_buffer": ""})["data"]["session_id"]
    server._tool_stop_coding_session({"session_id": session_id})
    assert session_id not in server._sessions


def _planner(new_buffer: str | None) -> object:
    return types.SimpleNamespace(plan=lambda intent, buffer_text: new_buffer)


def test_serve_answers_tools_list_over_injected_streams() -> None:
    import io
    import json

    request = '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
    output = io.StringIO()
    CodingServer(_planner(""), input_stream=io.StringIO(request + "\n"), output_stream=output).serve()
    tools = json.loads(output.getvalue())["result"]["tools"]
    assert {tool["name"] for tool in tools} == {"start_coding_session", "process_intent", "stop_coding_session"}
