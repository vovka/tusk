import types

from tusk.shared.schemas.tools.tool_call import ToolCall
from tusk.kernel.agent.agent_result import AgentResult
from tusk.kernel.agent.agent_run_request import AgentRunRequest
from tusk.kernel.agent.delegation import Delegation


class _Store:
    def __init__(self) -> None:
        self.events: list[tuple[str, str, dict[str, object]]] = []

    def append_event(self, session_id: str, event_type: str, data: dict[str, object]) -> None:
        self.events.append((session_id, event_type, data))


def test_request_reads_tool_call_parameters() -> None:
    call = ToolCall("run_agent", {"instruction": "do it", "profile_id": "planner", "runtime_tool_names": ["a"]}, "c1")
    request = Delegation(_Store()).request(call, "parent")
    assert request == AgentRunRequest("do it", "planner", parent_session_id="parent", parent_call_id="c1", runtime_tool_names=("a",))


def test_invalid_request_is_failed_tool_result() -> None:
    result = Delegation(_Store()).invalid_request()
    assert result.success is False
    assert "instruction" in result.message


def test_refusal_rejects_unknown_profile() -> None:
    result = Delegation(_Store()).refusal(AgentRunRequest("test", "missing"), None, (), set())
    assert result is not None
    assert "unknown profile" in result.summary


def test_refusal_rejects_deep_delegation() -> None:
    profile = types.SimpleNamespace(profile_id="executor")
    lineage = (("a", "s1", "i1"), ("b", "s2", "i2"), ("c", "s3", "i3"), ("d", "s4", "i4"))
    result = Delegation(_Store()).refusal(AgentRunRequest("test", "executor"), profile, lineage, {"x"})
    assert result is not None
    assert "depth" in result.summary


def test_refusal_rejects_recursive_delegation() -> None:
    profile = types.SimpleNamespace(profile_id="planner")
    result = Delegation(_Store()).refusal(AgentRunRequest("test", "planner"), profile, (("planner", "s1", "do"),), set())
    assert result is not None
    assert "recursive" in result.summary


def test_refusal_rejects_executor_without_tools() -> None:
    profile = types.SimpleNamespace(profile_id="executor")
    result = Delegation(_Store()).refusal(AgentRunRequest("test", "executor"), profile, (), set())
    assert result is not None
    assert result.status == "need_tools"


def test_refusal_allows_valid_request() -> None:
    profile = types.SimpleNamespace(profile_id="executor")
    assert Delegation(_Store()).refusal(AgentRunRequest("test", "executor"), profile, (), {"gnome.type_text"}) is None


def test_refusal_allows_non_executor_without_tools() -> None:
    profile = types.SimpleNamespace(profile_id="conversation")
    assert Delegation(_Store()).refusal(AgentRunRequest("test", "conversation"), profile, (), set()) is None


def test_child_lineage_appends_profile_session_and_instruction() -> None:
    lineage = Delegation(_Store()).child_lineage(AgentRunRequest("do stuff", "planner"), "s2", (("a", "s1", "i"),))
    assert lineage == (("a", "s1", "i"), ("planner", "s2", "do stuff"))


def test_started_and_finished_record_events() -> None:
    store = _Store()
    delegation = Delegation(store)
    delegation.started("parent", AgentRunRequest("do it", "planner"))
    delegation.finished("parent", "planner", AgentResult("done", "child", "ok"))
    assert [event[1] for event in store.events] == ["child_started", "child_finished"]
    assert store.events[1][2] == {"child_profile": "planner", "child_session": "child", "child_status": "done"}


def test_result_succeeds_only_when_child_is_done() -> None:
    delegation = Delegation(_Store())
    done = delegation.result("planner", AgentResult("done", "child", "ok", "reply"))
    failed = delegation.result("planner", AgentResult("failed", "child", "bad"))
    assert done.success and done.message == "reply"
    assert failed.success is False
    assert done.data["child_result"]["profile_id"] == "planner"
