import types

from tusk.lib.agent.agent_result import AgentResult
from tusk.lib.agent.agent_run_guard import AgentRunGuard
from tusk.lib.agent.agent_run_request import AgentRunRequest
from tusk.lib.agent.executor_tool_guard import ExecutorToolGuard
from tusk.lib.agent.planner_result_validator import PlannerResultValidator


def test_guard_rejects_unknown_profile() -> None:
    guard = AgentRunGuard()
    result = guard.validate(AgentRunRequest("test", "missing"), None, ())
    assert result is not None
    assert "unknown profile" in result.summary


def test_guard_rejects_deep_delegation() -> None:
    guard = AgentRunGuard()
    profile = types.SimpleNamespace(profile_id="executor")
    lineage = (("a", "s1", "i1"), ("b", "s2", "i2"), ("c", "s3", "i3"), ("d", "s4", "i4"))
    result = guard.validate(AgentRunRequest("test", "executor"), profile, lineage)
    assert result is not None
    assert "depth" in result.summary


def test_guard_rejects_recursive_delegation() -> None:
    guard = AgentRunGuard()
    profile = types.SimpleNamespace(profile_id="planner")
    lineage = (("planner", "s1", "do stuff"),)
    result = guard.validate(AgentRunRequest("test", "planner"), profile, lineage)
    assert result is not None
    assert "recursive" in result.summary


def test_guard_allows_valid_request() -> None:
    guard = AgentRunGuard()
    profile = types.SimpleNamespace(profile_id="executor")
    assert guard.validate(AgentRunRequest("test", "executor"), profile, ()) is None


def test_executor_guard_rejects_empty_tools() -> None:
    guard = ExecutorToolGuard()
    result = guard.validate("executor", AgentRunRequest("test", "executor"), set())
    assert result is not None
    assert result.status == "need_tools"


def test_executor_guard_allows_non_executor() -> None:
    guard = ExecutorToolGuard()
    result = guard.validate("conversation", AgentRunRequest("test"), set())
    assert result is None


def test_planner_validator_rejects_missing_tools() -> None:
    validator = PlannerResultValidator()
    result = AgentResult("done", "s1", "plan ready", payload={})
    validated = validator.validate("planner", result, {"gnome.type_text"})
    assert validated.status == "failed"


def test_planner_validator_rejects_non_tool_names() -> None:
    validator = PlannerResultValidator()
    result = AgentResult("done", "s1", "plan ready", payload={"selected_tool_names": ["executor", "desktop"]})
    validated = validator.validate("planner", result, {"gnome.type_text"})
    assert validated.status == "failed"


def test_planner_validator_accepts_valid_tools() -> None:
    validator = PlannerResultValidator()
    result = AgentResult("done", "s1", "plan ready", payload={"selected_tool_names": ["gnome.type_text"]})
    validated = validator.validate("planner", result, {"gnome.type_text"})
    assert validated.status == "done"
