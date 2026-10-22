from tests.kernel_api_support import make_registry_tool
from tusk.kernel.agent.agent_result import AgentResult
from tusk.kernel.agent.planner.result_validator import ResultValidator
from tusk.kernel.tools.tool_registry import ToolRegistry


def test_planner_validator_rejects_missing_tools() -> None:
    validator = ResultValidator()
    result = AgentResult("done", "s1", "plan ready", payload={})
    validated = validator.validate("planner", result, _registry())
    assert validated.status == "failed"


def test_planner_validator_rejects_non_tool_names() -> None:
    validator = ResultValidator()
    result = AgentResult("done", "s1", "plan ready", payload={"selected_tool_names": ["executor", "desktop"]})
    validated = validator.validate("planner", result, _registry())
    assert validated.status == "failed"


def test_planner_validator_accepts_valid_tools() -> None:
    validator = ResultValidator()
    result = AgentResult("done", "s1", "plan ready", payload=_payload())
    validated = validator.validate("planner", result, _registry())
    assert validated.status == "done"


def _registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.type_text", "type"))
    return registry


def _payload() -> dict[str, object]:
    step = {"id": "s1", "tool_name": "gnome.type_text", "args": {"text": "hello"}}
    return {"selected_tool_names": ["gnome.type_text"], "execution_mode": "normal", "planned_steps": {"steps": [step]}}
