import types

from tests.kernel_api_support import make_registry_tool
from tusk.kernel.agent.agent_result import AgentResult
from tusk.kernel.agent.planner_result_validator import PlannerResultValidator
from tusk.kernel.tool_registry import ToolRegistry


def test_planner_promotes_valid_plan_to_sequence() -> None:
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.type_text", "type", sequence_callable=True))
    logs: list[tuple[str, str]] = []
    result = _validated(_payload(["gnome.type_text"], "normal", _plan([_step("s1")])), registry, log=_logger(logs))
    assert result.status == "done"
    assert result.payload["execution_mode"] == "sequence"
    assert result.payload["sequence_plan"] == _plan([_step("s1")])
    assert logs == [("SEQPROMOTE", "session=s1 promoted normal plan to sequence with 1 steps")]


def test_planner_normalizes_unused_selected_tools() -> None:
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.type_text", "type", sequence_callable=True))
    payload = _payload(["gnome.type_text", "gnome.other"], "normal", _plan([_step("s1")]))
    result = _validated(payload, registry)
    assert result.status == "done"
    assert result.payload["selected_tool_names"] == ["gnome.type_text"]


def test_planner_rejects_missing_planned_steps() -> None:
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.type_text", "type", sequence_callable=True))
    result = _validated({"selected_tool_names": ["gnome.type_text"], "execution_mode": "normal"}, registry)
    assert result.status == "failed"
    assert "planned_steps" in result.summary


def test_planner_rejects_duplicate_planned_step_ids() -> None:
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.type_text", "type", sequence_callable=True))
    steps = [_step("s1"), _step("s1")]
    result = _validated(_payload(["gnome.type_text"], "normal", _plan(steps)), registry)
    assert result.status == "failed"
    assert "duplicate" in result.summary.lower()


def test_planner_rejects_non_sequence_callable_tool() -> None:
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.type_text", "type"))
    result = _validated(_payload(["gnome.type_text"], "sequence", _plan([_step("s1")])), registry)
    assert result.status == "failed"
    assert "sequence_callable" in result.summary


def test_planner_accepts_missing_selected_names_when_steps_are_valid() -> None:
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.type_text", "type", sequence_callable=True))
    result = _validated(_payload([], "normal", _plan([_step("s1")])), registry)
    assert result.status == "done"
    assert result.payload["selected_tool_names"] == ["gnome.type_text"]


def _validated(
    payload: dict[str, object],
    registry: ToolRegistry,
    log: object | None = None,
) -> AgentResult:
    result = AgentResult("done", "s1", "plan ready", payload=payload)
    return PlannerResultValidator(log).validate("planner", result, registry)


def _payload(names: list[str], mode: str, plan: dict[str, object]) -> dict[str, object]:
    return {"selected_tool_names": names, "execution_mode": mode, "planned_steps": plan}


def _plan(steps: list[dict[str, object]]) -> dict[str, object]:
    return {"goal": "Type hello", "steps": steps}


def _step(step_id: str) -> dict[str, object]:
    return {"id": step_id, "tool_name": "gnome.type_text", "args": {"text": "hello"}}


def _logger(logs: list[tuple[str, str]]) -> object:
    return types.SimpleNamespace(log=lambda tag, message, group=None: logs.append((tag, message)))
